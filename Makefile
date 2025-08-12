# ============================================================================
# CAMUNDA BPM ECOSYSTEM - MAKEFILE ORQUESTRADOR
# ============================================================================
# Gerencia os 3 projetos independentes de forma centralizada
# 
# Projetos:
# 1. camunda-platform-standalone     (Infraestrutura)
# 2. camunda-worker-api-gateway       (Gateway)  
# 3. camunda-workers-platform         (Workers)
# ============================================================================
include Makefile.config
# Configuração
PLATFORM_DIR := camunda-platform-standalone
GATEWAY_DIR := camunda-worker-api-gateway
WORKERS_DIR := camunda-workers-platform

# Detecção de modo
PLATFORM_EXTERNAL := $(shell grep -q "EXTERNAL_DATABASE_MODE=true" $(PLATFORM_DIR)/.env.local 2>/dev/null && echo "true" || echo "false")
GATEWAY_EXTERNAL := $(shell grep -q "EXTERNAL_SERVICES_MODE=true" $(GATEWAY_DIR)/.env.local 2>/dev/null && echo "true" || echo "false")

# Configurações SSH para setup remoto
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.67.197
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/mac_m2_ssh
REMOTE_DIR  ?= ~/camunda-ecosystem

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

# Cores para output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

# ============================================================================
# COMANDOS PRINCIPAIS - ORQUESTRAÇÃO COMPLETA
# ============================================================================

.PHONY: start
start: info
	@echo "$(GREEN)🚀 Starting complete Camunda BPM Ecosystem...$(RESET)"
	@$(MAKE) platform-up
	@echo "$(YELLOW)⏳ Waiting for Camunda to be ready...$(RESET)"
	@sleep 30
	@$(MAKE) workers-up
	@echo "$(GREEN)✅ Camunda BPM Ecosystem started successfully!$(RESET)"
	@$(MAKE) status

.PHONY: start-full
start-full: info
	@echo "$(GREEN)🚀 Starting complete ecosystem including Gateway...$(RESET)"
	@$(MAKE) platform-up
	@$(MAKE) gateway-up
	@echo "$(YELLOW)⏳ Waiting for services to be ready...$(RESET)"
	@sleep 45
	@$(MAKE) workers-up
	@echo "$(GREEN)✅ Full ecosystem started successfully!$(RESET)"
	@$(MAKE) status

.PHONY: stop
stop:
	@echo "$(RED)⏹️ Stopping complete Camunda BPM Ecosystem...$(RESET)"
	@$(MAKE) workers-down
	@$(MAKE) gateway-down
	@$(MAKE) platform-down
	@echo "$(GREEN)✅ Ecosystem stopped successfully$(RESET)"

.PHONY: restart
restart: stop
	@echo "$(YELLOW)🔄 Restarting ecosystem...$(RESET)"
	@sleep 5
	@$(MAKE) start

.PHONY: deploy-all
deploy-all: info
	@echo "$(GREEN)🚀 Deploying complete ecosystem to production...$(RESET)"
	@$(MAKE) platform-deploy
	@$(MAKE) gateway-deploy
	@$(MAKE) workers-deploy
	@echo "$(GREEN)✅ Production deployment completed!$(RESET)"
	@$(MAKE) status-remote

# ============================================================================
# GERENCIAMENTO POR PROJETO
# ============================================================================

# ---------------- PROJETO 1: PLATFORM ----------------
.PHONY: platform-up platform-down platform-status platform-logs platform-deploy
platform-up:
	@echo "$(BLUE)🏗️ Starting Camunda Platform...$(RESET)"
	@cd $(PLATFORM_DIR) && make local-up

platform-down:
	@echo "$(BLUE)🏗️ Stopping Camunda Platform...$(RESET)"
	@cd $(PLATFORM_DIR) && make local-down

platform-status:
	@echo "$(BLUE)🏗️ Camunda Platform Status:$(RESET)"
	@cd $(PLATFORM_DIR) && make local-status

platform-logs:
	@echo "$(BLUE)🏗️ Camunda Platform Logs:$(RESET)"
	@cd $(PLATFORM_DIR) && make local-logs

