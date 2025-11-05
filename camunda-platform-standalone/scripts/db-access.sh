#!/bin/bash
# Script para facilitar acesso ao banco PostgreSQL do Camunda
# Uso: ./db-access.sh [comando]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Carregar configurações
if [ -f "$PROJECT_DIR/.env.production" ]; then
    source "$PROJECT_DIR/.env.production"
fi

# Configurações SSH
VM_USER=${VM_USER:-ubuntu}
VM_HOST=${VM_HOST:-201.23.67.197}
SSH_KEY=${SSH_KEY:-~/.ssh/mac_m2_ssh}

# Configurações do banco
DB_CONTAINER=${DB_CONTAINER:-camunda-platform-db-1}
DB_USER=${POSTGRES_USER:-camunda}
DB_NAME=${POSTGRES_DB:-camunda}

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    cat << EOF
${BLUE}═══════════════════════════════════════════════════════════════${NC}
${GREEN}  Camunda PostgreSQL Database Access Helper${NC}
${BLUE}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}Uso:${NC}
  $0 [comando]

${YELLOW}Comandos disponíveis:${NC}

  ${GREEN}psql${NC}              - Abrir console psql interativo
  ${GREEN}query "SQL"${NC}       - Executar query SQL específica
  ${GREEN}tables${NC}            - Listar todas as tabelas
  ${GREEN}users${NC}             - Listar usuários Camunda
  ${GREEN}processes${NC}         - Listar processos rodando
  ${GREEN}history${NC}           - Últimas 20 instâncias de processo
  ${GREEN}deployments${NC}       - Listar deployments
  ${GREEN}stats${NC}             - Estatísticas do banco
  ${GREEN}size${NC}              - Tamanho das tabelas
  ${GREEN}backup [arquivo]${NC}  - Criar backup do banco
  ${GREEN}restore [arquivo]${NC} - Restaurar backup
  ${GREEN}info${NC}              - Informações de conexão

${YELLOW}Exemplos:${NC}
  $0 psql
  $0 query "SELECT * FROM act_id_user"
  $0 users
  $0 backup camunda-backup-\$(date +%Y%m%d).sql
  $0 stats

${YELLOW}Informações de Conexão:${NC}
  Host: ${VM_HOST}
  Porta: 5432
  Database: ${DB_NAME}
  Usuário: ${DB_USER}
  Container: ${DB_CONTAINER}

EOF
}

# Executar comando no banco via SSH
db_exec() {
    local sql="$1"
    ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no \
        "${VM_USER}@${VM_HOST}" \
        "docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \"${sql}\""
}

# Comando interativo psql
cmd_psql() {
    echo -e "${GREEN}Conectando ao PostgreSQL...${NC}"
    echo -e "${YELLOW}Dica: Use \\q para sair${NC}"
    echo ""
    ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -t \
        "${VM_USER}@${VM_HOST}" \
        "docker exec -it ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}"
}

# Executar query customizada
cmd_query() {
    if [ -z "$1" ]; then
        echo -e "${RED}Erro: SQL query não fornecida${NC}"
        echo "Uso: $0 query \"SELECT * FROM act_id_user\""
        exit 1
    fi
    db_exec "$1"
}

# Listar tabelas
cmd_tables() {
    echo -e "${GREEN}═══ Tabelas do Camunda ═══${NC}"
    db_exec "\dt"
}

# Listar usuários
cmd_users() {
    echo -e "${GREEN}═══ Usuários Camunda ═══${NC}"
    db_exec "SELECT u.id_, u.first_, u.last_, u.email_, string_agg(g.name_, ', ') as groups FROM act_id_user u LEFT JOIN act_id_membership m ON u.id_ = m.user_id_ LEFT JOIN act_id_group g ON m.group_id_ = g.id_ GROUP BY u.id_, u.first_, u.last_, u.email_;"
}

# Processos rodando
cmd_processes() {
    echo -e "${GREEN}═══ Processos em Execução ═══${NC}"
    db_exec "SELECT id_, proc_def_id_, business_key_, suspension_state_, start_time_ FROM act_ru_execution WHERE parent_id_ IS NULL ORDER BY start_time_ DESC LIMIT 20;"
}

# Histórico
cmd_history() {
    echo -e "${GREEN}═══ Últimas 20 Instâncias de Processo ═══${NC}"
    db_exec "SELECT id_, proc_def_key_, business_key_, start_time_, end_time_, state_ FROM act_hi_procinst ORDER BY start_time_ DESC LIMIT 20;"
}

