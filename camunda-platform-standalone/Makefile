# Camunda Platform Standalone - Makefile
# Gerenciamento independente da plataforma Camunda

# ---------------- CONFIGURAÇÃO -----------------------------------------------
# Carrega variáveis de ambiente baseado no ENVIRONMENT
ENVIRONMENT ?= local
ENV_FILE := .env.$(ENVIRONMENT)

ifneq (,$(wildcard $(ENV_FILE)))
    include $(ENV_FILE)
    export
endif

# Configurações SSH para deploy remoto
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.67.197
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/mac_m2_ssh
REMOTE_DIR  ?= ~/camunda-platform
STACK       ?= camunda-platform

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

# Detecção automática do modo Swarm
SWARM := $(shell docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo 'inactive')
COMPOSE_FILE := $(if $(filter active,$(SWARM)),docker-compose.swarm.yml,docker-compose.yml)

# ---------------- COMANDOS LOCAIS -------------------------------------------

.PHONY: local-up
local-up: setup-monitoring-local
	@echo "🚀 Starting Camunda Platform locally..."
	@if [ "$(shell grep EXTERNAL_DATABASE_MODE=true .env.local)" ]; then \
		echo "📡 Using external database mode..."; \
		ENVIRONMENT=local docker compose --env-file .env.local up -d; \
	else \
		echo "🗄️ Using local database mode..."; \
		ENVIRONMENT=local docker compose --env-file .env.local --profile local-db up -d; \
	fi
	@echo "✅ Camunda Platform started locally"
	@$(MAKE) local-status

.PHONY: local-up-external
local-up-external: setup-monitoring-local
	@echo "🚀 Starting Camunda Platform locally (external database mode)..."
	@echo "📡 Using external database - containers will connect to external URIs"
	ENVIRONMENT=local docker compose --env-file .env.local up -d
	@echo "✅ Camunda Platform started in external mode"
	@$(MAKE) local-status

.PHONY: local-down
local-down:
	@echo "⏹️ Stopping Camunda Platform locally..."
	docker compose --env-file .env.local down
	@echo "✅ Camunda Platform stopped locally"

.PHONY: local-logs
local-logs:
	docker compose --env-file .env.local logs -f --tail=100

.PHONY: local-status
local-status:
	@echo "\n📊 === CAMUNDA PLATFORM STATUS (LOCAL) ==="
	@docker compose --env-file .env.local ps
	@echo "\n🌐 === SERVICE URLS ==="
	@echo "Camunda:    http://localhost:$(CAMUNDA_PORT:-8080)"
	@echo "Prometheus: http://localhost:$(PROMETHEUS_PORT:-9090)"
	@echo "Grafana:    http://localhost:$(GRAFANA_PORT:-3001) (admin/admin)"

.PHONY: local-restart
local-restart: local-down local-up

# ---------------- COMANDOS REMOTOS ------------------------------------------

.PHONY: deploy
deploy: copy-files setup-monitoring-remote
	@echo "🚀 Deploying Camunda Platform to remote server..."
	$(SSH) "cd $(REMOTE_DIR) && make remote-up ENVIRONMENT=production"
	@echo "✅ Camunda Platform deployed successfully"
	@$(MAKE) remote-status

.PHONY: copy-files
copy-files:
	@echo "📁 Copying files to remote server..."
	$(SSH) "mkdir -p $(REMOTE_DIR)"
	$(SCP) -r . $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@echo "✅ Files copied successfully"

.PHONY: remote-up
remote-up:
	@echo "🚀 Starting Camunda Platform on remote server..."
	@echo "🔍 Checking Docker Swarm status and compose file compatibility..."
	@if docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active && ! grep -q "profiles:" $(COMPOSE_FILE); then \
		echo "✅ Docker Swarm is active and compose file is compatible - using stack deploy"; \
		ENVIRONMENT=$(ENVIRONMENT) docker stack deploy -c $(COMPOSE_FILE) $(STACK); \
	else \
		echo "⚠️  Using docker compose (Swarm inactive or profiles detected)"; \
		ENVIRONMENT=$(ENVIRONMENT) docker compose --env-file .env.$(ENVIRONMENT) up -d; \
	fi

.PHONY: remote-down
remote-down:
	@echo "⏹️ Stopping Camunda Platform on remote server..."
	$(SSH) "cd $(REMOTE_DIR) && (docker stack rm $(STACK) || docker compose --env-file .env.production down)"