platform-deploy:
	@echo "$(BLUE)🏗️ Deploying Camunda Platform...$(RESET)"
	@cd $(PLATFORM_DIR) && make deploy

# ---------------- PROJETO 2: GATEWAY ----------------
.PHONY: gateway-up gateway-down gateway-status gateway-logs gateway-deploy gateway-test
gateway-up:
	@echo "$(MAGENTA)🌐 Starting Worker API Gateway...$(RESET)"
	@cd $(GATEWAY_DIR) && make local-up

gateway-down:
	@echo "$(MAGENTA)🌐 Stopping Worker API Gateway...$(RESET)"
	@cd $(GATEWAY_DIR) && make local-down

gateway-status:
	@echo "$(MAGENTA)🌐 Worker API Gateway Status:$(RESET)"
	@cd $(GATEWAY_DIR) && make local-status

gateway-logs:
	@echo "$(MAGENTA)🌐 Worker API Gateway Logs:$(RESET)"
	@cd $(GATEWAY_DIR) && make local-logs

gateway-deploy:
	@echo "$(MAGENTA)🌐 Deploying Worker API Gateway...$(RESET)"
	@cd $(GATEWAY_DIR) && make deploy

gateway-test:
	@echo "$(MAGENTA)🌐 Testing Gateway endpoints...$(RESET)"
	@cd $(GATEWAY_DIR) && make local-test

# ---------------- PROJETO 3: WORKERS ----------------
.PHONY: workers-up workers-down workers-status workers-logs workers-deploy workers-list workers-new
workers-up:
	@echo "$(CYAN)👷 Starting Workers Platform...$(RESET)"
	@cd $(WORKERS_DIR) && make local-up

workers-down:
	@echo "$(CYAN)👷 Stopping Workers Platform...$(RESET)"
	@cd $(WORKERS_DIR) && make local-down

workers-status:
	@echo "$(CYAN)👷 Workers Platform Status:$(RESET)"
	@cd $(WORKERS_DIR) && make local-status

workers-logs:
	@echo "$(CYAN)👷 Workers Platform Logs:$(RESET)"
	@cd $(WORKERS_DIR) && make local-logs

workers-deploy:
	@echo "$(CYAN)👷 Deploying Workers Platform...$(RESET)"
	@cd $(WORKERS_DIR) && make deploy

workers-list:
	@echo "$(CYAN)👷 Available Workers:$(RESET)"
	@cd $(WORKERS_DIR) && make list-workers

workers-new:
	@echo "$(CYAN)👷 Creating new worker...$(RESET)"
	@cd $(WORKERS_DIR) && make new-worker

workers-build:
	@echo "$(CYAN)👷 Building all workers...$(RESET)"
	@cd $(WORKERS_DIR) && make build-workers

# ============================================================================
# STATUS E MONITORAMENTO
# ============================================================================

.PHONY: status status-remote health urls
status:
	@echo "$(WHITE)📊 === CAMUNDA BPM ECOSYSTEM STATUS (LOCAL) ===$(RESET)"
	@echo ""
	@$(MAKE) platform-status
	@echo ""
	@if [ -d "$(GATEWAY_DIR)" ]; then $(MAKE) gateway-status; echo ""; fi
	@$(MAKE) workers-status
	@echo ""
	@$(MAKE) urls

status-remote:
	@echo "$(WHITE)📊 === CAMUNDA BPM ECOSYSTEM STATUS (REMOTE) ===$(RESET)"
	@echo ""
	@cd $(PLATFORM_DIR) && make remote-status
	@echo ""
	@if [ -d "$(GATEWAY_DIR)" ]; then cd $(GATEWAY_DIR) && make remote-status; echo ""; fi
	@cd $(WORKERS_DIR) && make remote-status

