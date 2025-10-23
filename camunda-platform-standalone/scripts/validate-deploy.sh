#!/bin/bash
"""
Script de validação para deploy do Camunda Platform
Verifica todos os requisitos antes do deploy
"""

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para logging
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Contador de erros
ERRORS=0

# Função para verificar se comando existe
check_command() {
    if command -v "$1" &> /dev/null; then
        success "$1 está disponível"
        return 0
    else
        error "$1 não encontrado"
        ((ERRORS++))
        return 1
    fi
}

# Função para verificar versão
check_version() {
    local cmd="$1"
    local min_version="$2"
    local current_version
    
    if command -v "$cmd" &> /dev/null; then
        current_version=$($cmd --version 2>&1 | head -n1)
        log "Versão atual do $cmd: $current_version"
        
        # Verificar se contém a versão mínima
        if [[ "$current_version" == *"$min_version"* ]]; then
            success "$cmd versão compatível"
            return 0
        else
            warning "$cmd pode ter versão incompatível (esperado: $min_version)"
            return 1
        fi
    else
        error "$cmd não encontrado"
        ((ERRORS++))
        return 1
    fi
}

# Função para verificar arquivo
check_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        success "$description encontrado: $file"
        return 0
    else
        error "$description não encontrado: $file"
        ((ERRORS++))
        return 1
    fi
}

# Função para verificar sintaxe docker-compose
check_compose_syntax() {
    local file="$1"
    
    if [ -f "$file" ]; then
        log "Verificando sintaxe do $file..."
        if docker-compose -f "$file" config > /dev/null 2>&1; then
            success "Sintaxe do $file está correta"
            return 0
        else
            error "Sintaxe do $file está incorreta"
            ((ERRORS++))
            return 1
        fi
    else
        error "Arquivo $file não encontrado"
        ((ERRORS++))
        return 1
    fi
}

# Função para verificar variáveis de ambiente
check_env_vars() {
    local env_file="$1"
    
    if [ -f "$env_file" ]; then
        log "Verificando variáveis de ambiente em $env_file..."
        
        # Verificar variáveis críticas
        local required_vars=("DATABASE_URL" "POSTGRES_USER" "POSTGRES_PASSWORD")
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" "$env_file"; then
                missing_vars+=("$var")
            fi
        done
        
        if [ ${#missing_vars[@]} -eq 0 ]; then
            success "Todas as variáveis de ambiente críticas estão definidas"
            return 0
        else
            error "Variáveis de ambiente faltando: ${missing_vars[*]}"
            ((ERRORS++))
            return 1
        fi
    else
        warning "Arquivo de ambiente $env_file não encontrado"
        return 1
    fi
}

# Função para verificar portas
check_ports() {
    local ports=("8080" "5432" "9090" "3001")
    local occupied_ports=()
    
    log "Verificando portas disponíveis..."
    
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            occupied_ports+=("$port")
        fi
    done
    
    if [ ${#occupied_ports[@]} -eq 0 ]; then
        success "Todas as portas necessárias estão disponíveis"
        return 0
    else
        warning "Portas ocupadas: ${occupied_ports[*]}"
        return 1
    fi
}

# Função para verificar recursos do sistema
check_system_resources() {
    log "Verificando recursos do sistema..."
    
    # Verificar memória
    local total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ "$total_mem" -lt 4096 ]; then
        warning "Memória insuficiente: ${total_mem}MB (mínimo: 4GB)"
    else
        success "Memória suficiente: ${total_mem}MB"
    fi
    
    # Verificar espaço em disco
    local disk_usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        warning "Espaço em disco baixo: ${disk_usage}% usado"
    else
        success "Espaço em disco OK: ${disk_usage}% usado"
    fi
}

# Função principal
main() {
    echo "🔍 Validando requisitos para deploy do Camunda Platform..."
    echo "=================================================="
    
    # Verificar comandos necessários
    log "Verificando comandos necessários..."
    check_command "docker"
    check_command "docker-compose"
    
    # Verificar versões
    log "Verificando versões..."
    check_version "docker-compose" "1.26"
    
    # Verificar arquivos de configuração
    log "Verificando arquivos de configuração..."
    check_file "docker-compose.yml" "Docker Compose local"
    check_file "docker-compose.swarm.yml" "Docker Compose Swarm"
    check_file ".env.production" "Arquivo de ambiente produção"
    
    # Verificar sintaxe dos arquivos
    log "Verificando sintaxe dos arquivos Docker Compose..."
    check_compose_syntax "docker-compose.yml"
    check_compose_syntax "docker-compose.swarm.yml"
    
    # Verificar variáveis de ambiente
    log "Verificando variáveis de ambiente..."
    check_env_vars ".env.production"
    
    # Verificar portas
    check_ports
    
    # Verificar recursos do sistema
    check_system_resources
    
    # Verificar se Docker está rodando
    log "Verificando se Docker está rodando..."
    if docker info > /dev/null 2>&1; then
        success "Docker está rodando"
    else
        error "Docker não está rodando"
        ((ERRORS++))
    fi
    
    # Verificar se Docker Swarm está ativo (se aplicável)
    if [ "$1" = "swarm" ]; then
        log "Verificando Docker Swarm..."
        if docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
            success "Docker Swarm está ativo"
        else
            warning "Docker Swarm não está ativo"
        fi
    fi
    
    echo "=================================================="
    
    # Resultado final
    if [ $ERRORS -eq 0 ]; then
        success "✅ Todas as verificações passaram! Deploy pode prosseguir."
        exit 0
    else
        error "❌ $ERRORS erro(es) encontrado(s). Corrija antes do deploy."
        exit 1
    fi
}

# Verificar argumentos
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Uso: $0 [swarm]"
    echo ""
    echo "Argumentos:"
    echo "  swarm    - Inclui verificação do Docker Swarm"
    echo "  --help   - Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0           # Verificação básica"
    echo "  $0 swarm     # Verificação com Docker Swarm"
    exit 0
fi

# Executar validação
main "$1"
