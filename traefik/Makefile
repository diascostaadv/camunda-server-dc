# Traefik - Makefile
VM_USER     ?= ubuntu
VM_HOST     ?= dccamunda.duckdns.org
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/id_rsa
REMOTE_DIR  ?= ~/camunda-platform/traefik

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SCP_FLAGS := -i $(SSH_KEY) -P $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)
SCP := scp $(SCP_FLAGS)

.PHONY: deploy
deploy: copy-files setup
	@echo "✅ Traefik deployed"

.PHONY: copy-files
copy-files:
	@echo "📁 Copying Traefik files..."
	$(SSH) "mkdir -p $(REMOTE_DIR)"
	$(SCP) -r . $(VM_USER)@$(VM_HOST):$(REMOTE_DIR)/
	@echo "✅ Files copied"

.PHONY: setup
setup:
	@echo "🚀 Setting up Traefik..."
	$(SSH) "cd $(REMOTE_DIR) && \
		touch acme.json && \
		chmod 600 acme.json && \
		docker network create traefik || true && \
		docker compose up -d"
	@echo "✅ Traefik setup completed"

.PHONY: status
status:
	@echo "📊 Traefik status..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose ps"

.PHONY: logs
logs:
	@echo "📋 Traefik logs..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose logs -f"

.PHONY: restart
restart:
	@echo "🔄 Restarting Traefik..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down && docker compose up -d"
	@echo "✅ Traefik restarted"

.PHONY: stop
stop:
	@echo "⏹️ Stopping Traefik..."
	$(SSH) "cd $(REMOTE_DIR) && docker compose down"
	@echo "✅ Traefik stopped"
