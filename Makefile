# Camunda Server DC - Main Makefile
# CI/CD Pipeline para deploy completo da plataforma Camunda

# ---------------- CONFIGURAÇÃO -----------------------------------------------
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.69.65
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/id_rsa
REMOTE_DIR  ?= ~/camunda-platform

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

# ---------------- PIPELINE CI/CD ---------------------------------------------

.PHONY: ci-cd
ci-cd: check-requirements deploy-all deploy-bpmns
	@echo "🎉 CI/CD Pipeline completed successfully!"

.PHONY: deploy-all
deploy-all: deploy-secure
	@echo "✅ All services deployed successfully"

.PHONY: deploy-secure
deploy-secure:
	@echo "🔒 Deploying with security enhancements..."
	@$(SCP) scripts/deploy-secure.sh $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@$(SSH) "cd $(REMOTE_DIR) && chmod +x scripts/deploy-secure.sh && bash scripts/deploy-secure.sh"
	@echo "✅ Secure deployment completed"

.PHONY: deploy-camunda-platform
deploy-camunda-platform: init-swarm
	@echo "🚀 Deploying Camunda Platform..."
	@cd camunda-platform-standalone && $(MAKE) deploy ENVIRONMENT=production
	@echo "✅ Camunda Platform deployed"

.PHONY: deploy-api-gateway
deploy-api-gateway:
	@echo "🚀 Deploying API Gateway..."
	@cd camunda-worker-api-gateway && $(MAKE) deploy ENVIRONMENT=production
	@echo "✅ API Gateway deployed"

.PHONY: deploy-workers
deploy-workers:
	@echo "🚀 Deploying Workers Platform..."
	@cd camunda-workers-platform && $(MAKE) deploy ENVIRONMENT=production
	@echo "✅ Workers Platform deployed"

.PHONY: deploy-bpmns
deploy-bpmns:
	@echo "📋 Deploying BPMN processes..."
	@$(SSH) "cd $(REMOTE_DIR) && python3 scripts/deploy_bpmns.py"
	@echo "✅ BPMN processes deployed"

# ---------------- COMANDOS DE DEPLOY INDIVIDUAL ------------------------------

.PHONY: deploy-traefik
deploy-traefik:
	@echo "🌐 Deploying Traefik..."
	@$(SCP) -r traefik/ $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@$(SSH) "cd $(REMOTE_DIR)/traefik && make setup"
	@echo "✅ Traefik deployed"

.PHONY: deploy-portainer
deploy-portainer:
	@echo "🐳 Deploying Portainer..."
	@$(SCP) -r portainer/ $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@$(SSH) "cd $(REMOTE_DIR)/portainer && make deploy"
	@echo "✅ Portainer deployed"

.PHONY: deploy-n8n
deploy-n8n:
	@echo "🔄 Deploying N8N..."
	@$(SCP) -r n8n/ $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@$(SSH) "cd $(REMOTE_DIR)/n8n && make deploy"
	@echo "✅ N8N deployed"

# ---------------- COMANDOS DE INFRAESTRUTURA --------------------------------

.PHONY: setup-infrastructure
setup-infrastructure: install-docker install-make init-swarm setup-monitoring
	@echo "✅ Infrastructure setup completed"

.PHONY: install-docker
install-docker:
	@echo "🐳 Installing Docker on remote server..."
	@$(SCP) scripts/install_docker.sh $(VM_USER)@$(VM_HOST):~/
	@$(SSH) "chmod +x ~/install_docker.sh && sudo ~/install_docker.sh"
	@echo "✅ Docker installed"

.PHONY: install-make
install-make:
	@echo "🔧 Installing make on remote server..."
	@$(SSH) "sudo apt update && sudo apt install -y make"
	@echo "✅ Make installed"

.PHONY: init-swarm
init-swarm:
	@echo "🎯 Checking and initializing Docker Swarm..."
	@$(SSH) "if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then \
		echo 'Initializing Docker Swarm...'; \
		docker swarm init; \
		echo '✅ Docker Swarm initialized'; \
	else \
		echo '✅ Docker Swarm is already active'; \
	fi"

.PHONY: setup-monitoring
setup-monitoring:
	@echo "📊 Setting up monitoring..."
	@$(SSH) "cd $(REMOTE_DIR) && bash scripts/setup-monitoring.sh"
	@echo "✅ Monitoring setup completed"

# ---------------- COMANDOS DE VERIFICAÇÃO ----------------------------------

