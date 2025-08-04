# Worker API Gateway - Makefile
# Gerenciamento independente do Gateway de Workers

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
REMOTE_DIR  ?= ~/worker-api-gateway
STACK       ?= worker-gateway

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

# Detecção automática do modo Swarm
SWARM := $(shell docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo 'inactive')
COMPOSE_FILE := $(if $(filter active,$(SWARM)),docker-compose.swarm.yml,docker-compose.yml)

# ---------------- COMANDOS LOCAIS -------------------------------------------

.PHONY: local-up
local-up: build-image
	@echo "🚀 Starting Worker API Gateway locally..."
	@if [ "$(shell grep '^EXTERNAL_SERVICES_MODE=true' .env.local)" ]; then \
		echo "📡 Using external services mode..."; \
		ENVIRONMENT=local docker compose --env-file .env.local up -d; \
	else \
		echo "🗄️ Using local services mode..."; \
		ENVIRONMENT=local docker compose --env-file .env.local --profile local-services up -d; \
	fi
	@echo "✅ Worker API Gateway started locally"
	@$(MAKE) local-status

.PHONY: local-up-external
local-up-external: build-image
	@echo "🚀 Starting Worker API Gateway locally (external services mode)..."
	@echo "📡 Using external services - containers will connect to external URIs"
	ENVIRONMENT=local docker compose --env-file .env.local up -d
	@echo "✅ Worker API Gateway started in external mode"
	@$(MAKE) local-status

.PHONY: local-down
local-down:
	@echo "⏹️ Stopping Worker API Gateway locally..."
	docker compose --env-file .env.local down
	@echo "✅ Worker API Gateway stopped locally"

.PHONY: local-logs
local-logs:
	docker compose --env-file .env.local logs -f --tail=100

.PHONY: local-status
local-status:
	@echo "\n📊 === WORKER API GATEWAY STATUS (LOCAL) ==="
	@docker compose --env-file .env.local ps
	@echo "\n🌐 === SERVICE URLS ==="
	@echo "Gateway API:     http://localhost:$(GATEWAY_PORT:-8000)"
	@echo "Gateway Metrics: http://localhost:$(METRICS_PORT:-9000)/metrics"
	@echo "RabbitMQ Mgmt:   http://localhost:$(RABBITMQ_MGMT_PORT:-15672)"
	@echo "MongoDB:         mongodb://localhost:$(MONGODB_PORT:-27017)"

.PHONY: local-test
local-test:
	@echo "🧪 Testing Gateway endpoints..."
	@curl -s http://localhost:$(GATEWAY_PORT:-8000)/health | python -m json.tool || echo "❌ Health check failed"
	@curl -s http://localhost:$(GATEWAY_PORT:-8000)/ | python -m json.tool || echo "❌ Root endpoint failed"

.PHONY: local-restart
local-restart: local-down local-up

# ---------------- COMANDOS REMOTOS ------------------------------------------

.PHONY: deploy
deploy: build-image copy-files
	@echo "🚀 Deploying Worker API Gateway to remote server..."
	$(SSH) "cd $(REMOTE_DIR) && make remote-up ENVIRONMENT=production"
	@echo "✅ Worker API Gateway deployed successfully"
	@$(MAKE) remote-status

.PHONY: build-image
build-image:
	@echo "🏗️ Building Gateway Docker image..."
	docker build -t worker-api-gateway:latest ./app/
	@echo "✅ Gateway image built successfully"

.PHONY: copy-files
copy-files:
	@echo "📁 Copying files to remote server..."
	$(SSH) "mkdir -p $(REMOTE_DIR)"
	$(SCP) -r . $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@echo "✅ Files copied successfully"

.PHONY: remote-up
remote-up:
	@echo "🚀 Starting Worker API Gateway on remote server..."
	ENVIRONMENT=$(ENVIRONMENT) docker stack deploy -c $(COMPOSE_FILE) --env-file .env.$(ENVIRONMENT) $(STACK) || \
	ENVIRONMENT=$(ENVIRONMENT) docker compose --env-file .env.$(ENVIRONMENT) up -d

.PHONY: remote-down
remote-down:
	@echo "⏹️ Stopping Worker API Gateway on remote server..."
	$(SSH) "cd $(REMOTE_DIR) && (docker stack rm $(STACK) || docker compose --env-file .env.production down)"

.PHONY: remote-logs
remote-logs:
	@echo "📋 Fetching logs from remote server..."
	$(SSH) "cd $(REMOTE_DIR) && docker service logs $(STACK)_gateway --tail=100 -f 2>/dev/null || docker compose --env-file .env.production logs gateway --tail=100 -f"

