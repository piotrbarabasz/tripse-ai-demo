"""Small authenticated-demo job adapter: Firestore transactions and Cloud Tasks.

No process-local job state, background threads, SQL or real WhatsApp transport.
The injected store/dispatcher boundary permits deterministic offline tests.
"""
import hashlib
import json
import logging
import time
from contextvars import ContextVar
from uuid import uuid4, uuid5, NAMESPACE_URL

from fastapi import HTTPException

from app.db import now
from app.document_studio.repository import StorageError
from app.sharing import token_hash, result_summary

principal = ContextVar("cloud_principal", default=None)
logger = logging.getLogger(__name__)


def owner():
    value = principal.get()
    if not value:
        raise HTTPException(401, "Verified identity required")
    return hashlib.sha256(value.encode()).hexdigest()


class FirestoreJobStore:
    def __init__(self, client):
        self.client = client
        self.collection = client.collection("jobs")

    def get(self, key):
        snapshot = self.collection.document(key).get(timeout=10)
        return snapshot.to_dict() if snapshot.exists else None

    def mutate(self, key, operation):
        from google.cloud import firestore
        ref = self.collection.document(key)

        @firestore.transactional
        def apply(transaction):
            snapshot = ref.get(transaction=transaction, timeout=10)
            value, result = operation(snapshot.to_dict() if snapshot.exists else None)
            if value is not None:
                transaction.set(ref, value)
            return result

        from google.api_core.exceptions import GoogleAPIError
        try:
            return apply(self.client.transaction(max_attempts=5))
        except GoogleAPIError as exc:
            raise StorageError("Cloud job transaction unavailable") from exc
        except ValueError as exc:
            # The SDK wraps exhausted Aborted retries in ValueError.
            if isinstance(exc.__cause__, GoogleAPIError):
                raise StorageError("Cloud job transaction retry limit exceeded") from exc
            raise

    def find(self, field, value):
        from google.cloud.firestore_v1.base_query import FieldFilter
        return [s.to_dict() for s in self.collection.where(filter=FieldFilter(field, "==", value)).stream(timeout=10)]


class CloudTaskDispatcher:
    def __init__(self, client, queue, origin, task_account, oauth_client):
        self.client, self.queue, self.origin = client, queue, origin
        self.task_account, self.oauth_client = task_account, oauth_client

    def enqueue(self, trip_id, *, recovery_id=None):
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import tasks_v2
        suffix = f"-{recovery_id}" if recovery_id else ""
        task = {"name": f"{self.queue}/tasks/{trip_id}{suffix}",
                "http_request": {"http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{self.origin}/internal/jobs/{trip_id}",
                    "headers": {"Content-Type": "application/json"}, "body": b"{}",
                    "oidc_token": {"service_account_email": self.task_account,
                                   "audience": self.oauth_client}},
                "dispatch_deadline": {"seconds": 60}}
        try:
            self.client.create_task(request={"parent": self.queue, "task": task}, timeout=10)
        except AlreadyExists:
            pass


