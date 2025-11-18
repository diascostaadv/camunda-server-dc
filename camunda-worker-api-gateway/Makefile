# API Gateway - Makefile
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.69.65
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/id_rsa
REMOTE_DIR  ?= ~/camunda-server-dc/camunda-worker-api-gateway

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
RSYNC_FLAGS := -avz --progress --delete --exclude-from=.rsyncignore
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)
RSYNC := rsync $(RSYNC_FLAGS) -e "ssh $(SSH_FLAGS)"

# ============================================
# LOCAL DEVELOPMENT
# ============================================

.PHONY: local-up
local-up:
	@echo "🚀 Starting API Gateway locally (with local services)..."
	@echo "📋 Using .env.local configuration"
	docker network create camunda-gateway-network 2>/dev/null || true
	docker compose --env-file .env.local --profile local-services up -d --build
	@echo "✅ API Gateway started locally"
	@echo "📍 Gateway API: http://localhost:8000"
	@echo "📍 Metrics: http://localhost:9000"
	@echo "📍 MongoDB: localhost:27017 (admin/admin123)"
	@echo "📍 RabbitMQ Management: http://localhost:15672 (admin/admin123)"
	@echo "📍 Redis: localhost:6379"

.PHONY: local-up-external
local-up-external:
	@echo "🚀 Starting API Gateway locally (with external Azure services)..."
	@echo "📋 Using .env.local with EXTERNAL_SERVICES_MODE=true"
	docker network create camunda-gateway-network 2>/dev/null || true
	docker compose --env-file .env.local up -d --build
	@echo "✅ API Gateway started with external services"
	@echo "📍 Gateway API: http://localhost:8000"
	@echo "📍 Metrics: http://localhost:9000"

.PHONY: local-up-prod
local-up-prod:
	@echo "🚀 Starting API Gateway locally (with PRODUCTION config)..."
	@echo "📋 Using .env.production (Azure MongoDB, Redis, etc)"
	docker network create camunda-gateway-network 2>/dev/null || true
	docker compose --env-file .env.production up -d --build
	@echo "✅ API Gateway started with production config"
	@echo "📍 Gateway API: http://localhost:8080"
	@echo "📍 Metrics: http://localhost:9000"
	@echo "⚠️  Using PRODUCTION databases and services!"

.PHONY: local-down
local-down:
	@echo "⏹️ Stopping API Gateway locally..."
	docker compose --env-file .env.local --profile local-services down
	@echo "✅ API Gateway stopped"

.PHONY: local-down-prod
local-down-prod:
	@echo "⏹️ Stopping API Gateway (production config)..."
	docker compose --env-file .env.production down
	@echo "✅ API Gateway stopped"

.PHONY: local-logs
local-logs:
	@echo "📋 Showing API Gateway logs..."
	docker compose --env-file .env.local logs -f gateway

.PHONY: local-status
local-status:
	@echo "📊 API Gateway local status..."
	docker compose --env-file .env.local ps

.PHONY: local-restart
local-restart:
	@echo "🔄 Restarting API Gateway locally..."
	docker compose --env-file .env.local --profile local-services down
	docker compose --env-file .env.local --profile local-services up -d --build
	@echo "✅ API Gateway restarted"

.PHONY: local-test
local-test:
	@echo "🧪 Testing API Gateway health..."
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ API Gateway not responding"

.PHONY: health-check
health-check:
	@echo "🏥 Running comprehensive health check..."
	@echo "\n📡 Testing Gateway API..."
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Gateway not responding"
	@echo "\n📊 Testing Metrics..."
	@curl -s http://localhost:9000/metrics | head -10 || echo "❌ Metrics not available"
	@echo "\n💾 Testing MongoDB..."
	@docker exec $$(docker ps -qf "name=mongodb") mongosh --eval "db.adminCommand('ping')" 2>/dev/null || echo "❌ MongoDB not accessible"
	@echo "\n🐰 Testing RabbitMQ..."
	@curl -s -u admin:admin123 http://localhost:15672/api/overview 2>/dev/null | python3 -m json.tool | head -20 || echo "❌ RabbitMQ not accessible"
	@echo "\n✅ Health check complete"

# ============================================
# PRODUCTION DEPLOYMENT
# ============================================

.PHONY: deploy
deploy: copy-files
	@echo "🚀 Deploying API Gateway..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml up --build -d"
	@echo "✅ API Gateway deployed"

.PHONY: copy-files
copy-files:
	@echo "📁 Copying API Gateway files (excluding tests, cache, .venv)..."
	$(SSH) "mkdir -p $(REMOTE_DIR)"
	$(RSYNC) ./ $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@echo "✅ Files copied (optimized with rsync)"

.PHONY: status
status:
	@echo "📊 API Gateway status..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose ps"

.PHONY: logs
logs:
	@echo "📋 API Gateway logs..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose logs -f"

.PHONY: restart
restart:
	@echo "🔄 Restarting API Gateway..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down && docker compose up -d"
	@echo "✅ API Gateway restarted"

.PHONY: stop
stop:
	@echo "⏹️ Stopping API Gateway..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down"
	@echo "✅ API Gateway stopped"