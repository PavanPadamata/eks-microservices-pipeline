terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.71.0" # exact version is pinned by .terraform.lock.hcl (committed)
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "eks-microservices-pipeline"
      ManagedBy = "terraform"
    }
  }
}