.PHONY: remote-status
remote-status:
	@echo "📊 Checking remote status..."
	$(SSH) "cd $(REMOTE_DIR) && echo '=== DOCKER STACK STATUS ===' && docker stack ps $(STACK) 2>/dev/null || (echo '=== DOCKER COMPOSE STATUS ===' && docker compose --env-file .env.production ps)"
	@echo "\n🌐 === SERVICE URLS (REMOTE) ==="
	@echo "Gateway API:     http://$(VM_HOST):$(GATEWAY_PORT:-8000)"
	@echo "Gateway Metrics: http://$(VM_HOST):$(METRICS_PORT:-9000)/metrics"
	@echo "RabbitMQ Mgmt:   http://$(VM_HOST):$(RABBITMQ_MGMT_PORT:-15672)"

.PHONY: remote-test
remote-test:
	@echo "🧪 Testing remote Gateway endpoints..."
	@curl -s http://$(VM_HOST):$(GATEWAY_PORT:-8000)/health | python -m json.tool || echo "❌ Remote health check failed"

.PHONY: remote-restart
remote-restart: remote-down
	@sleep 10
	@$(MAKE) deploy

# ---------------- UTILITÁRIOS DE GATEWAY ------------------------------------

.PHONY: health-check
health-check:
	@echo "💊 Performing comprehensive health check..."
	@curl -s http://localhost:$(GATEWAY_PORT:-8000)/health | python -m json.tool

.PHONY: scale-gateway
scale-gateway:
	@if [ -z "$(N)" ]; then echo "❌ Usage: make scale-gateway N=<number>"; exit 1; fi
	@echo "📈 Scaling Gateway to $(N) replicas..."
	$(SSH) "cd $(REMOTE_DIR) && docker service scale $(STACK)_gateway=$(N)"

.PHONY: mongodb-shell
mongodb-shell:
	@echo "🗄️ Connecting to MongoDB..."
	docker exec -it $$(docker ps --filter 'name=mongodb' --format '{{.ID}}' | head -1) mongosh --username $(MONGO_USERNAME:-admin) --password $(MONGO_PASSWORD:-admin123) --authenticationDatabase admin $(MONGODB_DATABASE:-worker_gateway)

.PHONY: rabbitmq-queue-stats
rabbitmq-queue-stats:
	@echo "🐰 RabbitMQ queue statistics..."
	@curl -s -u $(RABBITMQ_USER:-admin):$(RABBITMQ_PASSWORD:-admin123) http://localhost:$(RABBITMQ_MGMT_PORT:-15672)/api/queues | python -m json.tool

# ---------------- UTILITÁRIOS DE DESENVOLVIMENTO ----------------------------

.PHONY: dev-setup
dev-setup:
	@echo "🛠️ Setting up development environment..."
	cd app && pip install -r requirements.txt
	@echo "✅ Development environment ready"

.PHONY: dev-run
dev-run:
	@echo "🚀 Running Gateway in development mode..."
	cd app && python main.py

.PHONY: test-api
test-api:
	@echo "🧪 Testing API endpoints..."
	@echo "Testing health endpoint..."
	@curl -X GET http://localhost:$(GATEWAY_PORT:-8000)/health
	@echo "\nTesting root endpoint..."
	@curl -X GET http://localhost:$(GATEWAY_PORT:-8000)/

# ---------------- INFORMAÇÕES -----------------------------------------------

.PHONY: help
help:
	@echo "🌐 Worker API Gateway - Available Commands"
	@echo ""
	@echo "LOCAL COMMANDS:"
	@echo "  make local-up      - Start gateway locally (auto-detect services mode)"
	@echo "  make local-up-external - Start gateway with external services"
	@echo "  make local-down    - Stop gateway locally"
	@echo "  make local-logs    - View local logs"
	@echo "  make local-status  - Check local status"
	@echo "  make local-test    - Test local endpoints"
	@echo ""
	@echo "REMOTE COMMANDS:"
	@echo "  make deploy        - Deploy to remote server"
	@echo "  make remote-down   - Stop remote gateway"
	@echo "  make remote-logs   - View remote logs"
	@echo "  make remote-status - Check remote status"
	@echo "  make remote-test   - Test remote endpoints"
	@echo ""
	@echo "UTILITIES:"
	@echo "  make health-check     - Comprehensive health check"
	@echo "  make scale-gateway N=3 - Scale gateway replicas"
	@echo "  make mongodb-shell    - Connect to MongoDB"
	@echo "  make rabbitmq-queue-stats - RabbitMQ statistics"
	@echo ""
	@echo "DEVELOPMENT:"
	@echo "  make dev-setup     - Setup development environment"
	@echo "  make dev-run       - Run gateway in dev mode"
	@echo "  make test-api      - Test API endpoints"
	@echo ""
	@echo "Environment: $(ENVIRONMENT)"
	@echo "Remote: $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)"

.DEFAULT_GOAL := help