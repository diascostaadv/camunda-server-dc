# Workers Platform - Makefile
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.69.65
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/azure_vm
REMOTE_DIR  ?= ~/camunda-server-dc/camunda-workers-platform

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

.PHONY: deploy
deploy: copy-files
	@echo "🚀 Deploying Workers Platform..."
	@echo "⏹️  Stopping existing containers..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml down"
	@echo "🔨 Rebuilding images (no cache)..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml build --no-cache"
	@echo "🚀 Starting services..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml up -d"
	@echo "✅ Workers Platform deployed and restarted with fresh images"

.PHONY: deploy-fast
deploy-fast: copy-files
	@echo "⚡ Fast deploying Workers Platform (reusing cached images)..."
	@echo "⏹️  Stopping existing containers..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml down"
	@echo "🚀 Starting services..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml up -d"
	@echo "✅ Workers Platform deployed (fast mode)"

.PHONY: copy-files
copy-files:
	@echo "📁 Copying Workers files..."
	$(SSH) "mkdir -p $(REMOTE_DIR)"
	$(SCP) -r . $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@echo "✅ Files copied"

.PHONY: status
status:
	@echo "📊 Workers status..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose ps"

.PHONY: logs
logs:
	@echo "📋 Workers logs..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose logs -f"

.PHONY: restart
restart:
	@echo "🔄 Restarting Workers Platform..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down && docker compose up -d"
	@echo "✅ Workers Platform restarted"

.PHONY: rebuild
rebuild:
	@echo "🔨 Rebuilding Workers Platform (no cache)..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down && docker compose build --no-cache && docker compose up -d"
	@echo "✅ Workers Platform rebuilt and restarted"

.PHONY: stop
stop:
	@echo "⏹️ Stopping Workers Platform..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down"
	@echo "✅ Workers Platform stopped"