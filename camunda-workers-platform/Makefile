# Workers Platform - Makefile
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.69.65
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/id_rsa
REMOTE_DIR  ?= ~/camunda-server-dc/camunda-workers-platform

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

.PHONY: deploy
deploy: copy-files
	@echo "🚀 Deploying Workers Platform..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose -f docker-compose.yml up -d"
	@echo "✅ Workers Platform deployed"

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

.PHONY: stop
stop:
	@echo "⏹️ Stopping Workers Platform..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down"
	@echo "✅ Workers Platform stopped"