# Deployments
cmd_deployments() {
    echo -e "${GREEN}═══ Deployments ═══${NC}"
    db_exec "SELECT id_, name_, deploy_time_, source_ FROM act_re_deployment ORDER BY deploy_time_ DESC;"
}

# Estatísticas
cmd_stats() {
    echo -e "${GREEN}═══ Estatísticas do Banco ═══${NC}"
    db_exec "SELECT 'Usuários' as tipo, COUNT(*) as total FROM act_id_user UNION ALL SELECT 'Grupos', COUNT(*) FROM act_id_group UNION ALL SELECT 'Deployments', COUNT(*) FROM act_re_deployment UNION ALL SELECT 'Process Definitions', COUNT(*) FROM act_re_procdef UNION ALL SELECT 'Processos Rodando', COUNT(*) FROM act_ru_execution WHERE parent_id_ IS NULL UNION ALL SELECT 'Histórico Total', COUNT(*) FROM act_hi_procinst UNION ALL SELECT 'Incidentes Ativos', COUNT(*) FROM act_ru_incident UNION ALL SELECT 'Jobs Pendentes', COUNT(*) FROM act_ru_job;"
}

# Tamanho das tabelas
cmd_size() {
    echo -e "${GREEN}═══ Tamanho das Tabelas (Top 10) ═══${NC}"
    db_exec "SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"
}

# Backup
cmd_backup() {
    local backup_file="${1:-camunda-backup-$(date +%Y%m%d-%H%M%S).sql}"
    echo -e "${GREEN}Criando backup do banco...${NC}"
    ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no \
        "${VM_USER}@${VM_HOST}" \
        "docker exec ${DB_CONTAINER} pg_dump -U ${DB_USER} ${DB_NAME}" > "$backup_file"
    echo -e "${GREEN}✓ Backup criado: ${backup_file}${NC}"
    echo -e "  Tamanho: $(du -h "$backup_file" | cut -f1)"
}

# Restore
cmd_restore() {
    if [ -z "$1" ] || [ ! -f "$1" ]; then
        echo -e "${RED}Erro: Arquivo de backup não fornecido ou não existe${NC}"
        echo "Uso: $0 restore camunda-backup.sql"
        exit 1
    fi

    echo -e "${YELLOW}⚠️  ATENÇÃO: Isso irá SUBSTITUIR todos os dados do banco!${NC}"
    read -p "Tem certeza? Digite 'RESTORE' para continuar: " confirm

    if [ "$confirm" != "RESTORE" ]; then
        echo -e "${RED}Operação cancelada${NC}"
        exit 0
    fi

    echo -e "${GREEN}Restaurando backup...${NC}"
    cat "$1" | ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no \
        "${VM_USER}@${VM_HOST}" \
        "docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} ${DB_NAME}"
    echo -e "${GREEN}✓ Backup restaurado com sucesso${NC}"
}

# Informações de conexão
cmd_info() {
    cat << EOF
${BLUE}═══════════════════════════════════════════════════════════════${NC}
${GREEN}  Informações de Conexão${NC}
${BLUE}═══════════════════════════════════════════════════════════════${NC}

${YELLOW}Acesso via psql (local):${NC}
  psql -h ${VM_HOST} -p 5432 -U ${DB_USER} -d ${DB_NAME}
  Senha: ${POSTGRES_PASSWORD:-camunda_prod_password_2024}

${YELLOW}Acesso via Docker (na VM):${NC}
  ssh ${VM_USER}@${VM_HOST}
  docker exec -it ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}

${YELLOW}Connection String:${NC}
  postgresql://${DB_USER}:****@${VM_HOST}:5432/${DB_NAME}

${YELLOW}DBeaver/pgAdmin:${NC}
  Host: ${VM_HOST}
  Port: 5432
  Database: ${DB_NAME}
  Username: ${DB_USER}
  Password: ${POSTGRES_PASSWORD:-camunda_prod_password_2024}
  SSL Mode: prefer

EOF
}

# Main
case "${1:-help}" in
    psql)
        cmd_psql
        ;;
    query)
        shift
        cmd_query "$@"
        ;;
    tables)
        cmd_tables
        ;;
    users)
        cmd_users
        ;;
    processes)
        cmd_processes
        ;;
    history)
        cmd_history
        ;;
    deployments)
        cmd_deployments
        ;;
    stats)
        cmd_stats
        ;;
    size)
        cmd_size
        ;;
    backup)
        shift
        cmd_backup "$@"
        ;;
    restore)
        shift
        cmd_restore "$@"
        ;;
    info)
        cmd_info
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Comando desconhecido: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