health:
	@echo "$(WHITE)💊 === HEALTH CHECKS ===$(RESET)"
	@echo "$(BLUE)🏗️ Camunda Platform:$(RESET)"
	@curl -s -f http://localhost:8080/camunda/app/welcome/default/ > /dev/null && echo "  ✅ Camunda: OK" || echo "  ❌ Camunda: FAIL"
	@curl -s -f http://localhost:9090/-/healthy > /dev/null && echo "  ✅ Prometheus: OK" || echo "  ❌ Prometheus: FAIL"
	@curl -s -f http://localhost:3001/api/health > /dev/null && echo "  ✅ Grafana: OK" || echo "  ❌ Grafana: FAIL"
	@if [ -d "$(GATEWAY_DIR)" ]; then \
		echo "$(MAGENTA)🌐 Gateway:$(RESET)"; \
		curl -s -f http://localhost:8000/health > /dev/null && echo "  ✅ Gateway: OK" || echo "  ❌ Gateway: FAIL"; \
	fi
	@echo "$(CYAN)👷 Workers:$(RESET)"
	@curl -s -f http://localhost:8001/metrics > /dev/null && echo "  ✅ Hello World Worker: OK" || echo "  ❌ Hello World Worker: FAIL"
	@curl -s -f http://localhost:8002/metrics > /dev/null && echo "  ✅ Publicacao Worker: OK" || echo "  ❌ Publicacao Worker: FAIL"

urls:
	@echo "$(WHITE)🌐 === SERVICE URLS ===$(RESET)"
	@echo "$(BLUE)🏗️ Camunda Platform:$(RESET)"
	@echo "  Camunda Web Apps: http://localhost:8080 (demo/demo)"
	@echo "  Prometheus:       http://localhost:9090"
	@echo "  Grafana:          http://localhost:3001 (admin/admin)"
	@if [ -d "$(GATEWAY_DIR)" ]; then \
		echo "$(MAGENTA)🌐 Worker API Gateway:$(RESET)"; \
		echo "  Gateway API:      http://localhost:8000"; \
		echo "  Gateway Docs:     http://localhost:8000/docs"; \
		echo "  RabbitMQ Mgmt:    http://localhost:15672 (admin/admin123)"; \
	fi
	@echo "$(CYAN)👷 Workers:$(RESET)"
	@echo "  Hello World:      http://localhost:8001/metrics"
	@echo "  Publicacao:       http://localhost:8002/metrics"

# ============================================================================
# COMANDOS DE DESENVOLVIMENTO
# ============================================================================

.PHONY: dev-setup dev-clean dev-reset vm-clean vm-clean-force vm-clean-remote vm-setup vm-setup-force vm-setup-remote vm-setup-docker vm-setup-ssl vm-setup-security vm-test vm-fresh-deploy
dev-setup:
	@echo "$(GREEN)🛠️ Setting up development environment...$(RESET)"
	@echo "Installing dependencies for all projects..."
	@if [ -d "$(GATEWAY_DIR)" ]; then cd $(GATEWAY_DIR) && make dev-setup; fi
	@cd $(WORKERS_DIR) && make dev-setup
	@echo "$(GREEN)✅ Development environment ready!$(RESET)"

dev-clean:
	@echo "$(YELLOW)🧹 Cleaning development environment...$(RESET)"
	@$(MAKE) stop
	@docker system prune -f --volumes
	@echo "$(GREEN)✅ Environment cleaned$(RESET)"

dev-reset: dev-clean dev-setup start

vm-clean:
	@echo "$(RED)🧨 ATTENTION: Complete VM Environment Cleanup!$(RESET)"
	@echo ""
	@echo "$(YELLOW)This operation will remove:$(RESET)"
	@echo "  ❌ All running containers (local and production)"
	@echo "  ❌ All Docker images, networks, and volumes"
	@echo "  ❌ All Docker build cache"
	@echo "  ❌ Docker Swarm mode (if active)"
	@echo "  ❌ All ecosystem services and data"
	@echo ""
	@echo "$(CYAN)💡 Use this to test fresh deployments:$(RESET)"
	@echo "  • make vm-clean && make start"
	@echo "  • make vm-clean && make deploy-all"
	@echo "  • make vm-clean && make platform-deploy"
	@echo ""
	@read -p "$(RED)Are you sure you want to proceed? [y/N]: $(RESET)" confirm && [ "$$confirm" = "y" ] || (echo "$(GREEN)Cancelled by user$(RESET)" && exit 1)
	@$(MAKE) vm-clean-force

