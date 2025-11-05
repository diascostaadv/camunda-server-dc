#!/bin/bash
# ============================================================================
# Script de Aplicação de Migração - Colunas TEXT_
# ============================================================================
# Executa a migração de VARCHAR(4000) → TEXT nas colunas TEXT_ do Camunda
# com backup automático, validações e logs detalhados.
#
# Uso:
#   ./apply-migration.sh [opções]
#
# Opções:
#   --dry-run          Simula execução sem alterar dados
#   --skip-backup      Pula criação de backup (NÃO RECOMENDADO)
#   --rollback         Executa rollback da migração
#   --help             Mostra esta ajuda
#
# ============================================================================

set -e  # Exit on error

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MIGRATION_NAME="text-column-migration"
MIGRATION_VERSION="001"

# Arquivos SQL
SQL_UPGRADE="${SCRIPT_DIR}/migrate-text-column-upgrade.sql"
SQL_ROLLBACK="${SCRIPT_DIR}/migrate-text-column-rollback.sql"

# Diretório de backups e logs
BACKUP_DIR="${SCRIPT_DIR}/backups"
LOG_DIR="${SCRIPT_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/camunda-backup-before-${MIGRATION_NAME}-${TIMESTAMP}.sql"
LOG_FILE="${LOG_DIR}/migration-${MIGRATION_NAME}-${TIMESTAMP}.log"

# Configurações do banco (carregar de .env se existir)
if [ -f "${PROJECT_DIR}/.env.production" ]; then
    source "${PROJECT_DIR}/.env.production"
fi

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${POSTGRES_DB:-camunda}
DB_USER=${POSTGRES_USER:-camunda}
DB_PASSWORD=${POSTGRES_PASSWORD:-camunda_prod_password_2024}

# SSH para acesso remoto (se necessário)
VM_USER=${VM_USER:-ubuntu}
VM_HOST=${VM_HOST:-201.23.67.197}
SSH_KEY=${SSH_KEY:-~/.ssh/mac_m2_ssh}
DB_CONTAINER=${DB_CONTAINER:-camunda-platform-db-1}

# Opções
DRY_RUN=false
SKIP_BACKUP=false
ROLLBACK=false

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $@" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $@" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $@" | tee -a "$LOG_FILE"
}

show_header() {
    echo ""
    echo "=========================================================================="
    echo "$@"
    echo "=========================================================================="
    echo ""
}

show_help() {
    cat << EOF
${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}
${GREEN}  Migração de Banco - Colunas TEXT_ (VARCHAR → TEXT)${NC}
${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}

${YELLOW}DESCRIÇÃO:${NC}
  Altera o tipo da coluna TEXT_ de VARCHAR(4000) para TEXT em 3 tabelas do
  Camunda BPM, permitindo armazenar textos maiores que 4000 caracteres.

${YELLOW}USO:${NC}
  $0 [opções]

${YELLOW}OPÇÕES:${NC}
  ${GREEN}--dry-run${NC}         Simula execução sem alterar dados
  ${GREEN}--skip-backup${NC}     Pula criação de backup (NÃO RECOMENDADO)
  ${GREEN}--rollback${NC}        Executa rollback da migração
  ${GREEN}--help${NC}            Mostra esta ajuda

${YELLOW}EXEMPLOS:${NC}
  # Simular migração (recomendado primeiro)
  $0 --dry-run

  # Executar migração com backup automático
  $0

  # Executar rollback
  $0 --rollback

${YELLOW}ARQUIVOS:${NC}
  Upgrade:  ${SQL_UPGRADE}
  Rollback: ${SQL_ROLLBACK}
  Backup:   ${BACKUP_DIR}/
  Logs:     ${LOG_DIR}/

${YELLOW}IMPORTANTE:${NC}
  - Backup é criado automaticamente antes da execução
  - Logs detalhados são salvos em ${LOG_DIR}/
  - Rollback está disponível em caso de problemas
  - Tempo estimado: 2-5 segundos

EOF
}

# ============================================================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================================================

check_prerequisites() {
    log_info "Verificando pré-requisitos..."

    # Verificar se os arquivos SQL existem
    if [ ! -f "$SQL_UPGRADE" ]; then
        log_error "Arquivo de migração não encontrado: $SQL_UPGRADE"
        exit 1
    fi

    if [ ! -f "$SQL_ROLLBACK" ]; then
        log_error "Arquivo de rollback não encontrado: $SQL_ROLLBACK"
        exit 1
    fi

    # Criar diretórios se não existirem
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"

    log_success "Pré-requisitos OK"
}

