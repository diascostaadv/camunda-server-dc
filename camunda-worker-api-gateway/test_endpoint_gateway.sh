#!/bin/bash
# Script para testar endpoint do API Gateway
# Testa configurações que SABEMOS que retornam publicações

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configurações
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
ENDPOINT="/buscar-publicacoes/processar-task-v2"

echo -e "${BOLD}${BLUE}=================================================================${NC}"
echo -e "${BOLD}${BLUE}       TESTE DO ENDPOINT API GATEWAY - BUSCAR PUBLICAÇÕES       ${NC}"
echo -e "${BOLD}${BLUE}=================================================================${NC}\n"

echo -e "${CYAN}Gateway URL:${NC} $GATEWAY_URL"
echo -e "${CYAN}Endpoint:${NC} $ENDPOINT\n"

# Função para testar endpoint
test_endpoint() {
    local test_name="$1"
    local json_data="$2"

    echo -e "${BOLD}📋 Teste: $test_name${NC}"
    echo -e "${CYAN}Payload:${NC}"
    echo "$json_data" | jq '.' 2>/dev/null || echo "$json_data"
    echo ""

    echo -e "${YELLOW}⏳ Enviando requisição...${NC}"

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$json_data" \
        "${GATEWAY_URL}${ENDPOINT}")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo -e "${CYAN}HTTP Status:${NC} $http_code"

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Sucesso!${NC}\n"

        # Extrair total_encontradas do JSON
        total=$(echo "$body" | jq -r '.total_encontradas' 2>/dev/null)

        if [ "$total" != "null" ] && [ "$total" != "" ]; then
            if [ "$total" -gt 0 ]; then
                echo -e "${GREEN}${BOLD}🎉 PUBLICAÇÕES ENCONTRADAS: $total${NC}"
            else
                echo -e "${YELLOW}⚠️  0 publicações encontradas${NC}"
            fi

            # Mostrar estatísticas
            echo -e "\n${BOLD}📊 Estatísticas:${NC}"
            echo "$body" | jq '{
                total_encontradas,
                total_processadas,
                instancias_criadas,
                instancias_com_erro,
                taxa_sucesso,
                duracao_segundos
            }' 2>/dev/null || echo "$body"
        else
            echo -e "${BOLD}Resposta:${NC}"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
    else
        echo -e "${RED}❌ Erro!${NC}\n"
        echo -e "${BOLD}Resposta:${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    fi

    echo -e "\n${BLUE}=================================================================${NC}\n"
}

# TESTE 1: Usar configurações padrão (grupo 5, últimos 180 dias)
echo -e "${BOLD}${CYAN}TESTE 1: Configurações Padrão (Grupo 5, Branch 3 - sem datas)${NC}"
echo -e "Deve usar: grupo 5 + últimos 180 dias automaticamente\n"

test_endpoint "Configurações Padrão" '{
    "task_id": "test-001",
    "process_instance_id": "test-instance-001",
    "topic_name": "BuscarPublicacoes",
    "worker_id": "test-worker",
    "variables": {}
}'

# TESTE 2: Fevereiro/2025 explícito (232 publicações esperadas)
echo -e "${BOLD}${CYAN}TESTE 2: Fevereiro/2025 - Período com Mais Dados (Branch 2)${NC}"
echo -e "Esperado: ~232 publicações\n"

test_endpoint "Fevereiro 2025" '{
    "task_id": "test-002",
    "process_instance_id": "test-instance-002",
    "topic_name": "BuscarPublicacoes",
    "worker_id": "test-worker",
    "variables": {
        "data_inicial": "2025-02-01",
        "data_final": "2025-02-28",
        "cod_grupo": 5
    }
}'

# TESTE 3: Janeiro/2025 (7 publicações esperadas)
echo -e "${BOLD}${CYAN}TESTE 3: Janeiro/2025 - Período com Poucos Dados (Branch 2)${NC}"
echo -e "Esperado: ~7 publicações\n"

test_endpoint "Janeiro 2025" '{
    "task_id": "test-003",
    "process_instance_id": "test-instance-003",
    "topic_name": "BuscarPublicacoes",
    "worker_id": "test-worker",
    "variables": {
        "data_inicial": "2025-01-01",
        "data_final": "2025-01-31",
        "cod_grupo": 5
    }
}'

# TESTE 4: Apenas não exportadas (Branch 1)
echo -e "${BOLD}${CYAN}TESTE 4: Apenas Não Exportadas (Branch 1)${NC}"
echo -e "Pode retornar 0 se todas já foram exportadas\n"

test_endpoint "Apenas Não Exportadas" '{
    "task_id": "test-004",
    "process_instance_id": "test-instance-004",
    "topic_name": "BuscarPublicacoes",
    "worker_id": "test-worker",
    "variables": {
        "apenas_nao_exportadas": true,
        "cod_grupo": 5
    }
}'

# Resumo
echo -e "${BOLD}${BLUE}=================================================================${NC}"
echo -e "${BOLD}${BLUE}                         RESUMO DOS TESTES                       ${NC}"
echo -e "${BOLD}${BLUE}=================================================================${NC}\n"

echo -e "${BOLD}Mudanças Aplicadas:${NC}"
echo -e "  ${GREEN}✅${NC} Grupo padrão alterado: 2 → 5"
echo -e "  ${GREEN}✅${NC} Período padrão alterado: desde 01/08/2025 → últimos 180 dias"
echo -e "  ${GREEN}✅${NC} Parâmetro intExportada=0 ativo"
echo -e "  ${GREEN}✅${NC} Logging detalhado habilitado\n"

echo -e "${BOLD}Períodos com Dados Confirmados:${NC}"
echo -e "  ${GREEN}•${NC} Fevereiro/2025: 232 publicações"
echo -e "  ${GREEN}•${NC} Janeiro/2025: 7 publicações"
echo -e "  ${GREEN}•${NC} Outubro/2024: 2 publicações"
echo -e "  ${GREEN}•${NC} Setembro/2024: 2 publicações\n"

echo -e "${BOLD}${CYAN}💡 Próximos Passos:${NC}"
echo -e "  1. Verificar logs do Gateway para mensagens:"
echo -e "     ${CYAN}📤 Parâmetros SOAP: ...intExportada=0${NC}"
echo -e "     ${CYAN}📥 Resultado: X publicações encontradas...${NC}"
echo -e ""
echo -e "  2. Se Gateway não estiver rodando, iniciar com:"
echo -e "     ${YELLOW}docker-compose up -d gateway${NC}"
echo -e ""
echo -e "  3. Monitorar logs:"
echo -e "     ${YELLOW}docker-compose logs -f gateway${NC}"
echo -e ""

echo -e "${BLUE}=================================================================${NC}\n"