vm-clean-force:
	@echo "$(RED)🛑 Stopping all ecosystem services...$(RESET)"
	@$(MAKE) stop 2>/dev/null || echo "  ⚠️ Some local services were not running"
	@$(MAKE) prod-down 2>/dev/null || echo "  ⚠️ Some production services were not running"
	@echo "$(RED)🗑️ Removing all containers...$(RESET)"
	@docker container stop $$(docker container ls -aq) 2>/dev/null || echo "  ⚠️ No containers to stop"
	@docker container rm $$(docker container ls -aq) 2>/dev/null || echo "  ⚠️ No containers to remove"
	@echo "$(RED)🗑️ Removing all Docker images...$(RESET)"
	@docker image rm $$(docker image ls -aq) --force 2>/dev/null || echo "  ⚠️ No images to remove"
	@echo "$(RED)🗑️ Removing all networks and volumes...$(RESET)"
	@docker network prune -f 2>/dev/null || echo "  ⚠️ No networks to prune"
	@docker volume prune -f 2>/dev/null || echo "  ⚠️ No volumes to prune"
	@echo "$(RED)🗑️ Removing all build cache...$(RESET)"
	@docker builder prune -af 2>/dev/null || echo "  ⚠️ No build cache to clear"
	@echo "$(RED)🗑️ Leaving Docker Swarm mode...$(RESET)"
	@docker swarm leave --force 2>/dev/null || echo "  ⚠️ Not in Swarm mode"
	@echo "$(GREEN)✅ VM completely cleaned! Ready for fresh testing$(RESET)"
	@echo ""
	@echo "$(CYAN)🚀 Suggested next steps:$(RESET)"
	@echo "  make start              # Test basic ecosystem startup"
	@echo "  make deploy-all         # Test complete production deployment"
	@echo "  make platform-deploy    # Test platform deployment only"
	@echo "  make scenario-local     # Test local development scenario"
	@echo "  make scenario-production # Test production scenario"

vm-clean-remote:
	@if [ -z "$(HOST)" ]; then \
		echo "$(RED)🧨 REMOTE VM CLEANUP: $(VM_HOST)$(RESET)"; \
		TARGET_HOST=$(VM_HOST); \
	else \
		echo "$(RED)🧨 REMOTE VM CLEANUP: $(HOST)$(RESET)"; \
		TARGET_HOST=$(HOST); \
	fi; \
	if [ "$(FORCE)" != "true" ]; then \
		echo ""; \
		echo "$(YELLOW)This will completely clean the remote VM:$(RESET)"; \
		echo "  ❌ All Docker containers, images, networks, volumes"; \
		echo "  ❌ All Docker Swarm services and stacks"; \
		echo "  ❌ Docker Swarm mode"; \
		echo "  ❌ Application directories and logs"; \
		echo ""; \
		read -p "$(RED)Proceed with remote VM cleanup? [y/N]: $(RESET)" confirm && [ "$$confirm" = "y" ] || (echo "$(GREEN)Cancelled$(RESET)" && exit 1); \
	fi; \
	echo "$(RED)🛑 Executing remote cleanup...$(RESET)"; \
	ssh $(SSH_FLAGS) $(VM_USER)@$$TARGET_HOST -t '\
		echo "🛑 Stopping all Docker services..."; \
		docker stack rm $$(docker stack ls --format "{{.Name}}" 2>/dev/null) 2>/dev/null || echo "  No stacks to remove"; \
		docker service rm $$(docker service ls -q 2>/dev/null) 2>/dev/null || echo "  No services to remove"; \
		echo "🗑️ Stopping and removing all containers..."; \
		docker container stop $$(docker container ls -aq 2>/dev/null) 2>/dev/null || echo "  No containers to stop"; \
		docker container rm $$(docker container ls -aq 2>/dev/null) 2>/dev/null || echo "  No containers to remove"; \
		echo "🗑️ Removing all Docker images..."; \
		docker image rm $$(docker image ls -aq 2>/dev/null) --force 2>/dev/null || echo "  No images to remove"; \
		echo "🗑️ Cleaning networks and volumes..."; \
		docker network prune -f 2>/dev/null || echo "  No networks to prune"; \
		docker volume prune -f 2>/dev/null || echo "  No volumes to prune"; \
		docker builder prune -af 2>/dev/null || echo "  No build cache to clear"; \
		echo "🗑️ Leaving Docker Swarm..."; \
		docker swarm leave --force 2>/dev/null || echo "  Not in Swarm mode"; \
		echo "🗑️ Cleaning application directories..."; \
		sudo rm -rf /opt/camunda/* 2>/dev/null || echo "  No camunda directories to clean"; \
		sudo rm -rf /var/log/camunda/* 2>/dev/null || echo "  No camunda logs to clean"; \
		echo "✅ Remote VM cleanup completed!"; \
	'; \
	echo "$(GREEN)✅ Remote VM cleanup completed successfully!$(RESET)"

