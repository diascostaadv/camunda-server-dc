#!/bin/bash

# Script para build e execução do Worker Unificado de Publicações
# Autor: Dias Costa
# Data: Dezembro 2023

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Função de ajuda
show_help() {
    cat << EOF
Worker Unificado de Publicações - Build & Deploy Script

USAGE:
    ./build-and-run.sh [COMMAND] [OPTIONS]

COMMANDS:
    build       Constrói a imagem Docker
    run         Executa o worker com docker-compose
    stop        Para o worker
    restart     Reinicia o worker
    logs        Mostra logs do worker
    clean       Remove containers e imagens
    test        Testa conectividade e configuração
    help        Mostra esta ajuda

OPTIONS:
    -d, --detach    Executa em background (apenas para 'run')
    -f, --follow    Segue logs em tempo real (apenas para 'logs')
    --rebuild       Force rebuild da imagem (apenas para 'run')

EXAMPLES:
    ./build-and-run.sh build
    ./build-and-run.sh run -d
    ./build-and-run.sh logs -f
    ./build-and-run.sh restart
    ./build-and-run.sh clean

EOF
}

# Função para verificar dependências
check_dependencies() {
    log_info "Verificando dependências..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose não está instalado!"
        exit 1
    fi
    
    log_info "✅ Dependências OK"
}

# Função para build da imagem
build_image() {
    log_info "🔨 Construindo imagem Docker..."
    
    # Copiar arquivos comuns necessários
    if [ ! -d "../common" ]; then
        log_error "Diretório ../common não encontrado!"
        exit 1
    fi
    
    # Build da imagem
    docker build -t publicacao-unified-worker:latest .
    
    if [ $? -eq 0 ]; then
        log_info "✅ Imagem construída com sucesso!"
    else
        log_error "❌ Falha na construção da imagem!"
        exit 1
    fi
}

# Função para executar o worker
run_worker() {
    local detach_flag=""
    local rebuild_flag=""
    
    # Processar argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--detach)
                detach_flag="-d"
                shift
                ;;
            --rebuild)
                rebuild_flag="--build"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "🚀 Iniciando Worker Unificado de Publicações..."
    
    # Verificar se a rede existe
    if ! docker network ls | grep -q "camunda-network"; then
        log_warn "Rede camunda-network não encontrada. Criando..."
        docker network create camunda-network
    fi
    
    # Executar com docker-compose
    docker-compose up $detach_flag $rebuild_flag
    
    if [ $? -eq 0 ]; then
        log_info "✅ Worker iniciado com sucesso!"
        if [ -n "$detach_flag" ]; then
            log_info "📊 Métricas disponíveis em: http://localhost:8002/metrics"
            log_info "🏥 Health check em: http://localhost:8002/health"
            log_info "📋 Para ver logs: ./build-and-run.sh logs -f"
        fi
    else
        log_error "❌ Falha ao iniciar worker!"
        exit 1
    fi
}

# Função para parar o worker
stop_worker() {
    log_info "⏹️ Parando Worker Unificado de Publicações..."
    docker-compose down
    log_info "✅ Worker parado!"
}

# Função para reiniciar o worker
restart_worker() {
    log_info "🔄 Reiniciando Worker Unificado de Publicações..."
    docker-compose down
    docker-compose up -d
    log_info "✅ Worker reiniciado!"
}

# Função para mostrar logs
show_logs() {
    local follow_flag=""
    
    # Processar argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--follow)
                follow_flag="-f"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "📋 Mostrando logs do worker..."
    docker-compose logs $follow_flag publicacao-unified-worker
}

# Função para limpeza
clean_worker() {
    log_warn "🧹 Limpando containers e imagens..."
    
    # Parar e remover containers
    docker-compose down --volumes --remove-orphans
    
    # Remover imagem
    docker rmi publicacao-unified-worker:latest 2>/dev/null || true
    
    log_info "✅ Limpeza concluída!"
}

# Função para testes
test_worker() {
    log_info "🧪 Testando Worker Unificado de Publicações..."
    
    # Verificar se o container está rodando
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Worker não está executando! Execute: ./build-and-run.sh run -d"
        exit 1
    fi
    
    # Testar health check
    log_info "Testando health check..."
    if curl -f http://localhost:8002/health &>/dev/null; then
        log_info "✅ Health check OK"
    else
        log_error "❌ Health check falhou"
    fi
    
    # Testar métricas
    log_info "Testando métricas Prometheus..."
    if curl -f http://localhost:8002/metrics &>/dev/null; then
        log_info "✅ Métricas OK"
    else
        log_error "❌ Métricas indisponíveis"
    fi
    
    # Mostrar informações do container
    log_info "Informações do container:"
    docker-compose ps
    
    log_info "🎉 Testes concluídos!"
}

# Função principal
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    local command="$1"
    shift
    
    check_dependencies
    
    case $command in
        build)
            build_image
            ;;
        run)
            run_worker "$@"
            ;;
        stop)
            stop_worker
            ;;
        restart)
            restart_worker
            ;;
        logs)
            show_logs "$@"
            ;;
        clean)
            clean_worker
            ;;
        test)
            test_worker
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Comando desconhecido: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Executar função principal
main "$@"