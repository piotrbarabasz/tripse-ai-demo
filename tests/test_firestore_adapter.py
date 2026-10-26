"""Real Firestore SDK transactions/protobufs with an in-process RPC boundary.

Exercises SDK retry and query behavior without credentials, gRPC or GCP.
"""
from uuid import uuid4

import pytest
from google.auth.credentials import AnonymousCredentials
from google.api_core.exceptions import Aborted
from google.cloud import firestore
from google.cloud.firestore_v1 import _helpers, types

from app.cloud_jobs import FirestoreJobStore
from app.document_studio.repository import StorageError


class RPC:
    def __init__(self):
        self.docs, self.commits, self.rollbacks = {}, 0, 0
        self.conflict_once, self.always_abort = False, False

    def begin_transaction(self, *, request, **kwargs):
        assert request["database"] == "projects/tripse-test-123/databases/tripse-ai-dev"
        return types.BeginTransactionResponse(transaction=uuid4().bytes)

    def batch_get_documents(self, *, request, **kwargs):
        name = request["documents"][0]
        if name in self.docs:
            return iter([types.BatchGetDocumentsResponse(found=types.Document(name=name, fields=_helpers.encode_dict(self.docs[name])))])
        return iter([types.BatchGetDocumentsResponse(missing=name)])

    def commit(self, *, request, **kwargs):
        self.commits += 1
        if self.always_abort:
            raise Aborted("simulated transaction conflict")
        if self.conflict_once:
            self.conflict_once = False
            name = request["writes"][0].update.name
            self.docs[name]["attempts"] = 5
            raise Aborted("another instance committed first")
        for write in request["writes"]:
            self.docs[write.update.name] = _helpers.decode_dict(write.update.fields, None)
        return types.CommitResponse()

    def rollback(self, **kwargs):
        self.rollbacks += 1

    def run_query(self, *, request, **kwargs):
        query = request["structured_query"]
        field = query.where.field_filter.field.field_path
        value = _helpers.decode_value(query.where.field_filter.value, None)
        return iter(types.RunQueryResponse(document=types.Document(name=name, fields=_helpers.encode_dict(doc)))
                    for name, doc in self.docs.items() if doc.get(field) == value)


def adapter():
    client = firestore.Client(project="tripse-test-123", database="tripse-ai-dev", credentials=AnonymousCredentials())
    rpc = RPC()
    client._firestore_api_internal = rpc
    return FirestoreJobStore(client), rpc


def test_firestore_sdk_retries_with_fresh_snapshot_and_queries_owner():
    store, rpc = adapter()
    assert store.get("missing") is None
    store.mutate("job", lambda previous: ({"owner": "alice", "attempts": 1}, "created"))
    rpc.conflict_once = True
    seen = []
    def increment(previous):
        seen.append(previous["attempts"])
        previous["attempts"] += 1
        return previous, previous["attempts"]
    assert store.mutate("job", increment) == 6
    assert seen == [1, 5]
    assert store.get("job")["attempts"] == 6
    store.mutate("other", lambda _: ({"owner": "bob", "attempts": 0}, None))
    assert store.find("owner", "alice") == [{"owner": "alice", "attempts": 6}]
    assert store.find("owner", "unknown") == []


def test_exhausted_firestore_sdk_retry_is_storage_error_and_rolls_back():
    store, rpc = adapter()
    rpc.always_abort = True
    with pytest.raises(StorageError, match="retry limit"):
        store.mutate("job", lambda _: ({"owner": "alice"}, None))
    assert rpc.commits == 5 and rpc.rollbacks == 1
    assert store.get("job") is None
