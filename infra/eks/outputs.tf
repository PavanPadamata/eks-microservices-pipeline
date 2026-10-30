output "cluster_name" {
  value = module.eks.cluster_name
}

output "region" {
  value = var.region
}

output "ecr_repository_urls" {
  description = "Registry/repository URLs for docker push (the account ID is part of the URL; it is not stored in git)."
  value       = { for name, repo in aws_ecr_repository.service : name => repo.repository_url }
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region} --alias eks-ms-aws"
}
