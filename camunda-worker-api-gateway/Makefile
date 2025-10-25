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

.PHONY: deploy
deploy: copy-files
	@echo "🚀 Deploying API Gateway..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml up -d"
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