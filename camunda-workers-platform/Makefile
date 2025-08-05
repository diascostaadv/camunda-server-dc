# Camunda Workers Platform - Makefile
# Gerenciamento independente da plataforma de workers

# ---------------- DETECÇÃO AUTOMÁTICA DE OS ----------------------------------
# Detecta o sistema operacional e configura comandos apropriados
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

ifeq ($(OS),Windows_NT)
    # Windows
    DETECTED_OS := Windows
    PYTHON_CMD := python
    SHELL_CMD := cmd
    PATH_SEP := \\
    EXE_EXT := .exe
else
    # Unix-like systems (Linux, macOS, etc.)
    ifeq ($(UNAME_S),Linux)
        DETECTED_OS := Linux
    endif
    ifeq ($(UNAME_S),Darwin)
        DETECTED_OS := macOS
    endif
    
    # Para sistemas Unix, verifica se python3 existe, senão usa python
    PYTHON_CMD := $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)
    SHELL_CMD := bash
    PATH_SEP := /
    EXE_EXT :=
endif

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
REMOTE_DIR  ?= ~/camunda-workers
STACK       ?= camunda-workers

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

# Detecção automática do modo Swarm
SWARM := $(shell docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null || echo 'inactive')
COMPOSE_FILE := $(if $(filter active,$(SWARM)),docker-compose.swarm.yml,docker-compose.yml)

# ---------------- GERENCIAMENTO DE WORKERS ----------------------------------

.PHONY: list-workers
list-workers:
	@echo "📋 Listing available workers..."
	@cd workers && $(PYTHON_CMD) _config/worker_discovery.py --list

.PHONY: new-worker
new-worker:
	@echo "🆕 Creating new worker..."
	@cd workers && $(PYTHON_CMD) _config/new-worker.py

.PHONY: generate-compose
generate-compose:
	@echo "⚙️ Generating docker-compose files..."
	@cd workers && $(PYTHON_CMD) _config/generate-compose.py

.PHONY: build-workers
build-workers:
	@echo "🏗️ Building all worker images..."
	@$(MAKE) list-workers
	@cd workers && find . -name "worker.json" -path "./*" ! -path "./_*" | while read config; do \
		worker_dir=$$(dirname "$$config" | sed 's|^\./||'); \
		echo "Building worker: $$worker_dir"; \
		docker build -t camunda-workers/$$worker_dir:latest --build-arg WORKER_DIR=$$worker_dir .; \
	done
	@echo "✅ All worker images built successfully"

.PHONY: build-worker
build-worker:
	@if [ -z "$(W)" ]; then echo "❌ Usage: make build-worker W=<worker-name>"; exit 1; fi
	@echo "🏗️ Building worker: $(W)..."
	@cd workers && docker build -t camunda-workers/$(W):latest --build-arg WORKER_DIR=$(W) .
	@echo "✅ Worker $(W) built successfully"

# ---------------- COMANDOS LOCAIS -------------------------------------------

.PHONY: local-up
local-up: build-workers
	@echo "🚀 Starting Workers Platform locally..."
	@echo "📊 Using replicas: Hello=${WORKER_HELLO_REPLICAS:-0}, Publicacao=${WORKER_PUBLICACAO_REPLICAS:-0}, Unified=${WORKER_PUBLICACAO_UNIFIED_REPLICAS:-1}"
	ENVIRONMENT=local docker compose -f docker-compose.yml --env-file .env.local up -d --scale worker-hello-world=$${WORKER_HELLO_REPLICAS:-0} --scale worker-publicacao=$${WORKER_PUBLICACAO_REPLICAS:-0} --scale worker-publicacao-unified=$${WORKER_PUBLICACAO_UNIFIED_REPLICAS:-1}
	@echo "✅ Workers Platform started locally"
	@$(MAKE) local-status

.PHONY: local-down
local-down:
	@echo "⏹️ Stopping Workers Platform locally..."
	docker compose -f docker-compose.yml --env-file .env.local down
	@echo "✅ Workers Platform stopped locally"

# Aliases para compatibilidade com documentação
.PHONY: workers-up
workers-up: local-up
	@echo "ℹ️ workers-up is an alias for local-up"

.PHONY: workers-down
workers-down: local-down
	@echo "ℹ️ workers-down is an alias for local-down"

.PHONY: local-logs
local-logs:
	docker compose -f docker-compose.yml --env-file .env.local logs -f --tail=100

