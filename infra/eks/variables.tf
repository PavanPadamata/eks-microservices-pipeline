variable "region" {
  description = "AWS region."
  type        = string
  default     = "eu-central-1"
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "eks-microservices"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. Keep it in standard support: extended support costs extra per cluster hour."
  type        = string
  default     = "1.36" # standard support until 2027-08-02 per the AWS EKS version calendar
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_type" {
  description = "Instance type of the managed node group."
  type        = string
  default     = "t3.medium"
}

variable "node_count" {
  description = "Number of worker nodes (fixed; there is no cluster autoscaler)."
  type        = number
  default     = 2
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT. SPOT is cheaper but nodes can be reclaimed during a demo."
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "node_capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "api_allowed_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint. Restrict this to your own IP, e.g. [\"203.0.113.7/32\"]."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ecr_repositories" {
  description = "ECR repositories to create (must match services/* image names used by the chart)."
  type        = list(string)
  default     = ["eks-microservices/api", "eks-microservices/worker"]
}
