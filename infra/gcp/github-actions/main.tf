# MANUAL BOOTSTRAP ONLY. Existing app resources must already be provisioned.
# No workflow invokes Terraform. Separate state from cloud-demo resources.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 8.7" }
  }
}
provider "google" {
  project = "tripse-ai"
  region  = "europe-central2"
}

variable "environments" {
  type    = set(string)
  default = ["dev"]
  validation {
    condition     = length(var.environments) > 0 && alltrue([for e in var.environments : contains(["dev", "prod"], e)])
    error_message = "Explicitly bootstrap dev and later prod."
  }
}
locals {
  project_number = "690165197462"
  repository     = "piotrbarabasz/tripse-ai-demo"
  repo_id        = "1430252241"
  owner_id       = "72949549"
  gh_env         = { dev = "development", prod = "production" }
  base_condition = "assertion.repository == '${local.repository}' && assertion.repository_id == '${local.repo_id}' && assertion.repository_owner_id == '${local.owner_id}' && assertion.event_name in ['push', 'workflow_dispatch']"
}

resource "google_project_service" "apis" {
  for_each           = toset(["iamcredentials.googleapis.com", "sts.googleapis.com"])
  service            = each.value
  disable_on_destroy = false
}
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "tripse-github"
  display_name              = "TRIPSE repository only"
  lifecycle { prevent_destroy = true }
  depends_on = [google_project_service.apis]
}
resource "google_iam_workload_identity_pool_provider" "github" {
  for_each                           = var.environments
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-${each.key}"
  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
    "attribute.environment"         = "assertion.environment"
  }
  attribute_condition = join(" && ", [
    local.base_condition,
    "assertion.sub == 'repo:${local.repository}:environment:${local.gh_env[each.key]}'",
    "assertion.environment == '${local.gh_env[each.key]}'",
    each.key == "prod" ? "assertion.ref == 'refs/heads/master'" : "((assertion.event_name == 'push' && assertion.ref in ['refs/heads/dev', 'refs/heads/master']) || (assertion.event_name == 'workflow_dispatch' && assertion.ref.startsWith('refs/heads/')))",
    "assertion.workflow_ref == '${local.repository}/.github/workflows/delivery.yml@' + assertion.ref"
  ])
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}
resource "google_service_account" "deploy" {
  for_each     = var.environments
  account_id   = "tripse-ai-${each.key}-ci-deploy"
  display_name = "TRIPSE ${each.key} GitHub deployer"
  lifecycle { prevent_destroy = true }
}
resource "google_service_account" "probe" {
  for_each     = var.environments
  account_id   = "tripse-ai-${each.key}-ci-probe"
  display_name = "TRIPSE ${each.key} CI application probe"
  lifecycle { prevent_destroy = true }
}
resource "google_service_account_iam_member" "federation" {
  for_each           = var.environments
  service_account_id = google_service_account.deploy[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.environment/${local.gh_env[each.key]}"
}

# Metadata inspection only: no document bytes, database entities or secret payloads.
resource "google_project_iam_custom_role" "inspect" {
  role_id = "tripseCiInspect"
  title   = "TRIPSE CI prerequisite metadata"
  permissions = [
    "serviceusage.services.use",
    "resourcemanager.projects.get", "resourcemanager.projects.getIamPolicy",
    "run.services.get", "run.services.list", "run.services.getIamPolicy", "run.locations.list",
    "run.revisions.get", "run.revisions.list", "run.operations.get",
    "artifactregistry.repositories.get", "artifactregistry.repositories.list",
    "storage.buckets.get", "storage.buckets.getIamPolicy",
    "datastore.databases.get", "datastore.databases.getMetadata",
    "cloudtasks.queues.get", "cloudtasks.queues.getIamPolicy",
    "iam.serviceAccounts.get", "iam.serviceAccounts.getIamPolicy",
    "iap.webServices.getIamPolicy", "iap.web.getSettings"
  ]
}
resource "google_project_iam_member" "inspect" {
  for_each = var.environments
  project  = "tripse-ai"
  role     = google_project_iam_custom_role.inspect.name
  member   = "serviceAccount:${google_service_account.deploy[each.key].email}"
}
# Existing deploy.py changes invoker IAM/access and traffic. Scope admin to only
# the selected existing service; do not grant project-wide Cloud Run Admin.
resource "google_cloud_run_v2_service_iam_member" "deploy" {
  for_each = var.environments
  name     = "tripse-ai-${each.key}"
  location = "europe-central2"
  role     = "roles/run.admin"
  member   = "serviceAccount:${google_service_account.deploy[each.key].email}"
}
resource "google_artifact_registry_repository_iam_member" "read" {
  for_each   = var.environments
  repository = "tripse-ai"
  location   = "europe-central2"
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.deploy[each.key].email}"
}
resource "google_service_account_iam_member" "runtime" {
  for_each           = var.environments
  service_account_id = "projects/tripse-ai/serviceAccounts/tripse-ai-${each.key}@tripse-ai.iam.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy[each.key].email}"
}
resource "google_service_account_iam_member" "sign_probe" {
  for_each           = var.environments
  service_account_id = google_service_account.probe[each.key].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.deploy[each.key].email}"
}
resource "google_cloud_run_v2_service_iam_member" "probe_invoker" {
  for_each = var.environments
  name     = "tripse-ai-${each.key}"
  location = "europe-central2"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.probe[each.key].email}"
}
resource "google_iap_web_cloud_run_service_iam_member" "probe" {
  for_each               = var.environments
  cloud_run_service_name = "tripse-ai-${each.key}"
  location               = "europe-central2"
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = "serviceAccount:${google_service_account.probe[each.key].email}"
}

# Only DEV can submit builds or act as the existing build identity.
resource "google_project_iam_custom_role" "build" {
  role_id     = "tripseCiBuild"
  title       = "TRIPSE CI Cloud Build submit and wait"
  permissions = ["cloudbuild.builds.create", "cloudbuild.builds.get", "cloudbuild.builds.list", "serviceusage.services.use"]
}
resource "google_project_iam_member" "build" {
  count   = contains(var.environments, "dev") ? 1 : 0
  project = "tripse-ai"
  role    = google_project_iam_custom_role.build.name
  member  = "serviceAccount:${google_service_account.deploy["dev"].email}"
}
resource "google_service_account_iam_member" "builder" {
  count              = contains(var.environments, "dev") ? 1 : 0
  service_account_id = "projects/tripse-ai/serviceAccounts/tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy["dev"].email}"
}
resource "google_storage_bucket_iam_member" "source" {
  for_each = contains(var.environments, "dev") ? toset(["roles/storage.objectCreator", "roles/storage.objectViewer"]) : toset([])
  bucket   = "tripse-ai_europe-central2_cloudbuild"
  role     = each.key
  member   = "serviceAccount:${google_service_account.deploy["dev"].email}"
}

output "environments" {
  value = { for e in var.environments : local.gh_env[e] => {
    WIF_PROVIDER           = google_iam_workload_identity_pool_provider.github[e].name
    DEPLOY_SERVICE_ACCOUNT = google_service_account.deploy[e].email
    CI_PROBE_ACCOUNT       = google_service_account.probe[e].email
  } }
}