.PHONY: local-status
local-status:
	@echo "\n📊 === WORKERS PLATFORM STATUS (LOCAL) ==="
	@docker compose -f docker-compose.yml --env-file .env.local ps
	@echo "\n🌐 === WORKER METRICS ==="
	@echo "📡 Dynamic ports assigned by Docker:"
	@docker compose -f docker-compose.yml --env-file .env.local ps --format "table {{.Service}}\t{{.Ports}}" | grep -E "(hello-world|publicacao)" | sed 's/0.0.0.0:/  http:\/\/localhost:/g' | sed 's/->.*/ \/metrics/g' || echo "  No workers running"

.PHONY: local-scale
local-scale:
	@if [ -z "$(W)" ] || [ -z "$(N)" ]; then echo "❌ Usage: make local-scale W=<worker> N=<number>"; exit 1; fi
	@echo "📈 Scaling worker $(W) to $(N) replicas locally..."
	docker compose -f docker-compose.yml --env-file .env.local up -d --scale worker-$(W)=$(N)

.PHONY: local-restart
local-restart: local-down local-up

# ---------------- COMANDOS REMOTOS ------------------------------------------

.PHONY: deploy
deploy: build-workers copy-files
	@echo "🚀 Deploying Workers Platform to remote server..."
	$(SSH) "cd $(REMOTE_DIR) && make remote-up ENVIRONMENT=production"
	@echo "✅ Workers Platform deployed successfully"
	@$(MAKE) remote-status

.PHONY: copy-files
copy-files:
	@echo "📁 Copying files to remote server..."
	$(SSH) "mkdir -p $(REMOTE_DIR)"
	$(SCP) -r . $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@echo "✅ Files copied successfully"

.PHONY: remote-up
remote-up:
	@echo "🚀 Starting Workers Platform on remote server..."
	ENVIRONMENT=$(ENVIRONMENT) docker stack deploy -c $(COMPOSE_FILE) --env-file .env.$(ENVIRONMENT) $(STACK) || \
	ENVIRONMENT=$(ENVIRONMENT) docker compose --env-file .env.$(ENVIRONMENT) up -d

.PHONY: remote-down
remote-down:
	@echo "⏹️ Stopping Workers Platform on remote server..."
	$(SSH) "cd $(REMOTE_DIR) && (docker stack rm $(STACK) || docker compose --env-file .env.production down)"

.PHONY: remote-logs
remote-logs:
	@echo "📋 Fetching logs from remote server..."
	$(SSH) "cd $(REMOTE_DIR) && docker service logs $(STACK)_worker-hello-world --tail=100 -f 2>/dev/null || docker compose --env-file .env.production logs --tail=100 -f"

.PHONY: remote-status
remote-status:
	@echo "📊 Checking remote status..."
	$(SSH) "cd $(REMOTE_DIR) && echo '=== DOCKER STACK STATUS ===' && docker stack ps $(STACK) 2>/dev/null || (echo '=== DOCKER COMPOSE STATUS ===' && docker compose --env-file .env.production ps)"
	@echo "\n🌐 === WORKER METRICS (REMOTE) ==="
	@echo "Hello World Worker:     http://$(VM_HOST):8001/metrics"
	@echo "Publicacao Worker:      http://$(VM_HOST):8002/metrics"
	@echo "Publicacao Unified:     http://$(VM_HOST):8003/metrics"

.PHONY: remote-scale
remote-scale:
	@if [ -z "$(W)" ] || [ -z "$(N)" ]; then echo "❌ Usage: make remote-scale W=<worker> N=<number>"; exit 1; fi
	@echo "📈 Scaling worker $(W) to $(N) replicas remotely..."
	$(SSH) "cd $(REMOTE_DIR) && docker service scale $(STACK)_worker-$(W)=$(N)"

.PHONY: remote-restart
remote-restart: remote-down
	@sleep 10
	@$(MAKE) deploy

# ---------------- UTILITÁRIOS DE WORKERS ------------------------------------

.PHONY: worker-logs
worker-logs:
	@if [ -z "$(W)" ]; then echo "❌ Usage: make worker-logs W=<worker-name>"; exit 1; fi
	@echo "📋 Fetching logs for worker $(W)..."
	@if [ "$(ENVIRONMENT)" = "local" ]; then \
		docker compose -f docker-compose.yml --env-file .env.$(ENVIRONMENT) logs -f worker-$(W); \
	else \
		docker compose --env-file .env.$(ENVIRONMENT) logs -f worker-$(W); \
	fi

.PHONY: worker-shell
worker-shell:
	@if [ -z "$(W)" ]; then echo "❌ Usage: make worker-shell W=<worker-name>"; exit 1; fi
	@echo "🐚 Opening shell in worker $(W)..."
	@if [ "$(ENVIRONMENT)" = "local" ]; then \
		docker compose -f docker-compose.yml --env-file .env.$(ENVIRONMENT) exec worker-$(W) /bin/bash; \
	else \
		docker compose --env-file .env.$(ENVIRONMENT) exec worker-$(W) /bin/bash; \
	fi

