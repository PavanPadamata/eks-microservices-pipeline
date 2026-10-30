# Local Jenkins on Docker Compose. Needs `make local-up` first and a .env (see .env.example).
JENKINS_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CLUSTER     ?= eks-ms
COMPOSE      = DOCKER_GID=$$(stat -c %g /var/run/docker.sock) docker compose \
               --env-file $(JENKINS_DIR)/../.env -f $(JENKINS_DIR)/docker-compose.yml

.PHONY: jenkins-kubeconfig jenkins-up jenkins-logs jenkins-down jenkins-clean

jenkins-kubeconfig: ## write an in-network kubeconfig for Jenkins (gitignored)
	@mkdir -p $(JENKINS_DIR)/secrets
	kind get kubeconfig --internal --name $(CLUSTER) > $(JENKINS_DIR)/secrets/kubeconfig
	@chmod 600 $(JENKINS_DIR)/secrets/kubeconfig

jenkins-up: jenkins-kubeconfig ## build and start Jenkins on http://localhost:8081
	@test -f $(JENKINS_DIR)/../.env || { echo "missing .env: cp .env.example .env and set JENKINS_ADMIN_PASSWORD"; exit 1; }
	$(COMPOSE) up -d --build

jenkins-logs: ## follow Jenkins logs
	$(COMPOSE) logs -f jenkins

jenkins-down: ## stop Jenkins (keeps jenkins_home volume)
	$(COMPOSE) down

jenkins-clean: ## stop Jenkins and delete its volume
	$(COMPOSE) down -v
