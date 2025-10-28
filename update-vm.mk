# Update VM - Makefile
VM_USER     ?= ubuntu
VM_HOST     ?= 201.23.69.65
SSH_PORT    ?= 22
SSH_KEY     ?= ~/.ssh/id_rsa

SSH_FLAGS := -i $(SSH_KEY) -p $(SSH_PORT) -o IdentitiesOnly=yes -o StrictHostKeyChecking=no
SSH := ssh $(SSH_FLAGS) $(VM_USER)@$(VM_HOST)

.PHONY: update-vm
update-vm:
	@echo "🔄 Updating VM with fresh code and rebuild..."
	@echo "📁 Syncing API Gateway code..."
	@cd camunda-worker-api-gateway && $(MAKE) copy-files
	@echo "📁 Syncing Workers Platform code..."
	@cd camunda-workers-platform && $(MAKE) copy-files
	@echo "🛑 Stopping all services..."
	@$(SSH) "cd ~/camunda-server-dc/camunda-worker-api-gateway && docker compose down || true"
	@$(SSH) "cd ~/camunda-server-dc/camunda-workers-platform && docker compose down || true"
	@echo "🗑️ Removing old images..."
	@$(SSH) "docker rmi camunda-worker-api-gateway-gateway 2>/dev/null || true"
	@$(SSH) "docker rmi camunda-workers-platform-workers 2>/dev/null || true"
	@echo "🔨 Rebuilding API Gateway without cache..."
	@$(SSH) "cd ~/camunda-server-dc/camunda-worker-api-gateway && docker compose build --no-cache"
	@echo "🔨 Rebuilding Workers Platform without cache..."
	@$(SSH) "cd ~/camunda-server-dc/camunda-workers-platform && docker compose build --no-cache"
	@echo "🚀 Starting API Gateway..."
	@$(SSH) "cd ~/camunda-server-dc/camunda-worker-api-gateway && docker compose up -d"
	@echo "🚀 Starting Workers Platform..."
	@$(SSH) "cd ~/camunda-server-dc/camunda-workers-platform && docker compose up -d"
	@echo "✅ VM update completed successfully!"
	@echo "📊 Checking services status..."
	@$(SSH) "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E '(gateway|worker)'"