test_db_connection() {
    log_info "Testando conexão com banco de dados..."

    # Tentar via Docker remoto primeiro
    if ssh -i "${SSH_KEY}" -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "${VM_USER}@${VM_HOST}" "docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c 'SELECT 1' > /dev/null 2>&1"; then
        log_success "Conexão OK (via Docker remoto)"
        DB_ACCESS_METHOD="remote_docker"
        return 0
    fi

    # Tentar via psql local
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
        log_success "Conexão OK (via psql local)"
        DB_ACCESS_METHOD="local_psql"
        return 0
    fi

    log_error "Não foi possível conectar ao banco de dados"
    log_error "Host: $DB_HOST:$DB_PORT | Database: $DB_NAME | User: $DB_USER"
    exit 1
}

# ============================================================================
# FUNÇÕES DE BACKUP
# ============================================================================

create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "Backup pulado (--skip-backup)"
        return 0
    fi

    show_header "CRIANDO BACKUP DO BANCO"

    log_info "Criando backup em: $BACKUP_FILE"

    if [ "$DB_ACCESS_METHOD" = "remote_docker" ]; then
        ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${VM_USER}@${VM_HOST}" \
            "docker exec ${DB_CONTAINER} pg_dump -U ${DB_USER} ${DB_NAME}" > "$BACKUP_FILE"
    else
        PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
    fi

    if [ $? -eq 0 ]; then
        local size=$(du -h "$BACKUP_FILE" | cut -f1)
        log_success "Backup criado com sucesso (${size})"
    else
        log_error "Falha ao criar backup"
        exit 1
    fi
}

# ============================================================================
# FUNÇÕES DE EXECUÇÃO
# ============================================================================

execute_sql() {
    local sql_file="$1"
    local description="$2"

    log_info "Executando: $description"

    if [ "$DB_ACCESS_METHOD" = "remote_docker" ]; then
        cat "$sql_file" | ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${VM_USER}@${VM_HOST}" \
            "docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}"
    else
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$sql_file"
    fi

    if [ $? -eq 0 ]; then
        log_success "$description executado com sucesso"
        return 0
    else
        log_error "Falha ao executar $description"
        return 1
    fi
}

run_upgrade() {
    show_header "EXECUTANDO MIGRAÇÃO (UPGRADE)"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN - Simulando execução..."
        log_info "SQL que seria executado: $SQL_UPGRADE"
        log_info "Backup que seria criado: $BACKUP_FILE"
        return 0
    fi

    execute_sql "$SQL_UPGRADE" "Migração de upgrade"
    local result=$?

    if [ $result -eq 0 ]; then
        log_success "✓ Migração concluída com sucesso!"
        log_info "Backup disponível em: $BACKUP_FILE"
        log_info "Para reverter, execute: $0 --rollback"
    else
        log_error "✗ Migração falhou!"
        log_error "Verifique os logs em: $LOG_FILE"
        log_info "Para restaurar backup: psql -U $DB_USER -d $DB_NAME < $BACKUP_FILE"
        exit 1
    fi
}

run_rollback() {
    show_header "EXECUTANDO ROLLBACK"

    log_warning "ATENÇÃO: Isso reverterá a migração!"

    read -p "Tem certeza que deseja continuar? (digite 'ROLLBACK' para confirmar): " confirm

    if [ "$confirm" != "ROLLBACK" ]; then
        log_info "Rollback cancelado"
        exit 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN - Simulando rollback..."
        log_info "SQL que seria executado: $SQL_ROLLBACK"
        return 0
    fi

    execute_sql "$SQL_ROLLBACK" "Rollback da migração"
    local result=$?

    if [ $result -eq 0 ]; then
        log_success "✓ Rollback concluído com sucesso!"
    else
        log_error "✗ Rollback falhou!"
        log_error "Verifique os logs em: $LOG_FILE"
        exit 1
    fi
}

# ============================================================================
# PARSE ARGUMENTOS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Opção desconhecida: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
done

# ============================================================================
# MAIN
# ============================================================================

main() {
    show_header "MIGRAÇÃO: Colunas TEXT_ - VARCHAR(4000) → TEXT"

    log_info "Iniciando processo de migração..."
    log_info "Timestamp: $TIMESTAMP"
    log_info "Log file: $LOG_FILE"

    # 1. Verificações
    check_prerequisites
    test_db_connection

    # 2. Informações
    log_info "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info "Método de acesso: $DB_ACCESS_METHOD"
    log_info "Dry run: $DRY_RUN"
    log_info "Skip backup: $SKIP_BACKUP"

    # 3. Executar operação apropriada
    if [ "$ROLLBACK" = true ]; then
        run_rollback
    else
        create_backup
        run_upgrade
    fi

    show_header "PROCESSO CONCLUÍDO"
    log_success "Tudo pronto!"
    log_info "Logs completos em: $LOG_FILE"
}

# Executar
main
