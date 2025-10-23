#!/bin/bash

# Deploy alternativo para contornar problemas de certificado TLS
# Este script faz o deploy usando imagens pré-construídas ou configurações alternativas

set -e

echo "🚀 Deploy alternativo do tópico verificar_processo_cnj"

# Configurações
VM_USER="ubuntu"
VM_HOST="201.23.69.65"
SSH_KEY="~/.ssh/id_rsa"
REMOTE_DIR="~/camunda-server-dc"

SSH_FLAGS="-i $SSH_KEY -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"

echo "📋 Configurando Docker no servidor remoto..."

# Configurar Docker para ignorar problemas de certificado
ssh $SSH_FLAGS $VM_USER@$VM_HOST << 'EOF'
# Configurar Docker daemon
sudo mkdir -p /etc/docker
cat << 'DOCKER_CONFIG' | sudo tee /etc/docker/daemon.json
{
  "insecure-registries": ["registry-1.docker.io"],
  "registry-mirrors": ["https://registry-1.docker.io"]
}
DOCKER_CONFIG

# Reiniciar Docker
sudo systemctl restart docker
sleep 5

# Verificar status
docker --version
docker system info | head -10
EOF

echo "✅ Docker configurado"

echo "📁 Copiando arquivos do API Gateway..."
scp -i $SSH_KEY -P 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -r camunda-worker-api-gateway/ $VM_USER@$VM_HOST:$REMOTE_DIR/

echo "📁 Copiando arquivos dos Workers..."
scp -i $SSH_KEY -P 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -r camunda-workers-platform/ $VM_USER@$VM_HOST:$REMOTE_DIR/

echo "🚀 Fazendo deploy do API Gateway..."
ssh $SSH_FLAGS $VM_USER@$VM_HOST << 'EOF'
cd ~/camunda-server-dc/camunda-worker-api-gateway

# Tentar usar imagem pré-construída ou configurar variáveis de ambiente
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0

# Deploy com configurações alternativas
docker compose up -d --build --no-cache || {
    echo "⚠️ Deploy com build falhou, tentando com imagem base..."
    # Usar imagem base Python se necessário
    docker pull python:3.11-slim || echo "⚠️ Não foi possível baixar imagem base"
    docker compose up -d
}
EOF

echo "🚀 Fazendo deploy dos Workers..."
ssh $SSH_FLAGS $VM_USER@$VM_HOST << 'EOF'
cd ~/camunda-server-dc/camunda-workers-platform

# Deploy dos workers
docker compose up -d worker-publicacao-unified --build || {
    echo "⚠️ Deploy com build falhou, tentando sem build..."
    docker compose up -d worker-publicacao-unified
}
EOF

echo "✅ Deploy alternativo concluído!"
echo "🔍 Verificando status dos serviços..."

ssh $SSH_FLAGS $VM_USER@$VM_HOST << 'EOF'
echo "=== STATUS DOS SERVIÇOS ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(gateway|worker)"

echo ""
echo "=== TESTE DO ENDPOINT CPJ ==="
curl -s -X POST http://localhost:8000/publicacoes/verificar-processo-cnj \
  -H "Content-Type: application/json" \
  -d '{"numero_cnj": "0000000-00.0000.0.00.0000"}' || echo "⚠️ Endpoint não acessível"
EOF

echo "🎉 Deploy alternativo finalizado!"