class CloudJobs:
    def __init__(self, store, dispatcher):
        self.store, self.dispatcher = store, dispatcher

    def initialize(self):
        pass

    def check(self):
        self.store.get("healthcheck")

    def _create(self, text, event=None, conversation=None, case="success"):
        user = owner()
        trip_id = str(uuid5(NAMESPACE_URL, user + ":" + event)) if event else str(uuid4())
        timestamp = now()

        def create(previous):
            if previous:
                if previous["request_text"] != text or previous["case"] != case:
                    raise HTTPException(409, "Idempotency key already used with different input")
                return None, False
            return dict(trip_id=trip_id, owner=user, request_text=text, status="queued",
                        result_json=None, error=None, created_at=timestamp, updated_at=timestamp,
                        conversation=conversation, case=case, attempts=0, lease_until=0,
                        lease_id=None, stage="W kolejce", dispatched=False), True

        created = self.store.mutate(trip_id, create)
        job = self.store.get(trip_id)
        if job["status"] == "queued" and not job["dispatched"]:
            # Durable job is committed first. Same request/event retries reuse it
            # after enqueue failure. Named tasks tolerate ambiguous network success.
            self.dispatcher.enqueue(trip_id)
            def dispatched(value):
                value["dispatched"] = True
                return value, None
            self.store.mutate(trip_id, dispatched)
        return trip_id, created

    def create_trip(self, request_text, *, idempotency_key=None):
        return self._create(request_text, f"planner:{idempotency_key}" if idempotency_key else None)[0]

    def create_waha_trip(self, session, message_id, sender, text, demo_case=None):
        if session != "demo":
            raise HTTPException(403, "Real WhatsApp is disabled in cloud_demo")
        return self._create(text, f"demo:{message_id}", sender, demo_case or "success")

    def get_trip(self, trip_id):
        job = self.store.get(trip_id)
        if not job or job["owner"] != owner():
            return None
        return {key: job[key] for key in ("trip_id", "request_text", "status", "error", "created_at", "updated_at")} | {
            "result": json.loads(job["result_json"]) if job["result_json"] else None}

    def get_viewer(self, token):
        user = owner()
        for job in self.store.find("viewer_hash", token_hash(token)):
            if job["owner"] == user and job["status"] == "completed" and job["viewer_expires_at"] > time.time():
                return json.loads(job["result_json"])
        return None

    def demo_conversation(self, conversation):
        jobs = sorted((j for j in self.store.find("owner", owner()) if j.get("conversation") == conversation),
                      key=lambda j: (j["created_at"], j["trip_id"]))
        messages, statuses = [], []
        for job in jobs:
            messages.append({"id": f"{job['trip_id']}:ack",
                "text": f"Przyjęto prośbę. Numer zadania: {job['trip_id']}. Przygotowuję plan DEMO z przykładowymi danymi."})
            if job.get("notification"):
                messages.append({"id": f"{job['trip_id']}:result", "text": job["notification"]})
            statuses.append({key: job[key] for key in ("trip_id", "status", "error", "stage")} |
                            {"delivery_status": "sent" if job.get("notification") else None})
        return {"messages": messages, "jobs": statuses}

    def process(self, trip_id):
        lease = str(uuid4())

        def claim(job):
            if not job or job["status"] in {"completed", "failed"}:
                return None, None
            if job["lease_until"] > time.time():
                raise HTTPException(503, "Job lease is active; retry later")
            if job["attempts"] >= 3:
                job.update(status="failed", error="Processing retry limit exceeded", updated_at=now(),
                           stage="Błąd przygotowania planu", notification="Przekroczono limit ponowień zadania.")
                return job, None
            job.update(status="running", lease_id=lease, lease_until=time.time() + 120,
                       attempts=job["attempts"] + 1, updated_at=now(),
                       stage="Przygotowanie planu i mapy demonstracyjnej")
            return job, job.copy()

        job = self.store.mutate(trip_id, claim)
        if job is None:
            return
        from app.worker import generate_job_result
        from app.planning_providers import PlanningError
        try:
            result, token, expires = generate_job_result(job, job["case"])
            encoded = json.dumps(result, ensure_ascii=False)
            if len(encoded.encode()) > 800_000:
                raise PlanningError("Plan exceeds demonstration storage limit")
            # Exercise a durable delivery retry without creating an external side effect.
            if job["case"] == "delivery" and job["attempts"] == 1:
                def defer(value):
                    if value["lease_id"] != lease:
                        return None, None
                    value.update(status="queued", lease_until=0,
                                 stage="Symulowana awaria wysyłki — oczekiwanie na ponowienie")
                    return value, None
                self.store.mutate(trip_id, defer)
                raise HTTPException(503, "Simulated delivery retry")
            changes = dict(status="completed", result_json=encoded, viewer_hash=token_hash(token),
                           viewer_expires_at=expires, notification=result_summary(result),
                           stage="Odpowiedź dostarczona do symulatora" if job["conversation"] else "Plan gotowy")
        except PlanningError as exc:
            changes = dict(status="failed", error=str(exc), stage="Błąd przygotowania planu",
                           notification=f"Tripse: trip {trip_id} failed. {exc}")
        except HTTPException:
            raise
        except Exception as exc:
            # Keep the lease/attempt durable for bounded retry, and never return
            # provider bodies, storage internals or credentials to a caller.
            logger.warning("Cloud job %s interrupted (%s)", trip_id, type(exc).__name__)
            raise HTTPException(503, "Processing interrupted; retry after the job lease expires") from None

        def finish(current):
            # Fence stale processors after a timeout/redelivery. Completion and
            # simulator outbox commit together, so retries cannot duplicate messages.
            if current["status"] != "running" or current["lease_id"] != lease:
                return None, None
            current.update(changes, updated_at=now(), lease_until=0)
            return current, None
        self.store.mutate(trip_id, finish)

    def recover(self, trip_id):
        """Operator-only recovery after queue exhaustion; never resets terminal jobs."""
        job = self.store.get(trip_id)
        if job and job["status"] not in {"completed", "failed"} and job["lease_until"] < time.time():
            self.dispatcher.enqueue(trip_id, recovery_id=uuid4().hex)
            return True
        return False