# VM Setup Commands
vm-setup:
	@echo "$(BLUE)🏗️ COMPLETE VM SETUP - Fresh Ubuntu to Production Ready$(RESET)"
	@echo ""
	@echo "$(YELLOW)This will configure:$(RESET)"
	@echo "  ✅ System updates and dependencies"
	@echo "  ✅ Docker and Docker Compose installation"
	@echo "  ✅ Docker Swarm initialization"
	@echo "  ✅ SSL certificates ($(SSL_PROVIDER:-selfsigned))"
	@echo "  ✅ Security hardening (firewall, fail2ban)"
	@echo "  ✅ Application directories and logging"
	@echo ""
	@echo "$(CYAN)Environment Configuration:$(RESET)"
	@echo "  Domain: $(DOMAIN:-localhost)"
	@echo "  SSL Provider: $(SSL_PROVIDER:-selfsigned)"
	@echo "  SSL Email: $(SSL_EMAIL:-admin@example.com)"
	@echo ""
	@read -p "$(GREEN)Proceed with VM setup? [y/N]: $(RESET)" confirm && [ "$$confirm" = "y" ] || (echo "$(YELLOW)Setup cancelled$(RESET)" && exit 1)
	@$(MAKE) vm-setup-force

vm-setup-force:
	@echo "$(BLUE)🚀 Starting complete VM setup...$(RESET)"
	@sudo ./scripts/vm-provision.sh
	@echo "$(GREEN)✅ VM setup completed! Ready for Camunda deployment$(RESET)"

vm-setup-remote:
	@if [ -z "$(HOST)" ]; then \
		echo "$(BLUE)🌐 Setting up default remote VM: $(VM_HOST)$(RESET)"; \
		TARGET_HOST=$(VM_HOST); \
	else \
		echo "$(BLUE)🌐 Setting up remote VM: $(HOST)$(RESET)"; \
		TARGET_HOST=$(HOST); \
	fi; \
	echo "$(YELLOW)Copying setup scripts to remote server...$(RESET)"; \
	scp $(SCP_FLAGS) -r scripts/ $(VM_USER)@$$TARGET_HOST:~/; \
	echo "$(YELLOW)Executing VM setup on remote server...$(RESET)"; \
	ssh $(SSH_FLAGS) $(VM_USER)@$$TARGET_HOST -t "sudo ~/scripts/vm-provision.sh"; \
	echo "$(GREEN)✅ Remote VM setup completed!$(RESET)"

vm-setup-docker:
	@echo "$(BLUE)🐳 Installing Docker and Docker Swarm...$(RESET)"
	@sudo ./scripts/vm-provision.sh docker
	@sudo ./scripts/vm-provision.sh swarm
	@echo "$(GREEN)✅ Docker setup completed$(RESET)"

