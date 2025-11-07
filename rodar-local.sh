#!/bin/bash

###############################################################################
# Script para Rodar Gateway + Workers Localmente
# Data: 2025-11-07
# Inclui: Worker DW LAW e-Protocol
###############################################################################

set -e  # Exit on error

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="/Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Rodando Gateway + Workers Localmente                     ║${NC}"
echo -e "${BLUE}║  Incluindo Worker DW LAW e-Protocol                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# STEP 1: Verificar Docker
###############################################################################
echo -e "${YELLOW}[STEP 1]${NC} Verificando Docker..."

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker não está rodando!${NC}"
    echo -e "${YELLOW}Inicie o Docker Desktop e tente novamente.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker está rodando${NC}"
echo ""

###############################################################################
# STEP 2: Verificar Portas
###############################################################################
echo -e "${YELLOW}[STEP 2]${NC} Verificando portas disponíveis..."

PORTS_TO_CHECK=(8000 8003 8004 8010 5672 6379 15672 9000)
PORTS_IN_USE=()

for port in "${PORTS_TO_CHECK[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        PORTS_IN_USE+=($port)
        echo -e "${YELLOW}⚠️  Porta $port em uso${NC}"
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    echo -e "${YELLOW}Portas em uso: ${PORTS_IN_USE[*]}${NC}"
    echo -e "${YELLOW}Deseja continuar mesmo assim? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deploy cancelado${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Verificação de portas concluída${NC}"
echo ""

###############################################################################
# STEP 3: Iniciar Gateway + Serviços
###############################################################################
echo -e "${YELLOW}[STEP 3]${NC} Iniciando Gateway + Serviços (MongoDB, RabbitMQ, Redis)..."
echo -e "${BLUE}Diretório:${NC} ${PROJECT_ROOT}/camunda-worker-api-gateway"
echo ""

cd "${PROJECT_ROOT}/camunda-worker-api-gateway"

# Para containers antigos se existirem
docker compose down 2>/dev/null || true

echo -e "${CYAN}🔨 Buildando Gateway...${NC}"
docker compose --profile local-services build gateway

echo -e "${CYAN}🚀 Iniciando serviços...${NC}"
# Inicia MongoDB, RabbitMQ, Redis e Gateway
docker compose --profile local-services up -d

echo -e "${CYAN}⏳ Aguardando Gateway inicializar (30 segundos)...${NC}"
sleep 30

