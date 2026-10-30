# EKS workflow. A running cluster costs real money: read infra/eks/README.md before `make eks-apply`.
# Needs AWS credentials in your environment (profile/SSO), never in this repo.
EKS_DIR         := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
EKS_ROOT        := $(abspath $(EKS_DIR)/../..)
AWS_REGION      ?= eu-central-1
EKS_CLUSTER     ?= eks-microservices
EKS_CTX         ?= eks-ms-aws
IMAGE_NAMESPACE ?= eks-microservices
EKS_TAG         ?= $(shell git -C $(EKS_ROOT) rev-parse --short=8 HEAD)
EKS_RELEASE     ?= microservices
EKS_NAMESPACE   ?= microservices

TF          := terraform -chdir=$(EKS_DIR)
EKS_KUBECTL := kubectl --context $(EKS_CTX)
EKS_HELM    := helm --kube-context $(EKS_CTX)
# Resolved at run time inside recipes, so the account ID never lands in a file or in `make help`.
REGISTRY    := $$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$(AWS_REGION).amazonaws.com

.PHONY: eks-init eks-plan eks-apply eks-kubeconfig eks-bootstrap eks-push eks-deploy eks-monitoring \
        eks-status eks-port-forward eks-cleanup eks-destroy eks-leftovers

eks-init: ## terraform init
	$(TF) init

eks-plan: ## terraform plan (creates nothing)
	$(TF) plan

eks-apply: ## create VPC + EKS + ECR (BILLING STARTS; asks for confirmation)
	$(TF) apply

eks-kubeconfig: ## add the cluster to ~/.kube/config as context eks-ms-aws
	aws eks update-kubeconfig --name $(EKS_CLUSTER) --region $(AWS_REGION) --alias $(EKS_CTX)

eks-bootstrap: ## install Traefik (ClusterIP) and metrics-server on EKS
	helm repo add traefik https://traefik.github.io/charts >/dev/null
	helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
	helm repo update >/dev/null
	$(EKS_HELM) upgrade --install traefik traefik/traefik --version $(TRAEFIK_CHART_VERSION) \
	  -n traefik --create-namespace -f $(EKS_DIR)/traefik-values.yaml --wait --timeout 5m
	$(EKS_HELM) upgrade --install metrics-server metrics-server/metrics-server --version $(METRICS_SERVER_CHART_VERSION) \
	  -n kube-system --wait --timeout 5m

eks-push: ## build both images and push them to ECR, tagged with the git SHA
	@REG=$(REGISTRY); set -e; \
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $$REG; \
	for svc in api worker; do \
	  docker build -t $$REG/$(IMAGE_NAMESPACE)/$$svc:$(EKS_TAG) $(EKS_ROOT)/services/$$svc; \
	  docker push $$REG/$(IMAGE_NAMESPACE)/$$svc:$(EKS_TAG); \
	done; \
	docker logout $$REG

eks-deploy: ## helm upgrade --install the chart on EKS using the ECR images
	@REG=$(REGISTRY); set -e; \
	$(EKS_HELM) upgrade --install $(EKS_RELEASE) $(EKS_ROOT)/charts/microservices -n $(EKS_NAMESPACE) --create-namespace \
	  -f $(EKS_ROOT)/charts/microservices/values-eks.yaml \
	  --set services.api.image.repository=$$REG/$(IMAGE_NAMESPACE)/api --set services.api.image.tag=$(EKS_TAG) \
	  --set services.worker.image.repository=$$REG/$(IMAGE_NAMESPACE)/worker --set services.worker.image.tag=$(EKS_TAG) \
	  --wait --rollback-on-failure --timeout 5m

eks-monitoring: ## install the monitoring stack on EKS (same values as kind)
	$(MAKE) monitoring-up KCTX=$(EKS_CTX)

eks-status: ## nodes, pods, HPAs and ingress
	$(EKS_KUBECTL) get nodes
	$(EKS_KUBECTL) -n $(EKS_NAMESPACE) get pods,hpa,ingress

eks-port-forward: ## reach the api through Traefik on http://localhost:8088 (kind uses 8080)
	$(EKS_KUBECTL) -n traefik port-forward svc/traefik 8088:80

eks-cleanup: ## uninstall everything Kubernetes created, so terraform destroy cannot hang on stray load balancers
	-$(EKS_HELM) uninstall $(EKS_RELEASE) -n $(EKS_NAMESPACE)
	-$(EKS_HELM) uninstall kube-prometheus-stack -n monitoring
	-$(EKS_HELM) uninstall traefik -n traefik
	-$(EKS_HELM) uninstall metrics-server -n kube-system
	@n=$$($(EKS_KUBECTL) get svc -A -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.name}{"\n"}{end}' | wc -l); \
	if [ "$$n" -ne 0 ]; then echo "LoadBalancer Services still exist; delete them first or destroy will hang on their ENIs"; exit 1; fi

eks-destroy: eks-cleanup ## STOP BILLING: remove Kubernetes objects, then terraform destroy (asks for confirmation)
	$(TF) destroy

eks-leftovers: ## list billable things that may remain after destroy (all should print empty lists)
	@echo "EKS clusters:";        aws eks list-clusters --region $(AWS_REGION) --query clusters --output text
	@echo "VPCs tagged for this project:"; aws ec2 describe-vpcs --region $(AWS_REGION) --filters Name=tag:Project,Values=eks-microservices-pipeline --query 'Vpcs[].VpcId' --output text
	@echo "ECR repositories:";    aws ecr describe-repositories --region $(AWS_REGION) --query "repositories[?starts_with(repositoryName,'$(IMAGE_NAMESPACE)/')].repositoryName" --output text
	@echo "Classic load balancers:"; aws elb describe-load-balancers --region $(AWS_REGION) --query 'LoadBalancerDescriptions[].LoadBalancerName' --output text
	@echo "ALB/NLB:";             aws elbv2 describe-load-balancers --region $(AWS_REGION) --query 'LoadBalancers[].LoadBalancerName' --output text
	@echo "Unattached EBS volumes:"; aws ec2 describe-volumes --region $(AWS_REGION) --filters Name=status,Values=available --query 'Volumes[].VolumeId' --output text
	@echo "NAT gateways (not available/deleted):"; aws ec2 describe-nat-gateways --region $(AWS_REGION) --filter Name=state,Values=available,pending --query 'NatGateways[].NatGatewayId' --output text
