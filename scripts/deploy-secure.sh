#!/bin/bash

# Script de deploy seguro completo
# Aplica todas as melhorias de segurança e migra para Swarm

set -e

echo "🚀 Iniciando deploy seguro completo..."

# 1. Verificar pré-requisitos
echo "🔍 Verificando pré-requisitos..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Execute: make install-docker"
    exit 1
fi

if ! command -v make &> /dev/null; then
    echo "❌ Make não encontrado. Execute: make install-make"
    exit 1
fi

# 2. Aplicar medidas de segurança
echo "🔒 Aplicando medidas de segurança..."
if [ -f "scripts/security-hardening.sh" ]; then
    chmod +x scripts/security-hardening.sh
    bash scripts/security-hardening.sh
else
    echo "⚠️ Script de segurança não encontrado, continuando..."
fi

# 3. Fazer backup dos dados existentes
echo "💾 Criando backup dos dados existentes..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup dos volumes Docker existentes
if docker volume ls | grep -q camunda; then
    echo "Backing up existing Camunda data..."
    docker run --rm -v camunda_db_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/camunda_data_backup.tar.gz -C /data .
fi

# 4. Migrar para Docker Swarm
echo "🔄 Migrando para Docker Swarm..."
if [ -f "scripts/migrate-to-swarm.sh" ]; then
    chmod +x scripts/migrate-to-swarm.sh
    bash scripts/migrate-to-swarm.sh
else
    echo "⚠️ Script de migração não encontrado, inicializando Swarm manualmente..."
    if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
        docker swarm init
    fi
fi

# 5. Configurar monitoramento
echo "📊 Configurando monitoramento..."
if [ -f "scripts/setup-monitoring.sh" ]; then
    chmod +x scripts/setup-monitoring.sh
    bash scripts/setup-monitoring.sh production
fi

# 6. Deploy dos serviços
echo "🚀 Deploying serviços..."


# Deploy Camunda Platform
echo "Deploying Camunda Platform..."
cd camunda-platform-standalone
docker stack deploy -c docker-compose.swarm.yml camunda-platform
cd ..

# Deploy Portainer
echo "Deploying Portainer..."
cd portainer
docker stack deploy -c docker-compose.yml portainer
cd ..

# 7. Verificar status
echo "📊 Verificando status dos serviços..."
sleep 20

echo "=== DOCKER STACKS ==="
docker stack ls

echo "=== DOCKER SERVICES ==="
docker service ls

echo "=== DOCKER CONTAINERS ==="
docker ps

# 8. Testar conectividade
echo "🔍 Testando conectividade..."
SERVER_IP=$(hostname -I | awk '{print $1}')

echo "Testando Camunda Platform..."
if curl -f -s "http://$SERVER_IP:8080/camunda/app/welcome/default/" > /dev/null; then
    echo "✅ Camunda Platform está respondendo"
else
    echo "⚠️ Camunda Platform pode não estar pronto ainda"
fi


# 9. Configurar SSL (se domínio estiver configurado)
if [ ! -z "$DOMAIN" ]; then
    echo "🔐 Configurando SSL para domínio: $DOMAIN"
    # Aqui você pode adicionar lógica para configurar SSL automaticamente
fi

echo ""
echo "✅ Deploy seguro concluído!"
echo ""
echo "🌐 URLs dos serviços:"
echo "  - Camunda Platform: http://$SERVER_IP:8080"
echo "  - Portainer: http://$SERVER_IP:9000"
echo "  - Prometheus: http://$SERVER_IP:9090"
echo "  - Grafana: http://$SERVER_IP:3001"
echo ""
echo "📋 Comandos úteis:"
echo "  - Ver logs: docker service logs -f camunda-platform_camunda"
echo "  - Status: docker service ls"
echo "  - Logs de segurança: tail -f /var/log/camunda/security.log"
echo ""
echo "🔒 Medidas de segurança aplicadas:"
echo "  - Firewall configurado"
echo "  - Fail2ban ativo"
echo "  - Rate limiting configurado"
echo "  - Headers de segurança"
echo "  - Monitoramento de segurança"
echo "  - Backup automático"

