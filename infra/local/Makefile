# Local workflow on kind. Run from the repo root (`make local-up`) or from here.
ROOT          := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
CLUSTER       ?= eks-ms
RELEASE       ?= microservices
NAMESPACE     ?= microservices
TAG           ?= local
IMAGE_PREFIX  ?= eks-microservices
PY_IMAGE      ?= python:3.12.16-slim
TRAEFIK_CHART_VERSION        ?= 42.1.3
METRICS_SERVER_CHART_VERSION ?= 3.14.0

# Always pin the kube-context so nothing here can touch another cluster.
KCTX    := kind-$(CLUSTER)
KUBECTL := kubectl --context $(KCTX)
HELM    := helm --kube-context $(KCTX)
CHART   := $(ROOT)/charts/microservices
LOCAL   := $(ROOT)/infra/local

.PHONY: help test lint local-up build load deploy status local-down
help:
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ -/'

test: ## run unit tests for both services in a python container
	@for svc in api worker; do \
	  echo "== $$svc"; \
	  docker run --rm -u $$(id -u) -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
	    -v $(ROOT)/services/$$svc:/src -w /src $(PY_IMAGE) \
	    sh -c "pip install -q --no-cache-dir --no-warn-script-location -r requirements-dev.txt 2>&1 | grep -E '^ERROR'; python -m pytest -q -p no:cacheprovider" || exit 1; \
	done

lint: ## helm lint with both value overrides
	helm lint $(CHART) -f $(CHART)/values-local.yaml
	helm lint $(CHART) -f $(CHART)/values-eks.yaml

local-up: ## create the kind cluster, Traefik ingress and metrics-server
	@kind get clusters | grep -qx $(CLUSTER) || kind create cluster --config $(LOCAL)/kind-config.yaml
	helm repo add traefik https://traefik.github.io/charts >/dev/null
	helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
	helm repo update >/dev/null
	$(HELM) upgrade --install traefik traefik/traefik --version $(TRAEFIK_CHART_VERSION) \
	  -n traefik --create-namespace -f $(LOCAL)/traefik-values.yaml --wait --timeout 3m
	$(HELM) upgrade --install metrics-server metrics-server/metrics-server --version $(METRICS_SERVER_CHART_VERSION) \
	  -n kube-system -f $(LOCAL)/metrics-server-values.yaml --wait --timeout 3m

build: ## build both service images
	docker build -t $(IMAGE_PREFIX)/api:$(TAG) $(ROOT)/services/api
	docker build -t $(IMAGE_PREFIX)/worker:$(TAG) $(ROOT)/services/worker

load: build ## load the images into the kind node (no registry needed)
	kind load docker-image --name $(CLUSTER) $(IMAGE_PREFIX)/api:$(TAG) $(IMAGE_PREFIX)/worker:$(TAG)

deploy: load ## helm upgrade --install the chart on kind
	$(HELM) upgrade --install $(RELEASE) $(CHART) -n $(NAMESPACE) --create-namespace \
	  -f $(CHART)/values-local.yaml \
	  --set services.api.image.tag=$(TAG) --set services.worker.image.tag=$(TAG) \
	  --wait --timeout 3m
	@echo "api reachable at: http://localhost:8080/compute?n=10"

status: ## pods, HPAs and ingress
	$(KUBECTL) -n $(NAMESPACE) get pods,hpa,ingress

local-down: ## delete the kind cluster
	kind delete cluster --name $(CLUSTER)
