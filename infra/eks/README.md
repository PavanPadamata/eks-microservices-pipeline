# EKS (AWS): bring up, deploy, screenshot, destroy

> **This costs real money while it exists.** The EKS control plane alone is about **$0.10 per hour**
> (check the current price on the [EKS pricing page](https://aws.amazon.com/eks/pricing/)), and the two worker nodes
> are billed on top. Bring it up, take your screenshots, destroy it the same session.

## Status of this code

`terraform fmt` and `terraform validate` pass, and the module arguments were checked against the pinned module
versions. **It has not been applied by the author of this repo yet**: no AWS account was available while writing it,
and `terraform plan` needs credentials. Treat the first `make eks-apply` as the first real test, and record any
fix it needs. The screenshots and timings below are therefore `TODO(measure)`.

## What gets created

| Resource | Notes |
|---|---|
| VPC, 2 public subnets in 2 AZs, internet gateway | `terraform-aws-modules/vpc` 6.7.3. **No NAT gateway** (it bills per hour and per GB). |
| EKS cluster, Kubernetes 1.36 | `terraform-aws-modules/eks` 21.29.0. 1.36 is in standard support until 2027-08-02; versions in extended support cost extra per hour. |
| Managed node group: 2 x `t3.medium`, on-demand | Fixed size, no cluster autoscaler. `node_capacity_type = "SPOT"` is cheaper but nodes can be reclaimed mid-demo. |
| 2 ECR repositories (`eks-microservices/api`, `/worker`) | Scan on push, keeps the last 10 images, `force_delete` so destroy works with images present. |

Deliberately **not** created, to keep cost and cleanup simple: NAT gateway, load balancers, control-plane log group,
customer-managed KMS key, persistent volumes. Traefik runs as a `ClusterIP` Service and you reach it with a
port-forward, so nothing outside Terraform's knowledge can block `terraform destroy`.

## Prerequisites

- An AWS account you are allowed to spend in. Use a **sandbox/personal account**, not a shared or production one:
  applying this creates VPC, EKS, IAM roles and ECR resources, which needs broad permissions.
- Credentials available to the AWS CLI in your shell (`aws configure sso`, a named profile, ...). Check with
  `aws sts get-caller-identity`. Never put keys in this repo; `.env`, `*.tfvars`, state and plans are gitignored.
- `terraform` (~> 1.9), `aws` CLI v2, `kubectl`, `helm`, `docker`.
- **Set a billing alarm first**: an [AWS Budget](https://console.aws.amazon.com/billing/home#/budgets) with an
  email alert at a small amount protects you if you forget to destroy.
- Copy `infra/eks/terraform.tfvars.example` to `terraform.tfvars` and set `api_allowed_cidrs` to your own IP
  (`["x.x.x.x/32"]`). The default `0.0.0.0/0` leaves the Kubernetes API endpoint reachable from anywhere (still
  IAM-protected, but not something to leave open).

## Bring up

```bash
make eks-init
make eks-plan          # read it: it should only create resources
make eks-apply         # BILLING STARTS; type "yes" to confirm
make eks-kubeconfig    # adds context "eks-ms-aws" to ~/.kube/config
make eks-bootstrap     # Traefik (ClusterIP) + metrics-server, needed for ingress and the HPA
```

Whoever runs `terraform apply` becomes cluster admin through an EKS access entry. Jenkins (below) works only if its
AWS credentials belong to the same IAM identity.

## Deploy

Directly from your machine:

```bash
make eks-push          # builds both images and pushes them to ECR, tagged with the git SHA
make eks-deploy        # helm upgrade --install with values-eks.yaml and the ECR image names
make eks-status
make eks-port-forward  # then: curl 'http://localhost:8088/compute?n=10'
make eks-monitoring    # optional: same monitoring stack as on kind
```

Or through the Jenkins pipeline (see the main README for the stage table):

1. In Jenkins add a credential `aws-credentials` of kind *Username with password* (AWS access key ID as username,
   secret access key as password). Long-lived keys are acceptable for a short demo, not for real use.
2. Make sure `api_allowed_cidrs` includes the public IP your machine reaches AWS from (the Jenkins container uses it).
3. Run the job with `TARGET=eks`, `ECR_REGISTRY=<terraform output ecr_repository_urls, host part>`, and the
   region/cluster name. The account ID in the registry host is entered at run time and never stored in git.

For Grafana on EKS: `make grafana KCTX=eks-ms-aws` (the monitoring targets take the kube-context as `KCTX`).

## Destroy (do this before you stop)

```bash
make eks-destroy       # uninstalls the Helm releases, refuses to continue if any LoadBalancer Service exists,
                       # then runs terraform destroy (type "yes")
make eks-leftovers     # every list it prints should be empty
```

Why the extra step: Kubernetes objects such as a `LoadBalancer` Service create AWS resources (ELB, ENIs) that
Terraform does not manage. They keep the VPC from deleting, and they keep billing. Always clean up the cluster
contents first. If `terraform destroy` fails on a dependency, the usual cause is exactly that: look for leftover
load balancers or network interfaces in the VPC, delete them, and run destroy again.

Afterwards, also check the **Billing and Cost Management** console the next day. Cost data lags, and it is the
only authoritative number.

## Cost note

- Control plane: about $0.10/hour (see the pricing link above; it is higher for a version in extended support).
- Nodes: 2 x `t3.medium` on-demand, billed per second while running. Look up the current `eu-central-1` price.
- Smaller items: EBS root volumes of the nodes, public IPv4 addresses on the nodes (AWS bills these per hour),
  ECR storage, data transfer.
- Rough formula for a session: `hours x (0.10 + 2 x node price + small items)`.

| Measured value | Source | Value |
|---|---|---|
| `terraform apply` duration | `time make eks-apply` (excluding the time you take to type "yes") | TODO(measure) |
| `terraform destroy` duration | `time make eks-destroy` | TODO(measure) |
| Total session length | your clock | TODO(measure) |
| What AWS actually billed for the session | Cost Explorer, grouped by service, the day after | TODO(measure) |

## Known limitations (not production-ready)

- Nodes sit in **public subnets** with public IPs to avoid a NAT gateway. Production would use private subnets
  plus NAT or VPC endpoints.
- The Kubernetes API endpoint is public (restricted only by `api_allowed_cidrs`).
- No control-plane logging, no customer-managed encryption key, no cluster autoscaler, no node auto-repair tuning.
- State is local (`terraform.tfstate`, gitignored): no remote backend, no locking. Fine for a one-person,
  one-session demo; lose the file and you have to clean up by hand with `make eks-leftovers`.
- The monitoring stack has no persistence and no Alertmanager, as on kind.
- Traefik is reached through a port-forward, not a public load balancer.
