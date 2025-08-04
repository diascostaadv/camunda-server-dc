#!/bin/bash
# -*- coding: utf-8 -*-
"""
Script de setup para ambiente de testes
Instala dependências, configura ambiente e executa verificações iniciais
"""

set -e  # Parar em caso de erro

echo "🔧 SETUP DO AMBIENTE DE TESTES"
echo "=" * 50

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Verificar Python
print_status "Verificando instalação do Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python encontrado: $PYTHON_VERSION"
else
    print_error "Python3 não está instalado!"
    exit 1
fi

# 2. Verificar pip
print_status "Verificando pip..."
if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
    print_success "pip encontrado"
else
    print_error "pip não está instalado!"
    exit 1
fi

# 3. Criar ambiente virtual (opcional)
if [ "$1" = "--venv" ]; then
    print_status "Criando ambiente virtual..."
    python3 -m venv venv
    source venv/bin/activate
    print_success "Ambiente virtual criado e ativado"
fi

# 4. Instalar dependências
print_status "Instalando dependências de teste..."
if [ -f "requirements-test.txt" ]; then
    pip install -r requirements-test.txt
    print_success "Dependências de teste instaladas"
else
    print_warning "Arquivo requirements-test.txt não encontrado"
fi

# 5. Instalar dependências do projeto
print_status "Verificando dependências do projeto..."
if [ -f "camunda-swarm/workers/requirements.txt" ]; then
    pip install -r camunda-swarm/workers/requirements.txt
    print_success "Dependências do projeto instaladas"
else
    print_warning "requirements.txt do projeto não encontrado"
fi

# 6. Criar diretórios necessários
print_status "Criando diretórios de trabalho..."
mkdir -p reports/htmlcov
mkdir -p tests/data
mkdir -p logs
print_success "Diretórios criados"

# 7. Verificar conectividade com Camunda (opcional)
print_status "Verificando conectividade com Camunda..."
CAMUNDA_URL=${CAMUNDA_URL:-"http://localhost:8080"}

if curl -s --connect-timeout 5 "$CAMUNDA_URL/camunda/engine-rest/version" > /dev/null; then
    print_success "Camunda está acessível em $CAMUNDA_URL"
else
    print_warning "Camunda não está acessível em $CAMUNDA_URL"
    print_warning "Testes de integração serão pulados automaticamente"
fi

# 8. Verificar worker (opcional)
print_status "Verificando worker..."
WORKER_PORT=${WORKER_PORT:-"8001"}

if curl -s --connect-timeout 5 "http://localhost:$WORKER_PORT/health" > /dev/null; then
    print_success "Worker está acessível na porta $WORKER_PORT"
else
    print_warning "Worker não está acessível na porta $WORKER_PORT"
    print_warning "Testes de worker serão pulados automaticamente"
fi

# 9. Executar teste básico
print_status "Executando teste básico de configuração..."
python3 -c "
import sys
print(f'Python: {sys.version}')

try:
    import pytest
    print(f'pytest: {pytest.__version__}')
except ImportError:
    print('pytest não está disponível')
    sys.exit(1)

try:
    import requests
    print(f'requests: {requests.__version__}')
except ImportError:
    print('requests não está disponível')
    sys.exit(1)

print('✅ Configuração básica OK')
"

if [ $? -eq 0 ]; then
    print_success "Teste básico passou"
else
    print_error "Teste básico falhou!"
    exit 1
fi

echo ""
echo "🎉 SETUP COMPLETO!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "  1. Execute testes unitários:       python run_tests.py unit"
echo "  2. Execute testes de integração:   python run_tests.py integration"
echo "  3. Execute todos os testes:        python run_tests.py all"
echo "  4. Execute teste específico:       python run_tests.py -m smoke"
echo ""
echo "📊 RELATÓRIOS:"
echo "  - HTML: reports/test_report.html"
echo "  - Cobertura: reports/htmlcov/index.html"
echo ""

# 10. Verificar se pytest funciona
print_status "Testando pytest..."
if python3 -m pytest --version > /dev/null 2>&1; then
    print_success "pytest está funcionando corretamente"
else
    print_error "Erro ao executar pytest"
    exit 1
fi

print_success "Ambiente de testes configurado e pronto para uso!"