.PHONY: test-worker-connection
test-worker-connection:
	@echo "🧪 Testing worker connections to Camunda..."
	@echo "Camunda URL: $(CAMUNDA_URL)"
	@curl -s "$(CAMUNDA_URL)/engine" | $(PYTHON_CMD) -m json.tool || echo "❌ Connection failed"

.PHONY: worker-metrics
worker-metrics:
	@echo "📊 Fetching worker metrics..."
	@echo "=== Hello World Worker ==="
	@curl -s http://localhost:8001/metrics | head -20 2>/dev/null || echo "Worker not running"
	@echo "\n=== Publicacao Worker ==="
	@curl -s http://localhost:8002/metrics | head -20 2>/dev/null || echo "Worker not running"
	@echo "\n=== Publicacao Unified Worker ==="
	@curl -s http://localhost:8003/metrics | head -20 2>/dev/null || echo "Worker not running"

# ---------------- UTILITÁRIOS DE DESENVOLVIMENTO ----------------------------

.PHONY: dev-setup
dev-setup:
	@echo "🛠️ Setting up development environment..."
	cd workers && pip install -r requirements.txt
	@echo "✅ Development environment ready"

.PHONY: dev-run-worker
dev-run-worker:
	@if [ -z "$(W)" ]; then echo "❌ Usage: make dev-run-worker W=<worker-name>"; exit 1; fi
	@echo "🚀 Running worker $(W) in development mode..."
	cd workers/$(W) && $(PYTHON_CMD) main.py

.PHONY: validate-workers
validate-workers:
	@echo "✅ Validating worker configurations..."
	@cd workers && $(PYTHON_CMD) _config/worker_discovery.py --validate

.PHONY: system-info
system-info:
	@echo "🖥️  System Information:"
	@echo "  OS: $(DETECTED_OS)"
	@echo "  Architecture: $(UNAME_M)"
	@echo "  Python Command: $(PYTHON_CMD)"
	@echo "  Shell: $(SHELL_CMD)"
	@echo "  Path Separator: $(PATH_SEP)"
	@echo "  Environment: $(ENVIRONMENT)"
	@echo ""
	@echo "Python Version:"
	@$(PYTHON_CMD) --version 2>/dev/null || echo "  Python not found"

# ---------------- INFORMAÇÕES -----------------------------------------------

.PHONY: help
help:
	@echo "👷 Camunda Workers Platform - Available Commands"
	@echo ""
	@echo "WORKER MANAGEMENT:"
	@echo "  make list-workers         - List available workers"
	@echo "  make new-worker          - Create new worker interactively"
	@echo "  make build-workers       - Build all worker images"
	@echo "  make build-worker W=name - Build specific worker"
	@echo "  make generate-compose    - Generate docker-compose files"
	@echo ""
	@echo "LOCAL COMMANDS:"
	@echo "  make local-up            - Start workers locally"
	@echo "  make local-down          - Stop workers locally"
	@echo "  make local-logs          - View local logs"
	@echo "  make local-status        - Check local status"
	@echo "  make local-scale W=name N=3 - Scale worker locally"
	@echo ""
	@echo "REMOTE COMMANDS:"
	@echo "  make deploy              - Deploy to remote server"
	@echo "  make remote-down         - Stop remote workers"
	@echo "  make remote-logs         - View remote logs"
	@echo "  make remote-status       - Check remote status"
	@echo "  make remote-scale W=name N=5 - Scale worker remotely"
	@echo ""
	@echo "WORKER UTILITIES:"
	@echo "  make worker-logs W=name  - View specific worker logs"
	@echo "  make worker-shell W=name - Shell into worker container"
	@echo "  make worker-metrics      - View worker metrics"
	@echo "  make test-worker-connection - Test Camunda connection"
	@echo ""
	@echo "DEVELOPMENT:"
	@echo "  make dev-setup           - Setup development environment"
	@echo "  make dev-run-worker W=name - Run worker in dev mode"
	@echo "  make validate-workers    - Validate worker configs"
	@echo ""
	@echo "SYSTEM:"
	@echo "  make system-info         - Show system and OS information"
	@echo ""
	@echo "CURRENT STATUS:"
	@echo "  OS: $(DETECTED_OS)"
	@echo "  Python: $(PYTHON_CMD)"
	@echo "  Environment: $(ENVIRONMENT)"
	@echo "  Remote: $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)"
	@echo "Camunda: $(CAMUNDA_URL)"

.DEFAULT_GOAL := help