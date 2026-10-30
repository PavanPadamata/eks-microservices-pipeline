# Monitoring stack. Defaults target the kind cluster; for another cluster pass KCTX=<kube-context>.
MON_DIR           := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CLUSTER           ?= eks-ms
KCTX              ?= kind-$(CLUSTER)
KUBECTL           ?= kubectl --context $(KCTX)
HELM              ?= helm --kube-context $(KCTX)
KPS_CHART_VERSION ?= 92.16.1
MON_NAMESPACE     ?= monitoring

.PHONY: monitoring-up monitoring-down grafana prometheus

monitoring-up: ## install kube-prometheus-stack + ServiceMonitor, alert rules and dashboard
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
	helm repo update >/dev/null
	$(HELM) upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
	  --version $(KPS_CHART_VERSION) -n $(MON_NAMESPACE) --create-namespace \
	  -f $(MON_DIR)/kube-prometheus-stack-values.yaml --wait --timeout 6m
	$(KUBECTL) apply -k $(MON_DIR)

monitoring-down: ## uninstall the monitoring stack (its CRDs are kept)
	-$(KUBECTL) delete -k $(MON_DIR)
	$(HELM) uninstall kube-prometheus-stack -n $(MON_NAMESPACE)

grafana: ## port-forward Grafana to http://localhost:3000 (prints the generated admin password)
	@echo "Grafana: http://localhost:3000  user: admin  password: $$($(KUBECTL) -n $(MON_NAMESPACE) get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d)"
	$(KUBECTL) -n $(MON_NAMESPACE) port-forward svc/kube-prometheus-stack-grafana 3000:80

prometheus: ## port-forward Prometheus to http://localhost:9090
	$(KUBECTL) -n $(MON_NAMESPACE) port-forward svc/kube-prometheus-stack-prometheus 9090:9090
