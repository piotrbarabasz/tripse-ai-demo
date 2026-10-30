# Isolated, operator-only import/removal. Never apply with an empty/unreviewed state.
# See README.md: import with retain=true, then review a retain=false removal plan.
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

variable "retain_legacy_default_worker_grant" {
  type        = bool
  default     = false
  description = "Import-only switch for the existing numeric legacy worker grant. Final false removes only the imported member."
}

resource "google_project_iam_member" "legacy_default_worker" {
  count   = var.retain_legacy_default_worker_grant ? 1 : 0
  project = "tripse-ai"
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:690165197462@cloudbuild.gserviceaccount.com"
}