vm-setup-ssl:
	@echo "$(BLUE)🔒 Setting up SSL certificates...$(RESET)"
	@echo "Provider: $(SSL_PROVIDER:-selfsigned) | Domain: $(DOMAIN:-localhost)"
	@sudo DOMAIN=$(DOMAIN:-localhost) SSL_PROVIDER=$(SSL_PROVIDER:-selfsigned) SSL_EMAIL=$(SSL_EMAIL:-admin@example.com) ./scripts/ssl-setup.sh
	@echo "$(GREEN)✅ SSL setup completed$(RESET)"

vm-setup-security:
	@echo "$(BLUE)🔐 Configuring security hardening...$(RESET)"
	@sudo ./scripts/security-setup.sh
	@echo "$(GREEN)✅ Security hardening completed$(RESET)"

vm-test:
	@echo "$(BLUE)🧪 Testing VM setup completeness...$(RESET)"
	@./scripts/vm-provision.sh verify
	@echo "$(CYAN)🔍 Checking SSL certificates...$(RESET)"
	@./scripts/ssl-setup.sh info 2>/dev/null || echo "$(YELLOW)⚠️ No SSL certificates found$(RESET)"
	@echo "$(CYAN)🔍 Checking security configuration...$(RESET)"
	@./scripts/security-setup.sh status 2>/dev/null || echo "$(YELLOW)⚠️ Security tools not configured$(RESET)"
	@echo "$(GREEN)✅ VM testing completed$(RESET)"

vm-fresh-deploy:
	@if [ -z "$(HOST)" ]; then \
		echo "$(MAGENTA)🚀 FRESH DEPLOYMENT: $(VM_HOST)$(RESET)"; \
		TARGET_HOST=$(VM_HOST); \
	else \
		echo "$(MAGENTA)🚀 FRESH DEPLOYMENT: $(HOST)$(RESET)"; \
		TARGET_HOST=$(HOST); \
	fi; \
	echo ""; \
	echo "$(CYAN)This will perform a complete fresh deployment:$(RESET)"; \
	echo "  1️⃣ Clean remote VM completely"; \
	echo "  2️⃣ Setup VM infrastructure (Docker + SSL + Security)"; \
	echo "  3️⃣ Deploy complete Camunda ecosystem"; \
	echo "  4️⃣ Verify deployment status"; \
	echo ""; \
	echo "$(YELLOW)Configuration:$(RESET)"; \
	echo "  🌐 Target: $$TARGET_HOST"; \
	echo "  🔒 SSL: $(SSL_PROVIDER:-selfsigned)"; \
	echo "  🏷️ Domain: $(DOMAIN:-$$TARGET_HOST)"; \
	echo ""; \
	read -p "$(GREEN)Proceed with fresh deployment? [y/N]: $(RESET)" confirm && [ "$$confirm" = "y" ] || (echo "$(YELLOW)Deployment cancelled$(RESET)" && exit 1); \
	echo "$(BLUE)🗑️ Step 1/4: Cleaning remote VM...$(RESET)"; \
	$(MAKE) vm-clean-remote HOST=$$TARGET_HOST FORCE=true 2>/dev/null || echo "$(YELLOW)⚠️ VM cleanup completed with warnings$(RESET)"; \
	echo "$(BLUE)🛠️ Step 2/4: Setting up VM infrastructure...$(RESET)"; \
	$(MAKE) vm-setup-remote HOST=$$TARGET_HOST; \
	echo "$(BLUE)🚀 Step 3/4: Deploying Camunda ecosystem...$(RESET)"; \
	$(MAKE) deploy-all; \
	echo "$(BLUE)✅ Step 4/4: Verifying deployment...$(RESET)"; \
	sleep 30; \
	$(MAKE) status-remote; \
	echo ""; \
	echo "$(GREEN)🎉 FRESH DEPLOYMENT COMPLETED!$(RESET)"; \
	echo "$(CYAN)Access your services:$(RESET)"; \
	echo "  🌐 Camunda:    https://$$TARGET_HOST:8080"; \
	echo "  📊 Prometheus: https://$$TARGET_HOST:9090"; \
	echo "  📈 Grafana:    https://$$TARGET_HOST:3001"; \
	echo "  🔧 Workers:    https://$$TARGET_HOST:8001/metrics"

