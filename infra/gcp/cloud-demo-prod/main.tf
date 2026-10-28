# Separate PROD root/state. Never initialize with the DEV cloud-demo state.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 8.7" }
  }
}

module "cloud_demo" {
  source              = "../cloud-demo"
  project_id          = "tripse-ai"
  project_number      = "690165197462"
  environment         = "prod"
  manage_project_apis = false
  demo_members = [
    "user:kontakt@protolume.pl",
    "user:barabasz.piotrek@gmail.com",
    "user:tripse.kontakt@gmail.com",
  ]
  live_secret_ids = []
}

output "document_bucket" { value = module.cloud_demo.document_bucket }
output "firestore_database" { value = module.cloud_demo.firestore_database }
output "task_queue" { value = module.cloud_demo.task_queue }
output "task_account" { value = module.cloud_demo.task_account }