# Verificar se Gateway está respondendo
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Gateway está rodando e respondendo!${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -e "${YELLOW}⏳ Aguardando Gateway... (tentativa $RETRY_COUNT/$MAX_RETRIES)${NC}"
        sleep 5
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Gateway não respondeu após ${MAX_RETRIES} tentativas${NC}"
    echo -e "${YELLOW}Ver logs:${NC} docker logs camunda-worker-api-gateway-gateway-1"
    exit 1
fi

echo ""

###############################################################################
# STEP 4: Iniciar Workers
###############################################################################
echo -e "${YELLOW}[STEP 4]${NC} Iniciando Workers (Publicacao, CPJ, DW LAW)..."
echo -e "${BLUE}Diretório:${NC} ${PROJECT_ROOT}/camunda-workers-platform"
echo ""

cd "${PROJECT_ROOT}/camunda-workers-platform"

# Para containers antigos se existirem
docker compose down 2>/dev/null || true

echo -e "${CYAN}🔨 Buildando Workers...${NC}"
docker compose build

echo -e "${CYAN}🚀 Iniciando Workers...${NC}"
docker compose up -d

echo -e "${CYAN}⏳ Aguardando Workers inicializarem (20 segundos)...${NC}"
sleep 20

# Verificar workers
echo ""
echo -e "${YELLOW}📊 Status dos Workers:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep worker || echo -e "${RED}Nenhum worker encontrado${NC}"

echo ""

###############################################################################
# STEP 5: Verificações de Saúde
###############################################################################
echo -e "${YELLOW}[STEP 5]${NC} Verificando saúde dos serviços..."
echo ""

# Gateway
echo -e "${CYAN}🔍 Gateway Health:${NC}"
if curl -s http://localhost:8000/health | jq . 2>/dev/null; then
    echo -e "${GREEN}✅ Gateway OK${NC}"
else
    echo -e "${RED}❌ Gateway com problemas${NC}"
fi
echo ""

# Worker DW LAW
echo -e "${CYAN}🔍 Worker DW LAW Health:${NC}"
if curl -s http://localhost:8010/health 2>/dev/null; then
    echo -e "${GREEN}✅ Worker DW LAW OK${NC}"
else
    echo -e "${YELLOW}⚠️  Worker DW LAW não respondeu (pode estar inicializando)${NC}"
fi
echo ""

# RabbitMQ
echo -e "${CYAN}🔍 RabbitMQ:${NC}"
if curl -s -u admin:admin123 http://localhost:15672/api/overview > /dev/null 2>&1; then
    echo -e "${GREEN}✅ RabbitMQ OK - Management: http://localhost:15672${NC}"
else
    echo -e "${YELLOW}⚠️  RabbitMQ não respondeu${NC}"
fi
echo ""

# Redis
echo -e "${CYAN}🔍 Redis:${NC}"
if docker exec camunda-worker-api-gateway-redis-1 redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis OK${NC}"
else
    echo -e "${YELLOW}⚠️  Redis não respondeu${NC}"
fi
echo ""

###############################################################################
# STEP 6: Teste de Integração DW LAW
###############################################################################
echo -e "${YELLOW}[STEP 6]${NC} Testando integração DW LAW..."
echo ""

echo -e "${CYAN}🔍 Testando conexão DW LAW...${NC}"
DW_LAW_TEST=$(curl -s http://localhost:8000/dw-law/test-connection)

if echo "$DW_LAW_TEST" | jq -e '.success == true' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Conexão DW LAW OK${NC}"
    echo "$DW_LAW_TEST" | jq .
else
    echo -e "${RED}❌ Erro na conexão DW LAW${NC}"
    echo "$DW_LAW_TEST" | jq .
fi

echo ""

###############################################################################
# RESUMO FINAL
###############################################################################
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RESUMO - Ambiente Local                                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}✅ Serviços Iniciados:${NC}"
echo ""

echo -e "${CYAN}Gateway:${NC}"
echo -e "  📍 API:        http://localhost:8000"
echo -e "  📍 Docs:       http://localhost:8000/docs"
echo -e "  📍 Health:     http://localhost:8000/health"
echo -e "  📍 Metrics:    http://localhost:9000/metrics"
echo ""

echo -e "${CYAN}Workers:${NC}"
echo -e "  📍 DW LAW:     http://localhost:8010 (metrics)"
echo -e "  📍 Publicacao: http://localhost:8003 (metrics)"
echo -e "  📍 CPJ:        http://localhost:8004 (metrics)"
echo ""

echo -e "${CYAN}Serviços Auxiliares:${NC}"
echo -e "  📍 RabbitMQ:   http://localhost:15672 (admin/admin123)"
echo -e "  📍 Redis:      localhost:6379"
echo -e "  📍 MongoDB:    Azure Cosmos DB (remoto)"
echo ""

echo -e "${CYAN}Camunda (Remoto):${NC}"
echo -e "  📍 Cockpit:    http://201.23.67.197:8080/camunda/app/cockpit"
echo -e "  📍 Login:      demo / DiasCostaA!!2025"
echo ""

echo -e "${GREEN}📋 Comandos Úteis:${NC}"
echo ""
echo -e "  # Ver logs Gateway:"
echo -e "  docker logs -f camunda-worker-api-gateway-gateway-1"
echo ""
echo -e "  # Ver logs Worker DW LAW:"
echo -e "  docker logs -f worker-dw-law"
echo ""
echo -e "  # Testar DW LAW:"
echo -e "  curl http://localhost:8000/dw-law/test-connection | jq ."
echo ""
echo -e "  # Parar tudo:"
echo -e "  cd ${PROJECT_ROOT}/camunda-worker-api-gateway && docker compose down"
echo -e "  cd ${PROJECT_ROOT}/camunda-workers-platform && docker compose down"
echo ""

echo -e "${YELLOW}📝 Próximos Passos:${NC}"
echo -e "  1. Acessar Swagger: http://localhost:8000/docs"
echo -e "  2. Testar endpoints DW LAW"
echo -e "  3. Criar processo BPMN de teste no Camunda"
echo -e "  4. Executar processo e verificar logs"
echo ""

echo -e "${GREEN}🎉 Ambiente local pronto para desenvolvimento!${NC}"
echo ""
