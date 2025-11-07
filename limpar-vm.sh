#!/bin/bash

###############################################################################
# Script de Limpeza de Espaço em Disco - VM Produção
# VM: 201.23.69.65
# Uso: ./limpar-vm.sh
###############################################################################

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VM_HOST="201.23.69.65"
VM_USER="ubuntu"
SSH_KEY="~/.ssh/id_rsa"

echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  LIMPEZA DE ESPAÇO EM DISCO - VM PRODUÇÃO                 ║${NC}"
echo -e "${RED}║  ATENÇÃO: Esta operação vai PARAR serviços temporariamente║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}VM: ${VM_HOST}${NC}"
echo -e "${YELLOW}Usuário: ${VM_USER}${NC}"
echo ""

read -p "$(echo -e ${YELLOW}Deseja continuar? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Operação cancelada${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}═══ Conectando na VM...${NC}"

ssh -i ${SSH_KEY} ${VM_USER}@${VM_HOST} << 'ENDSSH'

set -e

echo ""
echo -e "\033[1;33m[1/6] Verificando espaço atual...\033[0m"
echo ""
df -h | grep -E "(Filesystem|/$)"
echo ""

echo -e "\033[1;33m[2/6] Parando containers Docker...\033[0m"
docker stop $(docker ps -aq) 2>/dev/null || echo "Nenhum container rodando"
echo ""

echo -e "\033[1;33m[3/6] Limpando containers, imagens e volumes...\033[0m"
echo "→ Removendo containers parados..."
docker container prune -f

echo "→ Removendo imagens não usadas..."
docker image prune -a -f

echo "→ Removendo volumes órfãos..."
docker volume prune -f

echo "→ Removendo redes não usadas..."
docker network prune -f

echo "→ Limpando build cache..."
docker builder prune -af
echo ""

echo -e "\033[1;33m[4/6] Limpando logs Docker...\033[0m"
sudo find /var/lib/docker/containers/ -name "*.log" -size +50M -exec rm {} \; 2>/dev/null || echo "Logs limpos"
echo ""

echo -e "\033[1;33m[5/6] Limpando logs de sistema...\033[0m"
sudo journalctl --vacuum-time=7d
sudo journalctl --vacuum-size=500M
echo ""

echo -e "\033[1;33m[6/6] Limpando cache do sistema...\033[0m"
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get autoremove --purge -y
sudo rm -rf /tmp/* 2>/dev/null || true
echo ""

echo -e "\033[0;32m╔════════════════════════════════════════════════════════════╗\033[0m"
echo -e "\033[0;32m║  LIMPEZA CONCLUÍDA                                         ║\033[0m"
echo -e "\033[0;32m╚════════════════════════════════════════════════════════════╝\033[0m"
echo ""
echo -e "\033[0;34mEspaço recuperado:\033[0m"
df -h | grep -E "(Filesystem|/$)"
echo ""

ENDSSH

echo ""
echo -e "${GREEN}✅ Limpeza concluída com sucesso!${NC}"
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo -e "  1. Verificar se há espaço suficiente (mínimo 5GB livres)"
echo -e "  2. Reiniciar serviços essenciais:"
echo -e "     ${BLUE}cd camunda-platform-standalone && make local-up${NC}"
echo -e "     ${BLUE}cd camunda-worker-api-gateway && make deploy${NC}"
echo -e "     ${BLUE}cd camunda-workers-platform && make deploy${NC}"
echo ""
echo -e "${YELLOW}Se ainda não tiver espaço suficiente:${NC}"
echo -e "  → Considere aumentar o disco da VM (Azure Portal)"
echo -e "  → Recomendado: 50GB mínimo"
echo ""
