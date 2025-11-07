#!/bin/bash

###############################################################################
# Script de Preparação da VM para Deploy
# Cria redes Docker necessárias e prepara ambiente
# VM: 201.23.69.65
###############################################################################

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

VM_HOST="201.23.69.65"
VM_USER="ubuntu"
SSH_KEY="~/.ssh/id_rsa"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Preparando VM para Deploy                                 ║${NC}"
echo -e "${BLUE}║  VM: ${VM_HOST}                                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}[1/5] Verificando conexão SSH...${NC}"
if ssh -i ${SSH_KEY} ${VM_USER}@${VM_HOST} "echo 'Conectado'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH OK${NC}"
else
    echo -e "${RED}❌ Erro ao conectar via SSH${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}[2/5] Verificando espaço em disco...${NC}"
ssh -i ${SSH_KEY} ${VM_USER}@${VM_HOST} << 'ENDSSH'
df -h | grep -E "(Filesystem|/$)"
ENDSSH
echo ""

echo -e "${YELLOW}[3/5] Criando redes Docker...${NC}"
ssh -i ${SSH_KEY} ${VM_USER}@${VM_HOST} << 'ENDSSH'
# Criar redes necessárias
docker network create camunda-gateway-network 2>/dev/null || echo "  → camunda-gateway-network já existe"
docker network create camunda-worker-api-gateway_backend 2>/dev/null || echo "  → camunda-worker-api-gateway_backend já existe"
docker network create camunda-workers-platform_default 2>/dev/null || echo "  → camunda-workers-platform_default já existe"
docker network create camunda-workers-platform_gateway_network 2>/dev/null || echo "  → camunda-workers-platform_gateway_network já existe"
docker network create camunda-workers-platform_camunda_network 2>/dev/null || echo "  → camunda-workers-platform_camunda_network já existe"

echo ""
echo "📋 Redes Docker criadas/verificadas:"
docker network ls | grep -E "(camunda|gateway|worker)"
ENDSSH
echo ""

echo -e "${YELLOW}[4/5] Criando diretórios...${NC}"
ssh -i ${SSH_KEY} ${VM_USER}@${VM_HOST} << 'ENDSSH'
mkdir -p ~/camunda-server-dc/camunda-worker-api-gateway
mkdir -p ~/camunda-server-dc/camunda-workers-platform/workers
echo "✅ Diretórios criados"
ENDSSH
echo ""

echo -e "${YELLOW}[5/5] Verificando Docker Compose...${NC}"
ssh -i ${SSH_KEY} ${VM_USER}@${VM_HOST} << 'ENDSSH'
docker compose version
ENDSSH
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  VM Preparada com Sucesso!                                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Próximos passos:${NC}"
echo -e "  1. Deploy Gateway:"
echo -e "     ${YELLOW}cd camunda-worker-api-gateway && make deploy${NC}"
echo ""
echo -e "  2. Deploy Workers:"
echo -e "     ${YELLOW}cd camunda-workers-platform && make deploy${NC}"
echo ""
