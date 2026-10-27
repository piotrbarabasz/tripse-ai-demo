# Additive opt-in resources only. Existing Cloud Run services/images remain owned
# by scripts/gcp/deployment.py. Use a separate reviewed state for each environment.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 8.7" }
  }
}

variable "project_id" { type = string }
variable "project_number" { type = string }
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Use dev or prod and a separate state."
  }
}
variable "manage_project_apis" {
  type        = bool
  default     = true
  description = "Only the existing DEV state owns shared project API enablement. PROD reuses enabled APIs."
}
variable "demo_members" {
  type        = set(string)
  description = "Explicit user:email principals; mirror DEMO_READERS/DEMO_EDITORS."
  validation {
    condition     = length(var.demo_members) > 0 && alltrue([for m in var.demo_members : can(regex("^user:[^@]+@[^@]+$", m))])
    error_message = "At least one explicit user principal is required."
  }
}
variable "live_secret_ids" {
  type        = set(string)
  default     = []
  description = "Optional existing Secret Manager secret IDs for later reviewed live mode; no values/versions in state."
}

provider "google" {
  project = var.project_id
  region  = "europe-central2"
}

locals {
  service = "tripse-ai-${var.environment}"
  runtime = "serviceAccount:${local.service}@${var.project_id}.iam.gserviceaccount.com"
  labels  = { app = "tripse-ai", managed-by = "tripse-scripts", environment = var.environment }
}

resource "google_project_service" "apis" {
  for_each           = var.manage_project_apis ? toset(["storage.googleapis.com", "firestore.googleapis.com", "cloudtasks.googleapis.com", "iap.googleapis.com", "secretmanager.googleapis.com"]) : toset([])
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-${local.service}-documents"
  location                    = "europe-central2"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
  versioning { enabled = true }
  soft_delete_policy { retention_duration_seconds = 604800 }
  lifecycle_rule {
    condition { num_newer_versions = 20 }
    action { type = "Delete" }
  }
  lifecycle { prevent_destroy = true }
  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "runtime" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectUser"
  member = local.runtime
}

resource "google_firestore_database" "jobs" {
  name                              = local.service
  location_id                       = "europe-central2"
  type                              = "FIRESTORE_NATIVE"
  concurrency_mode                  = "PESSIMISTIC"
  delete_protection_state           = "DELETE_PROTECTION_ENABLED"
  deletion_policy                   = "ABANDON"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
  lifecycle { prevent_destroy = true }
  depends_on = [google_project_service.apis]
}

# Exclude potentially large/private plan text from automatic single-field indexes.
resource "google_firestore_field" "unindexed" {
  for_each   = toset(["result_json", "request_text", "notification", "error", "stage"])
  database   = google_firestore_database.jobs.name
  collection = "jobs"
  field      = each.value
  index_config {}
}

resource "google_project_iam_member" "database_runtime" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = local.runtime
  condition {
    title      = "${local.service}-database-only"
    expression = "resource.name == 'projects/${var.project_id}/databases/${local.service}'"
  }
}

resource "google_cloud_tasks_queue" "jobs" {
  name     = local.service
  location = "europe-central2"
  rate_limits {
    max_dispatches_per_second = 1
    max_concurrent_dispatches = 2
  }
  retry_config {
    max_attempts       = 12
    max_retry_duration = "3600s"
    min_backoff        = "30s"
    max_backoff        = "300s"
    max_doublings      = 3
  }
  lifecycle { prevent_destroy = true }
  depends_on = [google_project_service.apis]
}

resource "google_cloud_tasks_queue_iam_member" "enqueue" {
  name     = google_cloud_tasks_queue.jobs.name
  location = google_cloud_tasks_queue.jobs.location
  role     = "roles/cloudtasks.enqueuer"
  member   = local.runtime
}

resource "google_service_account" "task" {
  account_id   = "${local.service}-tasks"
  display_name = "TRIPSE ${var.environment} authenticated tasks"
  lifecycle { prevent_destroy = true }
}

resource "google_service_account_iam_member" "runtime_act_as" {
  service_account_id = google_service_account.task.name
  role               = "roles/iam.serviceAccountUser"
  member             = local.runtime
}

# Cloud Tasks service agent mints OIDC tokens for this dedicated caller only.
resource "google_service_account_iam_member" "task_token" {
  service_account_id = google_service_account.task.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${var.project_number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"
  depends_on         = [google_project_service.apis]
}

# These additive bindings require the existing service and IAP service agent.
# Bootstrap the custom external OAuth client via Console before applying them.
resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  name       = local.service
  location   = "europe-central2"
  role       = "roles/run.invoker"
  member     = "serviceAccount:service-${var.project_number}@gcp-sa-iap.iam.gserviceaccount.com"
  depends_on = [google_project_service.apis]
}

resource "google_iap_web_cloud_run_service_iam_member" "members" {
  for_each               = var.demo_members
  cloud_run_service_name = local.service
  location               = "europe-central2"
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = each.value
  depends_on             = [google_project_service.apis]
}

resource "google_iap_web_cloud_run_service_iam_member" "task" {
  cloud_run_service_name = local.service
  location               = "europe-central2"
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = "serviceAccount:${google_service_account.task.email}"
  depends_on             = [google_project_service.apis]
}

# References and IAM only. No secret data in dotenv, source or Terraform state.
resource "google_secret_manager_secret_iam_member" "live" {
  for_each  = var.live_secret_ids
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = local.runtime
  lifecycle {
    precondition {
      condition     = startswith(each.value, "${local.service}-")
      error_message = "Secret IDs must be prefixed with the selected environment service."
    }
  }
}

output "document_bucket" { value = google_storage_bucket.documents.name }
output "firestore_database" { value = google_firestore_database.jobs.name }
output "task_queue" { value = google_cloud_tasks_queue.jobs.id }
output "task_account" { value = google_service_account.task.email }
