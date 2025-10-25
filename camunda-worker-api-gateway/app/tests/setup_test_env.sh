#!/bin/bash
# Script para configurar ambiente de testes CPJ
# Cria virtualenv isolado e instala dependências

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Setup Ambiente de Testes CPJ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verifica versão do Python
echo -e "${CYAN}🔍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado!${NC}"
    echo -e "${YELLOW}Instale Python 3.8+ e tente novamente.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} encontrado${NC}"
echo ""

# Remove venv existente se solicitado
if [ "$1" == "--clean" ]; then
    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}🧹 Removendo ambiente virtual existente...${NC}"
        rm -rf "$VENV_DIR"
        echo -e "${GREEN}✅ Ambiente limpo${NC}"
        echo ""
    fi
fi

# Verifica se venv já existe
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Ambiente virtual já existe em: ${VENV_DIR}${NC}"
    echo -e "${YELLOW}   Use './setup_test_env.sh --clean' para recriar${NC}"
    echo ""

    # Ativa venv existente para verificar
    source "$VENV_DIR/bin/activate"

    # Verifica se pytest está instalado
    if python -c "import pytest" 2>/dev/null; then
        PYTEST_VERSION=$(python -c "import pytest; print(pytest.__version__)")
        echo -e "${GREEN}✅ pytest ${PYTEST_VERSION} já instalado${NC}"
        echo ""
        echo -e "${GREEN}🎉 Ambiente pronto para uso!${NC}"
        echo ""
        echo -e "${CYAN}Para executar os testes:${NC}"
        echo -e "  ${YELLOW}./run_cpj_tests.sh all${NC}"
        exit 0
    fi
fi

# Cria virtualenv
echo -e "${CYAN}📦 Criando ambiente virtual Python...${NC}"
python3 -m venv "$VENV_DIR"
echo -e "${GREEN}✅ Virtualenv criado em: ${VENV_DIR}${NC}"
echo ""

# Ativa virtualenv
echo -e "${CYAN}🔌 Ativando ambiente virtual...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✅ Ambiente ativado${NC}"
echo ""

# Atualiza pip
echo -e "${CYAN}⬆️  Atualizando pip...${NC}"
python -m pip install --upgrade pip --quiet
PIP_VERSION=$(pip --version | cut -d' ' -f2)
echo -e "${GREEN}✅ pip ${PIP_VERSION} atualizado${NC}"
echo ""

# Instala dependências do projeto (necessárias para os testes)
echo -e "${CYAN}📚 Instalando dependências do projeto...${NC}"

# Dependências essenciais para testes (sem dependências opcionais)
ESSENTIAL_DEPS=(
    "fastapi==0.104.1"
    "pydantic==2.8.2"
    "pydantic-settings==2.0.3"
    "requests==2.31.0"
    "httpx==0.25.2"
    "pymongo==4.6.0"
)

for dep in "${ESSENTIAL_DEPS[@]}"; do
    package_name=$(echo "$dep" | cut -d'=' -f1)
    echo -e "  📦 Instalando ${package_name}..."
    pip install "$dep" --quiet 2>/dev/null || {
        echo -e "  ${YELLOW}⚠️  Erro ao instalar ${package_name} (continuando)${NC}"
    }
done

echo -e "${GREEN}✅ Dependências essenciais do projeto instaladas${NC}"
echo ""

# Instala dependências de teste
echo -e "${CYAN}📚 Instalando dependências de teste...${NC}"
echo ""

# Lista de dependências
DEPENDENCIES=(
    "pytest==7.4.0"
    "pytest-asyncio==0.21.1"
    "pytest-mock==3.11.1"
    "requests-mock==1.11.0"
    "pytest-cov==4.1.0"
)

for dep in "${DEPENDENCIES[@]}"; do
    package_name=$(echo "$dep" | cut -d'=' -f1)
    echo -e "  📦 Instalando ${package_name}..."
    pip install "$dep" --quiet
    echo -e "  ${GREEN}✅ ${dep}${NC}"
done

echo ""
echo -e "${GREEN}✅ Todas as dependências instaladas${NC}"
echo ""

# Verifica instalação
echo -e "${CYAN}🔍 Verificando instalação...${NC}"

if python -c "import pytest, pytest_asyncio, pytest_mock, requests_mock" 2>/dev/null; then
    PYTEST_VERSION=$(python -c "import pytest; print(pytest.__version__)")
    echo -e "${GREEN}✅ pytest ${PYTEST_VERSION} - OK${NC}"

    ASYNCIO_VERSION=$(python -c "import pytest_asyncio; print(pytest_asyncio.__version__)")
    echo -e "${GREEN}✅ pytest-asyncio ${ASYNCIO_VERSION} - OK${NC}"

    echo -e "${GREEN}✅ pytest-mock - OK${NC}"
    echo -e "${GREEN}✅ requests-mock - OK${NC}"
    echo -e "${GREEN}✅ pytest-cov - OK${NC}"
else
    echo -e "${RED}❌ Erro ao verificar instalação!${NC}"
    deactivate
    exit 1
fi

echo ""

# Salva requirements instalados
echo -e "${CYAN}💾 Salvando requirements.txt...${NC}"
pip freeze > "${SCRIPT_DIR}/requirements-test-installed.txt"
echo -e "${GREEN}✅ Lista salva em: requirements-test-installed.txt${NC}"
echo ""

# Desativa venv
deactivate

# Sucesso
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 Ambiente configurado com sucesso!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${CYAN}📝 Próximos passos:${NC}"
echo ""
echo -e "  1️⃣  Executar todos os testes:"
echo -e "     ${YELLOW}./run_cpj_tests.sh all${NC}"
echo ""
echo -e "  2️⃣  Executar apenas testes unitários:"
echo -e "     ${YELLOW}./run_cpj_tests.sh unit${NC}"
echo ""
echo -e "  3️⃣  Executar com cobertura:"
echo -e "     ${YELLOW}./run_cpj_tests.sh coverage${NC}"
echo ""
echo -e "  4️⃣  Modo debug:"
echo -e "     ${YELLOW}./run_cpj_tests.sh debug${NC}"
echo ""

echo -e "${CYAN}💡 Dica:${NC}"
echo -e "   O ambiente virtual será ativado automaticamente"
echo -e "   quando você executar ${YELLOW}./run_cpj_tests.sh${NC}"
echo ""

echo -e "${CYAN}🔧 Recriar ambiente:${NC}"
echo -e "   ${YELLOW}./setup_test_env.sh --clean${NC}"
echo ""