# ============================================================================
# COMANDOS DE PRODUÇÃO
# ============================================================================

.PHONY: prod-deploy prod-status prod-down prod-logs
prod-deploy: deploy-all

prod-status: status-remote

prod-down:
	@echo "$(RED)⏹️ Stopping production deployment...$(RESET)"
	@cd $(WORKERS_DIR) && make remote-down
	@if [ -d "$(GATEWAY_DIR)" ]; then cd $(GATEWAY_DIR) && make remote-down; fi
	@cd $(PLATFORM_DIR) && make remote-down
	@echo "$(GREEN)✅ Production stopped$(RESET)"

prod-logs:
	@echo "$(WHITE)📋 === PRODUCTION LOGS ===$(RESET)"
	@echo "$(BLUE)🏗️ Platform Logs:$(RESET)"
	@cd $(PLATFORM_DIR) && make remote-logs &
	@if [ -d "$(GATEWAY_DIR)" ]; then \
		echo "$(MAGENTA)🌐 Gateway Logs:$(RESET)"; \
		cd $(GATEWAY_DIR) && make remote-logs & \
	fi
	@echo "$(CYAN)👷 Workers Logs:$(RESET)"
	@cd $(WORKERS_DIR) && make remote-logs

# ============================================================================
# COMANDOS DE ESCALABILIDADE
# ============================================================================

.PHONY: scale-platform scale-gateway scale-worker
scale-platform:
	@if [ -z "$(N)" ]; then echo "$(RED)❌ Usage: make scale-platform N=<number>$(RESET)"; exit 1; fi
	@echo "$(BLUE)📈 Scaling Camunda Platform to $(N) replicas...$(RESET)"
	@cd $(PLATFORM_DIR) && make scale N=$(N)

scale-gateway:
	@if [ -z "$(N)" ]; then echo "$(RED)❌ Usage: make scale-gateway N=<number>$(RESET)"; exit 1; fi
	@echo "$(MAGENTA)📈 Scaling Gateway to $(N) replicas...$(RESET)"
	@cd $(GATEWAY_DIR) && make scale-gateway N=$(N)

scale-worker:
	@if [ -z "$(W)" ] || [ -z "$(N)" ]; then echo "$(RED)❌ Usage: make scale-worker W=<worker> N=<number>$(RESET)"; exit 1; fi
	@echo "$(CYAN)📈 Scaling worker $(W) to $(N) replicas...$(RESET)"
	@cd $(WORKERS_DIR) && make remote-scale W=$(W) N=$(N)

# ============================================================================
# UTILITÁRIOS
# ============================================================================

.PHONY: info logs-all backup-db
info:
	@echo "$(WHITE)📋 === ECOSYSTEM CONFIGURATION ===$(RESET)"
	@echo "Platform External DB: $(PLATFORM_EXTERNAL)"
	@echo "Gateway External Services: $(GATEWAY_EXTERNAL)"
	@echo ""

logs-all:
	@echo "$(WHITE)📋 === ALL LOGS (press Ctrl+C to stop) ===$(RESET)"
	@$(MAKE) platform-logs &
	@if [ -d "$(GATEWAY_DIR)" ]; then $(MAKE) gateway-logs & fi
	@$(MAKE) workers-logs

backup-db:
	@echo "$(YELLOW)💾 Creating database backup...$(RESET)"
	@cd $(PLATFORM_DIR) && make backup-db

# ============================================================================
# CENÁRIOS PRÉ-DEFINIDOS
# ============================================================================

.PHONY: scenario-local scenario-hybrid scenario-production
scenario-local:
	@echo "$(GREEN)🏠 === CENÁRIO: DESENVOLVIMENTO LOCAL COMPLETO ===$(RESET)"
	@echo "Todos os serviços em containers locais"
	@$(MAKE) start

