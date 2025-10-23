#!/bin/bash

# Script de migração do modo simples para Docker Swarm
# Migra containers existentes para o modo Swarm

echo "🔄 Iniciando migração para Docker Swarm..."

# 1. Parar containers existentes
echo "⏹️ Parando containers existentes..."
docker stop $(docker ps -q) 2>/dev/null || true

# 2. Inicializar Docker Swarm se não estiver ativo
echo "🎯 Verificando Docker Swarm..."
if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
    echo "Inicializando Docker Swarm..."
    docker swarm init
    echo "✅ Docker Swarm inicializado"
else
    echo "✅ Docker Swarm já está ativo"
fi

# 3. Criar rede externa do Traefik
echo "🌐 Criando rede do Traefik..."
docker network create --driver overlay traefik 2>/dev/null || echo "Rede traefik já existe"

# 4. Configurar variáveis de ambiente
echo "⚙️ Configurando variáveis de ambiente..."
cat > .env <<EOF
# Database Configuration
POSTGRES_DB=camunda
POSTGRES_USER=camunda
POSTGRES_PASSWORD=camunda_secure_$(date +%s)
DATABASE_URL=jdbc:postgresql://db:5432/camunda

# Camunda Configuration
CAMUNDA_PORT=8080
CAMUNDA_JMX_PORT=9404
CAMUNDA_REPLICAS=1

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
GF_SECURITY_ADMIN_PASSWORD=admin_secure_$(date +%s)

# Network Configuration
NETWORK_DRIVER=overlay
TZ=America/Sao_Paulo

# Security Configuration
DB_CONNECTION_TIMEOUT=30000
DB_IDLE_TIMEOUT=600000
DB_MAX_LIFETIME=1800000
DB_MAXIMUM_POOL_SIZE=20
EOF

# 5. Deploy do Traefik primeiro
echo "🌐 Deploying Traefik..."
cd traefik
docker stack deploy -c docker-compose.yml traefik
cd ..

# Aguardar Traefik estar pronto
echo "⏳ Aguardando Traefik estar pronto..."
sleep 30

# 6. Deploy da plataforma Camunda
echo "🚀 Deploying Camunda Platform..."
cd camunda-platform-standalone
docker stack deploy -c docker-compose.swarm.yml camunda-platform
cd ..

# 7. Verificar status dos serviços
echo "📊 Verificando status dos serviços..."
sleep 10

echo "=== DOCKER STACKS ==="
docker stack ls

echo "=== DOCKER SERVICES ==="
docker service ls

echo "=== DOCKER CONTAINERS ==="
docker ps

# 8. Configurar monitoramento
echo "📈 Configurando monitoramento..."
if [ -f "scripts/setup-monitoring.sh" ]; then
    bash scripts/setup-monitoring.sh production
fi

echo "✅ Migração para Docker Swarm concluída!"
echo ""
echo "🌐 URLs dos serviços:"
echo "  - Traefik Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo "  - Camunda Platform: http://$(hostname -I | awk '{print $1}'):8080"
echo "  - Prometheus: http://$(hostname -I | awk '{print $1}'):9090"
echo "  - Grafana: http://$(hostname -I | awk '{print $1}'):3001"
echo ""
echo "📋 Comandos úteis:"
echo "  - Ver logs: docker service logs -f camunda-platform_camunda"
echo "  - Escalar serviço: docker service scale camunda-platform_camunda=2"
echo "  - Remover stack: docker stack rm camunda-platform"