.PHONY: remote-logs
remote-logs:
	@echo "📋 Fetching logs from remote server..."
	$(SSH) "cd $(REMOTE_DIR) && docker service logs $(STACK)_camunda --tail=100 -f 2>/dev/null || docker compose --env-file .env.production logs camunda --tail=100 -f"

.PHONY: remote-status
remote-status:
	@echo "📊 Checking remote status..."
	$(SSH) "cd $(REMOTE_DIR) && echo '=== DOCKER STACK STATUS ===' && docker stack ps $(STACK) 2>/dev/null || (echo '=== DOCKER COMPOSE STATUS ===' && docker compose --env-file .env.production ps)"
	@echo "\n🌐 === SERVICE URLS (REMOTE) ==="
	@echo "Camunda:    http://$(VM_HOST):$(CAMUNDA_PORT:-8080)"
	@echo "Prometheus: http://$(VM_HOST):$(PROMETHEUS_PORT:-9090)"
	@echo "Grafana:    http://$(VM_HOST):$(GRAFANA_PORT:-3001) (admin/admin)"

.PHONY: remote-restart
remote-restart: remote-down
	@sleep 10
	@$(MAKE) deploy

# ---------------- UTILITÁRIOS DE MONITORAMENTO -------------------------------

.PHONY: setup-monitoring-local
setup-monitoring-local:
	@echo "⚙️ Configuring monitoring for local environment..."
	@bash scripts/setup-monitoring.sh local

.PHONY: setup-monitoring-remote
setup-monitoring-remote:
	@echo "⚙️ Configuring monitoring for remote environment..."
	$(SSH) "cd $(REMOTE_DIR) && bash scripts/setup-monitoring.sh production"

.PHONY: backup-db
backup-db:
	@echo "💾 Creating database backup..."
	$(SSH) "cd $(REMOTE_DIR) && docker exec \$$(docker ps --filter 'name=$(STACK)_db' --format '{{.ID}}' | head -1) pg_dump -U camunda camunda > backup_\$$(date +%Y%m%d_%H%M%S).sql"

.PHONY: psql
psql:
	@echo "🗄️ Connecting to PostgreSQL..."
	$(SSH) "cd $(REMOTE_DIR) && docker exec -it \$$(docker ps --filter 'name=$(STACK)_db' --format '{{.ID}}' | head -1) psql -U camunda -d camunda"

.PHONY: deploy-bpmn
deploy-bpmn:
	@echo "🚀 Deploying BPMN files to Camunda..."
	@if [ -f "scripts/deploy_bpmns.py" ]; then \
		python3 scripts/deploy_bpmns.py; \
	else \
		echo "❌ deploy_bpmns.py script not found"; \
	fi

.PHONY: deploy-bpmn-remote
deploy-bpmn-remote:
	@echo "🚀 Deploying BPMN files to remote Camunda..."
	$(SSH) "cd $(REMOTE_DIR) && python3 scripts/deploy_bpmns.py"

# ---------------- UTILITÁRIOS DE SISTEMA ------------------------------------

.PHONY: install-docker
install-docker:
	@echo "🐳 Installing Docker on remote server..."
	$(SCP) scripts/install_docker.sh $(VM_USER)@$(VM_HOST):~/
	$(SSH) "chmod +x ~/install_docker.sh && sudo ~/install_docker.sh"

.PHONY: init-swarm
init-swarm:
	@echo "🎯 Initializing Docker Swarm..."
	$(SCP) scripts/init_swarm.sh $(VM_USER)@$(VM_HOST):~/
	$(SSH) "chmod +x ~/init_swarm.sh && ~/init_swarm.sh"

.PHONY: install-make
install-make:
	@echo "🔧 Installing make on remote server..."
	$(SSH) "sudo apt update && sudo apt install -y make"
	@echo "✅ Make installed successfully"

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

.PHONY: scale
scale:
	@if [ -z "$(N)" ]; then echo "❌ Usage: make scale N=<number>"; exit 1; fi
	@echo "📈 Scaling Camunda to $(N) replicas..."
	$(SSH) "cd $(REMOTE_DIR) && docker service scale $(STACK)_camunda=$(N)"

