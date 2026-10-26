"""Explicit authenticated demo configuration. No implicit local storage fallback."""
import os
import re
from dataclasses import dataclass

from app.cloud_access import CloudAccess, IAPVerifier


def members(value):
    result = frozenset(item.strip().lower() for item in value.split("|") if item.strip())
    if any(not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{}~-]+@[a-z0-9.-]+\.[a-z]{2,}", item) for item in result):
        raise ValueError("Invalid demo member email")
    return result


@dataclass(frozen=True)
class DemoSettings:
    project: str
    audience: str
    origin: str
    bucket: str
    database: str
    queue: str
    task_account: str
    oauth_client: str
    readers: frozenset[str]
    editors: frozenset[str]

    @classmethod
    def from_env(cls, cloud, env=None):
        env = os.environ if env is None else env
        project, number = env.get("GCP_PROJECT_ID", ""), env.get("GCP_PROJECT_NUMBER", "")
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project) or not re.fullmatch(r"[0-9]{6,}", number):
            raise ValueError("cloud_demo requires project ID and project number")
        origin = env.get("PUBLIC_BASE_URL", "")
        if not re.fullmatch(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.run\.app", origin):
            raise ValueError("cloud_demo requires its exact HTTPS run.app origin")
        environment = cloud.environment
        expected = {
            "GCP_DOCUMENT_BUCKET": f"{project}-tripse-ai-{environment}-documents",
            "GCP_FIRESTORE_DATABASE": f"tripse-ai-{environment}",
            "GCP_TASK_QUEUE": f"projects/{project}/locations/europe-central2/queues/tripse-ai-{environment}",
            "GCP_TASK_ACCOUNT": f"tripse-ai-{environment}-tasks@{project}.iam.gserviceaccount.com",
        }
        if any(env.get(key) != value for key, value in expected.items()):
            raise ValueError("Cloud data resources must match the selected environment")
        oauth_client = env.get("IAP_OAUTH_CLIENT_ID", "")
        if not re.fullmatch(r"[a-zA-Z0-9-]+\.apps\.googleusercontent\.com", oauth_client):
            raise ValueError("Explicit IAP OAuth client for task OIDC required")
        editors, readers = members(env.get("DEMO_EDITORS", "")), members(env.get("DEMO_READERS", ""))
        if not editors or expected["GCP_TASK_ACCOUNT"] in editors | readers:
            raise ValueError("At least one human editor and a separate task identity are required")
        if any(env.get(key) for key in ("FIRESTORE_EMULATOR_HOST", "STORAGE_EMULATOR_HOST", "CLOUD_TASKS_EMULATOR_HOST")):
            raise ValueError("Emulator endpoints are forbidden in cloud_demo")
        return cls(project,
            f"/projects/{number}/locations/europe-central2/services/{cloud.service}", origin,
            expected["GCP_DOCUMENT_BUCKET"], expected["GCP_FIRESTORE_DATABASE"],
            expected["GCP_TASK_QUEUE"], expected["GCP_TASK_ACCOUNT"], oauth_client, readers, editors)


@dataclass
class CloudComponents:
    repository: object
    assets: object
    jobs: object
    access: CloudAccess


def build_components(settings):
    # SDKs and ADC are only used for an explicitly selected, validated cloud_demo.
    from google.cloud import storage, firestore, tasks_v2
    from app.document_studio.assets import AssetStore
    from app.document_studio.cloud_storage import GCSRepository, GCSAssetBytes
    from app.cloud_jobs import CloudJobs, FirestoreJobStore, CloudTaskDispatcher
    bucket = storage.Client(project=settings.project).bucket(settings.bucket)
    repository = GCSRepository(bucket)
    jobs = CloudJobs(FirestoreJobStore(firestore.Client(project=settings.project, database=settings.database)),
        CloudTaskDispatcher(tasks_v2.CloudTasksClient(), settings.queue, settings.origin,
                            settings.task_account, settings.oauth_client))
    return CloudComponents(repository, AssetStore(repository, GCSAssetBytes(bucket)), jobs,
        CloudAccess(settings.origin, settings.readers, settings.editors,
                    IAPVerifier(settings.audience), settings.task_account))
