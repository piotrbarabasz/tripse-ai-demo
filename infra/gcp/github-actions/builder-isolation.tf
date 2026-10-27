# The DEV deployer can execute arbitrary reviewed branch code as this builder.
# It must not inherit project-wide document-bucket access before PROD has data.
variable "retain_legacy_builder_grant" {
  type        = bool
  default     = false
  description = "Temporary import-only switch. Final reviewed plan must remove the old builder project role."
}

# Import the existing exact member with the temporary switch=true; final false
# removes only that member, never the builder identity or another role member.
resource "google_project_iam_member" "legacy_builder" {
  count   = var.retain_legacy_builder_grant ? 1 : 0
  project = "tripse-ai"
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
}

resource "google_project_iam_custom_role" "builder_metadata" {
  role_id     = "tripseBuildMetadata"
  title       = "TRIPSE builder project metadata and logging only"
  permissions = ["resourcemanager.projects.get", "serviceusage.services.use", "logging.logEntries.create"]
}
resource "google_project_iam_member" "builder_metadata" {
  project = "tripse-ai"
  role    = google_project_iam_custom_role.builder_metadata.name
  member  = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
}
resource "google_project_iam_custom_role" "builder_bucket_metadata" {
  role_id     = "tripseBuildBucketMetadata"
  title       = "TRIPSE builder exact bucket metadata"
  permissions = ["storage.buckets.get"]
}
resource "google_storage_bucket_iam_member" "builder_bucket_metadata" {
  for_each = toset(["tripse-ai_europe-central2_cloudbuild", "690165197462-europe-central2-cloudbuild-logs"])
  bucket   = each.key
  role     = google_project_iam_custom_role.builder_bucket_metadata.name
  member   = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
}
resource "google_storage_bucket_iam_member" "builder_source" {
  bucket = "tripse-ai_europe-central2_cloudbuild"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
}
resource "google_storage_bucket_iam_member" "builder_logs" {
  bucket = "690165197462-europe-central2-cloudbuild-logs"
  role   = "roles/storage.objectUser"
  member = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
}
resource "google_project_iam_custom_role" "builder_registry" {
  role_id = "tripseBuildRegistryPush"
  title   = "TRIPSE builder registry push without deletion"
  permissions = [
    "artifactregistry.repositories.get", "artifactregistry.repositories.uploadArtifacts",
    "artifactregistry.repositories.downloadArtifacts", "artifactregistry.tags.create", "artifactregistry.tags.update",
    "artifactregistry.tags.get", "artifactregistry.tags.list", "artifactregistry.packages.get",
    "artifactregistry.versions.get", "artifactregistry.versions.list"
  ]
}
resource "google_artifact_registry_repository_iam_member" "builder_push" {
  project    = "tripse-ai"
  repository = "tripse-ai"
  location   = "europe-central2"
  role       = google_project_iam_custom_role.builder_registry.name
  member     = "serviceAccount:tripse-ai-build@tripse-ai.iam.gserviceaccount.com"
}
