data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2) # two AZs
}

# Cost choice: public subnets only and no NAT gateway (a NAT gateway bills per hour plus per GB).
# Nodes get public IPs but the node security group allows no inbound traffic from the internet.
# This is NOT how a production cluster is laid out; see the README limitations.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name = var.cluster_name
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets     = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i)]
  enable_nat_gateway = false

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

  name               = var.cluster_name
  kubernetes_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnets

  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.api_allowed_cidrs

  # Whoever runs `terraform apply` becomes cluster admin (EKS access entry).
  enable_cluster_creator_admin_permissions = true

  # No control-plane logging and no customer-managed KMS key: both add cost, and a KMS key
  # lingers in "pending deletion" after destroy. (The module creates a log group by default
  # even with no log types enabled, so that is switched off explicitly.)
  enabled_log_types           = []
  create_cloudwatch_log_group = false
  create_kms_key              = false
  encryption_config           = null

  addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
    }
  }

  eks_managed_node_groups = {
    default = {
      instance_types = [var.node_instance_type]
      capacity_type  = var.node_capacity_type
      min_size       = var.node_count
      max_size       = var.node_count + 1
      desired_size   = var.node_count
    }
  }
}