.PHONY: check-requirements
check-requirements:
	@echo "🔍 Checking remote server requirements..."
	@echo "Remote: $(VM_USER)@$(VM_HOST)"
	@echo "Checking SSH connectivity..."
	@$(SSH) "echo '✅ SSH connection successful'"
	@echo "Checking Docker installation..."
	@$(SSH) "docker --version && echo '✅ Docker is installed' || echo '❌ Docker not found - run: make install-docker'"
	@echo "Checking Docker Swarm status..."
	@$(SSH) "docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q active && echo '✅ Docker Swarm is active' || echo '⚠️  Docker Swarm not initialized - run: make init-swarm'"
	@echo "Checking make installation..."
	@$(SSH) "make --version >/dev/null 2>&1 && echo '✅ Make is installed' || echo '❌ Make not found - run: make install-make'"
	@echo "✅ Requirements check completed"

.PHONY: status
status:
	@echo "📊 Checking all services status..."
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== TRAEFIK STATUS ===' && docker ps | grep traefik || echo 'Traefik not running'"
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== PORTAINER STATUS ===' && docker ps | grep portainer || echo 'Portainer not running'"
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== CAMUNDA STATUS ===' && docker ps | grep camunda || echo 'Camunda not running'"
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== API GATEWAY STATUS ===' && docker ps | grep gateway || echo 'API Gateway not running'"
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== WORKERS STATUS ===' && docker ps | grep worker || echo 'Workers not running'"
	@echo "\n🌐 === SERVICE URLS ==="
	@echo "Traefik:     http://$(VM_HOST)"
	@echo "Portainer:  http://$(VM_HOST):9000"
	@echo "Camunda:    http://$(VM_HOST):8080"
	@echo "API Gateway: http://$(VM_HOST):8000"

.PHONY: logs
logs:
	@echo "📋 Fetching logs from all services..."
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== TRAEFIK LOGS ===' && docker logs traefik --tail=50"
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== PORTAINER LOGS ===' && docker logs portainer --tail=50"
	@$(SSH) "cd $(REMOTE_DIR) && echo '=== CAMUNDA LOGS ===' && docker logs camunda --tail=50"

# ---------------- COMANDOS DE MANUTENÇÃO ------------------------------------

.PHONY: restart-all
restart-all: stop-all deploy-all
	@echo "🔄 All services restarted"

.PHONY: stop-all
stop-all:
	@echo "⏹️ Stopping all services..."
	@$(SSH) "cd $(REMOTE_DIR) && docker stop \$$(docker ps -q) 2>/dev/null || true"
	@echo "✅ All services stopped"

.PHONY: cleanup
cleanup:
	@echo "🧹 Cleaning up remote server..."
	@$(SSH) "cd $(REMOTE_DIR) && docker system prune -f"
	@$(SSH) "cd $(REMOTE_DIR) && docker volume prune -f"
	@echo "✅ Cleanup completed"

.PHONY: backup
backup:
	@echo "💾 Creating backup..."
	@$(SSH) "cd $(REMOTE_DIR) && mkdir -p backups && tar -czf backups/backup_\$$(date +%Y%m%d_%H%M%S).tar.gz ."
	@echo "✅ Backup created"

# ---------------- INFORMAÇÕES -----------------------------------------------

.PHONY: help
help:
	@echo "🏗️ Camunda Server DC - CI/CD Pipeline"
	@echo ""
	@echo "MAIN COMMANDS:"
	@echo "  make ci-cd              - Complete CI/CD pipeline"
	@echo "  make deploy-all         - Deploy all services with security"
	@echo "  make deploy-secure      - Deploy with security enhancements"
	@echo "  make deploy-bpmns       - Deploy BPMN processes"
	@echo ""
	@echo "INDIVIDUAL DEPLOYS:"
	@echo "  make deploy-traefik     - Deploy Traefik only"
	@echo "  make deploy-portainer   - Deploy Portainer only"
	@echo "  make deploy-camunda-platform - Deploy Camunda Platform only"
	@echo "  make deploy-api-gateway - Deploy API Gateway only"
	@echo "  make deploy-workers     - Deploy Workers only"
	@echo "  make deploy-n8n         - Deploy N8N only"
	@echo ""
	@echo "INFRASTRUCTURE:"
	@echo "  make setup-infrastructure - Setup complete infrastructure"
	@echo "  make install-docker     - Install Docker on remote"
	@echo "  make install-make       - Install make on remote"
	@echo "  make init-swarm         - Initialize Docker Swarm"
	@echo "  make setup-monitoring   - Setup monitoring"
	@echo ""
	@echo "MAINTENANCE:"
	@echo "  make status             - Check all services status"
	@echo "  make logs                - View all services logs"
	@echo "  make restart-all         - Restart all services"
	@echo "  make stop-all            - Stop all services"
	@echo "  make cleanup             - Clean up remote server"
	@echo "  make backup              - Create backup"
	@echo ""
	@echo "VERIFICATION:"
	@echo "  make check-requirements - Verify remote server prerequisites"
	@echo ""
	@echo "CURRENT CONFIG:"
	@echo "  Remote: $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)"
	@echo "  Services: Traefik, Portainer, Camunda, API Gateway, Workers, N8N"

.DEFAULT_GOAL := help