.PHONY: validate-config
validate-config:
	@echo "🔧 Validating configuration for environment: $(ENVIRONMENT)"
	@if [ ! -f ".env.$(ENVIRONMENT)" ]; then echo "❌ Environment file .env.$(ENVIRONMENT) not found"; exit 1; fi
	@echo "✅ Environment file exists: .env.$(ENVIRONMENT)"
	@grep -q "DATABASE_URL=" .env.$(ENVIRONMENT) && echo "✅ DATABASE_URL is set" || echo "⚠️  DATABASE_URL not found"
	@grep -q "EXTERNAL_DATABASE_MODE=" .env.$(ENVIRONMENT) && echo "✅ EXTERNAL_DATABASE_MODE is configured" || echo "⚠️  EXTERNAL_DATABASE_MODE not found"
	@if grep -q "EXTERNAL_DATABASE_MODE=true" .env.$(ENVIRONMENT); then \
		echo "📡 External database mode - checking DATABASE_URL format..."; \
		if grep "DATABASE_URL=.*localhost" .env.$(ENVIRONMENT); then \
			echo "⚠️  WARNING: DATABASE_URL points to localhost but EXTERNAL_DATABASE_MODE=true"; \
		fi; \
	else \
		echo "🗄️  Local database mode"; \
	fi
	@echo "✅ Configuration validation completed"

.PHONY: show-config
show-config:
	@echo "📋 Current configuration for environment: $(ENVIRONMENT)"
	@echo "Environment file: .env.$(ENVIRONMENT)"
	@if [ -f ".env.$(ENVIRONMENT)" ]; then \
		echo "--- Configuration ---"; \
		cat .env.$(ENVIRONMENT) | grep -v PASSWORD | sed 's/^/  /'; \
		echo "--- End Configuration ---"; \
	else \
		echo "❌ Environment file not found"; \
	fi
	@echo "Remote: $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)"

# ---------------- INFORMAÇÕES -----------------------------------------------

.PHONY: help
help:
	@echo "🏗️ Camunda Platform Standalone - Available Commands"
	@echo ""
	@echo "LOCAL COMMANDS:"
	@echo "  make local-up      - Start platform locally (auto-detect DB mode)"
	@echo "  make local-up-external - Start platform with external database"
	@echo "  make local-down    - Stop platform locally"
	@echo "  make local-logs    - View local logs"
	@echo "  make local-status  - Check local status"
	@echo ""
	@echo "REMOTE COMMANDS:"
	@echo "  make deploy ENVIRONMENT=production - Deploy to remote server"
	@echo "  make remote-down   - Stop remote platform"
	@echo "  make remote-logs   - View remote logs"
	@echo "  make remote-status - Check remote status"
	@echo ""
	@echo "CONFIGURATION:"
	@echo "  make validate-config - Validate environment configuration"
	@echo "  make show-config   - Display current configuration"
	@echo "  Environment modes: EXTERNAL_DATABASE_MODE=true (external) | false (local)"
	@echo "  Available envs: local, production (use ENVIRONMENT=production)"
	@echo ""
	@echo "TROUBLESHOOTING:"
	@echo "  make check-requirements - Verify remote server prerequisites"
	@echo "  make install-make  - Install make on remote server"
	@echo "  make install-docker - Install Docker on remote server"
	@echo "  make init-swarm    - Initialize Docker Swarm on remote"
	@echo ""
	@echo "UTILITIES:"
	@echo "  make backup-db     - Backup remote database"
	@echo "  make psql          - Connect to remote PostgreSQL"
	@echo "  make scale N=3     - Scale Camunda replicas (Swarm mode only)"
	@echo "  make deploy-bpmn   - Deploy BPMN files to local Camunda"
	@echo "  make deploy-bpmn-remote - Deploy BPMN files to remote Camunda"
	@echo ""
	@echo "EXAMPLES:"
	@echo "  make deploy ENVIRONMENT=production  - Deploy to production"
	@echo "  make validate-config ENVIRONMENT=local - Validate local config"
	@echo "  make scale N=2     - Scale to 2 Camunda instances"
	@echo ""
	@echo "CURRENT STATUS:"
	@echo "  Environment: $(ENVIRONMENT)"
	@echo "  Remote: $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)"
	@echo "  Services after deploy: http://$(VM_HOST):8080 (Camunda) | http://$(VM_HOST):3001 (Grafana)"

.DEFAULT_GOAL := help