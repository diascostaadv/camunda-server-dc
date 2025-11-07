#!/bin/bash
# Script master para executar todos os testes de BPMN errors

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMUNDA_URL="${CAMUNDA_URL:-http://localhost:8080}"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Suite de Testes: BPMN Errors"
echo "=========================================="
echo ""

# Verificar se Camunda está rodando
echo -n "Verificando conectividade com Camunda... "
if curl -s -f "${CAMUNDA_URL}/camunda/api/engine/engine/default/version" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FALHOU${NC}"
    echo "Camunda não está acessível em ${CAMUNDA_URL}"
    echo "Execute: make start"
    exit 1
fi

# Verificar se worker está rodando
echo -n "Verificando worker... "
if docker ps | grep -q publicacao-unified-worker; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FALHOU${NC}"
    echo "Worker não está rodando"
    exit 1
fi

echo ""
echo "=========================================="
echo "Executando Testes"
echo "=========================================="
echo ""

# Array de testes
tests=(
    "01_test_erro_validacao_nova_publicacao.sh"
    "02_test_erro_validacao_busca.sh"
    "03_test_erro_validacao_classificacao.sh"
)

# Contador
total=${#tests[@]}
passed=0
failed=0

for test_script in "${tests[@]}"; do
    test_path="${SCRIPT_DIR}/${test_script}"

    if [ ! -f "$test_path" ]; then
        echo -e "${RED}✗${NC} Script não encontrado: $test_script"
        ((failed++))
        continue
    fi

    echo ""
    echo "=== Executando: $test_script ==="

    if bash "$test_path"; then
        echo -e "${GREEN}✔${NC} PASSOU: $test_script"
        ((passed++))
    else
        echo -e "${RED}✗${NC} FALHOU: $test_script"
        ((failed++))
    fi

    # Aguardar um pouco entre testes
    sleep 2
done

echo ""
echo "=========================================="
echo "Resumo dos Testes"
echo "=========================================="
echo -e "Total:   $total"
echo -e "${GREEN}Passou:  $passed${NC}"
echo -e "${RED}Falhou:  $failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ Todos os testes passaram!${NC}"
    exit 0
else
    echo -e "${RED}❌ Alguns testes falharam${NC}"
    exit 1
fi
