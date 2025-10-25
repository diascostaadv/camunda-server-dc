#!/bin/bash
# Script para executar testes CPJ isolados
# Uso: ./run_cpj_tests.sh [opcao]
# Opções: unit, integration, all, coverage

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Diretório base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
GATEWAY_DIR="$(dirname "$APP_DIR")"
VENV_DIR="${SCRIPT_DIR}/.venv"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Testes CPJ - Worker API Gateway${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verifica se virtualenv existe
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Ambiente virtual não encontrado!${NC}"
    echo -e "${CYAN}🔧 Execute primeiro: ${YELLOW}./setup_test_env.sh${NC}"
    echo ""
    echo -e "${CYAN}Deseja criar o ambiente agora? (s/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Ss]$ ]]; then
        echo ""
        ./setup_test_env.sh
        echo ""
    else
        echo -e "${RED}❌ Ambiente necessário para executar testes${NC}"
        exit 1
    fi
fi

# Ativa virtualenv
echo -e "${CYAN}🔌 Ativando ambiente virtual...${NC}"
source "$VENV_DIR/bin/activate"

# Verifica se pytest está instalado no venv
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}❌ pytest não está instalado no ambiente virtual!${NC}"
    echo -e "${YELLOW}Execute: ./setup_test_env.sh --clean${NC}"
    deactivate
    exit 1
fi

PYTEST_VERSION=$(python -c "import pytest; print(pytest.__version__)")
echo -e "${GREEN}✅ pytest ${PYTEST_VERSION} (virtualenv ativo)${NC}"
echo ""

# Define tipo de teste (padrão: all)
TEST_TYPE="${1:-all}"

# Configuração do PYTHONPATH
export PYTHONPATH="${APP_DIR}:${PYTHONPATH}"

cd "$APP_DIR"

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}🧪 Executando testes UNITÁRIOS do CPJService...${NC}"
        echo ""
        python -m pytest tests/test_cpj_service.py -v --tb=short
        ;;

    integration)
        echo -e "${GREEN}🔗 Executando testes de INTEGRAÇÃO do endpoint...${NC}"
        echo ""
        python -m pytest tests/test_cpj_endpoint.py -v --tb=short
        ;;

    coverage)
        echo -e "${GREEN}📊 Executando testes com COBERTURA...${NC}"
        echo ""
        python -m pytest tests/test_cpj*.py \
            --cov=services.cpj_service \
            --cov=routers.publicacoes \
            --cov-report=term-missing \
            --cov-report=html:tests/htmlcov \
            -v

        echo ""
        echo -e "${GREEN}✅ Relatório HTML gerado em: tests/htmlcov/index.html${NC}"
        ;;

    quick)
        echo -e "${GREEN}⚡ Execução RÁPIDA (sem verbose)...${NC}"
        echo ""
        python -m pytest tests/test_cpj*.py -q
        ;;

    debug)
        echo -e "${GREEN}🐛 Execução em modo DEBUG...${NC}"
        echo ""
        python -m pytest tests/test_cpj*.py -vv -s --tb=long --log-cli-level=DEBUG
        ;;

    specific)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Especifique o teste: ./run_cpj_tests.sh specific TestClassName::test_name${NC}"
            exit 1
        fi
        echo -e "${GREEN}🎯 Executando teste específico: $2${NC}"
        echo ""
        python -m pytest "tests/test_cpj_service.py::$2" -vv -s
        ;;

    all|*)
        echo -e "${GREEN}🚀 Executando TODOS os testes CPJ...${NC}"
        echo ""
        python -m pytest tests/test_cpj*.py -v --tb=short
        ;;
esac

# Captura exit code
EXIT_CODE=$?

# Desativa virtualenv
deactivate

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Todos os testes passaram com sucesso!${NC}"
else
    echo -e "${RED}❌ Alguns testes falharam (código: $EXIT_CODE)${NC}"
fi

echo -e "${BLUE}========================================${NC}"

exit $EXIT_CODE