scenario-hybrid:
	@echo "$(YELLOW)🌐 === CENÁRIO: HÍBRIDO (LOCAL + EXTERNAL) ===$(RESET)"
	@echo "Platform local, Gateway externo"
	@cd $(PLATFORM_DIR) && make local-up
	@cd $(GATEWAY_DIR) && make local-up-external
	@sleep 30
	@cd $(WORKERS_DIR) && make local-up
	@$(MAKE) status

scenario-production:
	@echo "$(BLUE)☁️ === CENÁRIO: PRODUÇÃO COMPLETA ===$(RESET)"
	@echo "Todos os serviços em modo produção"
	@$(MAKE) deploy-all

# ============================================================================
# HELP E INFORMAÇÕES
# ============================================================================

.PHONY: help
help:
	@echo "$(WHITE)🎯 CAMUNDA BPM ECOSYSTEM - Makefile Orquestrador$(RESET)"
	@echo ""
	@echo "$(GREEN)COMANDOS PRINCIPAIS:$(RESET)"
	@echo "  make start             - Inicia ecosystem completo (Platform + Workers)"
	@echo "  make start-full        - Inicia ecosystem + Gateway"
	@echo "  make stop              - Para todo o ecosystem"
	@echo "  make restart           - Reinicia ecosystem completo"
	@echo "  make status            - Status de todos os projetos"
	@echo "  make health            - Health check de todos os serviços"
	@echo "  make urls              - Lista todas as URLs de acesso"
	@echo ""
	@echo "$(BLUE)GERENCIAMENTO POR PROJETO:$(RESET)"
	@echo "  make platform-up/down  - Gerencia Camunda Platform"
	@echo "  make gateway-up/down   - Gerencia Worker API Gateway"
	@echo "  make workers-up/down   - Gerencia Workers Platform"
	@echo ""
	@echo "$(CYAN)WORKERS:$(RESET)"
	@echo "  make workers-list      - Lista workers disponíveis"
	@echo "  make workers-new       - Cria novo worker"
	@echo "  make workers-build     - Build de todos os workers"
	@echo ""
	@echo "$(MAGENTA)PRODUÇÃO:$(RESET)"
	@echo "  make deploy-all        - Deploy completo em produção"
	@echo "  make prod-status       - Status produção"
	@echo "  make prod-down         - Para produção"
	@echo "  make scale-platform N=3 - Escala platform"
	@echo "  make scale-worker W=hello-world N=5 - Escala worker"
	@echo ""
	@echo "$(YELLOW)CENÁRIOS:$(RESET)"
	@echo "  make scenario-local    - Setup desenvolvimento local"
	@echo "  make scenario-hybrid   - Setup híbrido (local+cloud)"
	@echo "  make scenario-production - Setup produção completa"
	@echo ""
	@echo "$(RED)DESENVOLVIMENTO:$(RESET)"
	@echo "  make dev-setup         - Setup ambiente desenvolvimento"
	@echo "  make dev-clean         - Limpa ambiente"
	@echo "  make dev-reset         - Reset completo"
	@echo "  make vm-clean          - Limpeza completa da VM (com confirmação)"
	@echo "  make vm-clean-force    - Limpeza completa da VM (sem confirmação)"
	@echo ""
	@echo "$(MAGENTA)INFRAESTRUTURA VM:$(RESET)"
	@echo "  make vm-setup          - Setup completo VM Ubuntu (Docker+SSL+Security)"
	@echo "  make vm-setup-force    - Setup completo sem confirmação"
	@echo "  make vm-setup-remote HOST=IP - Setup VM remota via SSH"
	@echo "  make vm-setup-docker   - Instala apenas Docker + Swarm"
	@echo "  make vm-setup-ssl      - Configura apenas certificados SSL"
	@echo "  make vm-setup-security - Configura apenas segurança"
	@echo "  make vm-test           - Testa completude do setup da VM"
	@echo "  make vm-clean-remote HOST=IP - Limpa VM remota completamente"
	@echo "  make vm-fresh-deploy HOST=IP - Deploy completo do zero (clean+setup+deploy)"
	@echo ""
	@echo "$(WHITE)Para ajuda específica de um projeto: cd <projeto> && make help$(RESET)"

.DEFAULT_GOAL := help