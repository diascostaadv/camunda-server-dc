# Guia de Otimização: Azure PostgreSQL para Camunda BPM

## Contexto

Este documento detalha estratégias para otimizar a latência ao usar Azure Database for PostgreSQL com Camunda BPM, baseado na análise do problema de conectividade detectado em produção.

## Problema Identificado

**Sintomas:**
- Latência extrema reportada pelos usuários
- 100% packet loss ao pingar Azure PostgreSQL endpoint
- Timeout em conexões de banco de dados

**Diagnóstico realizado:**
```bash
# Teste de conectividade falhou
ping -c 5 camunda-dc-db.postgres.database.azure.com
# Resultado: 100% packet loss
```

## Estratégias de Otimização

### 1. Configuração de Rede e Firewall Azure

#### 1.1 Verificar Regras de Firewall

**Problema comum:** IP da VM não está na allowlist do Azure Database.

**Solução:**
```bash
# 1. Verificar IP público da VM
curl -s ifconfig.me

# 2. No Azure Portal:
Azure Database for PostgreSQL > Networking > Firewall rules
- Adicionar IP público da VM: 201.23.67.197
- OU: Permitir acesso de serviços Azure (se VM estiver na mesma região)
```

#### 1.2 Configurar Virtual Network (VNet)

**Melhor prática:** Usar VNet Service Endpoints ou Private Link para conectividade segura e de baixa latência.

```bash
# Azure CLI - Criar service endpoint
az postgres flexible-server vnet-rule create \
  --resource-group <resource-group> \
  --server-name camunda-dc-db \
  --name camunda-vm-rule \
  --vnet-name <vnet-name> \
  --subnet <subnet-name>
```

**Benefícios:**
- ✅ Latência reduzida (tráfego não sai da rede Azure)
- ✅ Maior segurança (sem exposição à internet pública)
- ✅ Sem custos adicionais de tráfego

#### 1.3 Usar Azure Private Link

**Para produção crítica:**
```bash
# Criar private endpoint
az network private-endpoint create \
  --name camunda-db-private-endpoint \
  --resource-group <resource-group> \
  --vnet-name <vnet-name> \
  --subnet <subnet-name> \
  --private-connection-resource-id <db-resource-id> \
  --group-id postgresqlServer \
  --connection-name camunda-db-connection
```

**Vantagens:**
- Latência mínima (~1-5ms dentro da mesma região)
- IP privado dedicado
- Tráfego nunca deixa a rede Microsoft

---

### 2. Otimização do Connection Pool (HikariCP)

#### 2.1 Configuração para Azure PostgreSQL

```bash
# .env.production - Configuração otimizada para Azure

# Connection timeout: Reduzir para detectar problemas mais rápido
DB_CONNECTION_TIMEOUT=20000  # 20s (Azure tem limit de 30s)

# Idle timeout: Azure fecha conexões idle após 10min
DB_IDLE_TIMEOUT=300000  # 5 min (antes do timeout do Azure)

# Max lifetime: Reciclar conexões periodicamente
DB_MAX_LIFETIME=600000  # 10 min (prevenir timeout do Azure)

# Pool size: Ajustar conforme tier do Azure Database
DB_MAXIMUM_POOL_SIZE=10  # Azure Basic: 50, General Purpose: 100+
DB_MINIMUM_IDLE=3  # Manter conexões warm

# Keepalive: CRÍTICO para Azure
DB_KEEPALIVE_TIME=120000  # 2 min - envia keepalive antes do idle timeout

# Validation: Verificar saúde das conexões
DB_VALIDATION_TIMEOUT=3000
DB_VALIDATE_ON_BORROW=true

# Leak detection: Debug em dev
DB_LEAK_DETECTION_THRESHOLD=30000  # 30s - alertar sobre leaks
```

#### 2.2 JDBC URL Otimizada para Azure

```bash
# URL com parâmetros de performance
DATABASE_URL=jdbc:postgresql://camunda-dc-db.postgres.database.azure.com:5432/postgres?sslmode=require&tcpKeepAlive=true&socketTimeout=30&connectTimeout=10&loginTimeout=10&ApplicationName=Camunda-BPM

# Parâmetros explicados:
# - sslmode=require: SSL obrigatório (Azure requirement)
# - tcpKeepAlive=true: Keepalive no nível TCP
# - socketTimeout=30: Timeout de socket (30s)
# - connectTimeout=10: Timeout de conexão inicial (10s)
# - loginTimeout=10: Timeout de autenticação (10s)
# - ApplicationName: Identificar conexões no Azure
```

---

### 3. Otimização de Performance do PostgreSQL Azure

#### 3.1 Escolher Tier Adequado

**Azure Database for PostgreSQL - Tiers:**

| Tier | vCores | RAM | IOPS | Latência | Custo |
|------|--------|-----|------|----------|-------|
| Basic | 1-2 | 2-4GB | Limitado | Alta | $ |
| General Purpose | 2-64 | 10-432GB | 3 IOPS/GB | Média | $$ |
| Memory Optimized | 2-32 | 20-864GB | 3 IOPS/GB | Baixa | $$$ |

**Recomendação para Camunda:**
- Produção: **General Purpose** (mínimo 4 vCores, 16GB RAM)
- Dev/QA: Basic (2 vCores, 4GB RAM)

#### 3.2 Configurações PostgreSQL para Camunda

```sql
-- Conectar ao Azure Database
psql "host=camunda-dc-db.postgres.database.azure.com port=5432 dbname=postgres user=root_camunda sslmode=require"

-- Otimizações recomendadas
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '4GB';  -- 25% da RAM
ALTER SYSTEM SET effective_cache_size = '12GB';  -- 75% da RAM
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;  -- SSD
ALTER SYSTEM SET effective_io_concurrency = 200;  -- SSD
ALTER SYSTEM SET work_mem = '10MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Aplicar mudanças (requer restart via Azure Portal)
SELECT pg_reload_conf();
```

#### 3.3 Índices Específicos para Camunda

```sql
-- Melhorar performance de queries Camunda
CREATE INDEX CONCURRENTLY idx_act_ru_task_assignee ON act_ru_task(assignee_);
CREATE INDEX CONCURRENTLY idx_act_ru_task_owner ON act_ru_task(owner_);
CREATE INDEX CONCURRENTLY idx_act_hi_procinst_end ON act_hi_procinst(end_time_);
CREATE INDEX CONCURRENTLY idx_act_hi_procinst_business ON act_hi_procinst(business_key_);
CREATE INDEX CONCURRENTLY idx_act_hi_actinst_end ON act_hi_actinst(end_time_);

-- Monitorar índices não utilizados
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;
```

---

### 4. Monitoramento e Diagnóstico

#### 4.1 Monitorar Latência de Rede

```bash
# Script de monitoramento contínuo
#!/bin/bash
# monitor-azure-db-latency.sh

DB_HOST="camunda-dc-db.postgres.database.azure.com"
LOG_FILE="/var/log/azure-db-latency.log"

while true; do
    # Ping test
    PING_TIME=$(ping -c 1 $DB_HOST | grep 'time=' | awk -F'time=' '{print $2}' | awk '{print $1}')

    # Connection test
    CONN_TIME=$(time psql "host=$DB_HOST port=5432 user=root_camunda sslmode=require" -c "SELECT 1" 2>&1 | grep real | awk '{print $2}')

    echo "$(date) | Ping: ${PING_TIME}ms | Connect: ${CONN_TIME}" >> $LOG_FILE

    sleep 60
done
```

#### 4.2 Azure Metrics para PostgreSQL

**Métricas críticas no Azure Portal:**

```bash
# Via Azure CLI
az monitor metrics list \
  --resource "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.DBforPostgreSQL/flexibleServers/camunda-dc-db" \
  --metric-names \
    "cpu_percent" \
    "memory_percent" \
    "storage_percent" \
    "active_connections" \
    "network_bytes_ingress" \
    "network_bytes_egress" \
    "io_consumption_percent" \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

**Alertas recomendados:**
- CPU > 80% por 5 minutos
- Conexões ativas > 80% do máximo
- Storage > 85%
- Latência de queries > 1000ms

#### 4.3 Query Performance Insights

```sql
-- Queries mais lentas
SELECT
    queryid,
    calls,
    mean_exec_time,
    max_exec_time,
    stddev_exec_time,
    query
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Conexões ativas por estado
SELECT
    state,
    COUNT(*),
    AVG(EXTRACT(EPOCH FROM (now() - query_start))) as avg_duration
FROM pg_stat_activity
WHERE state IS NOT NULL
GROUP BY state;

-- Bloqueios
SELECT
    pid,
    usename,
    pg_blocking_pids(pid) as blocked_by,
    query as blocked_query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

---

### 5. Estratégias de Cache

#### 5.1 Cache de Read-Through (Redis)

**Arquitetura:**
```
Camunda → Redis Cache → Azure PostgreSQL
            ↓ (miss)
        Azure PostgreSQL
```

**Implementação:**

```yaml
# docker-compose.yml - Adicionar Redis
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru

volumes:
  redis_data:
```

**Configuração Camunda + Redis:**

```java
// CamundaProcessEngineConfiguration.java
@Bean
public ProcessEngineConfiguration processEngineConfiguration() {
    SpringProcessEngineConfiguration config = new SpringProcessEngineConfiguration();

    // Habilitar cache L2 (opcional)
    config.setDatabaseSchemaUpdate("true");
    config.setDeploymentCache(new DeploymentCache(1000)); // 1000 deployments
    config.setProcessDefinitionCache(new ProcessDefinitionCache(1000));

    return config;
}
```

#### 5.2 Connection Pooling Avançado com PgBouncer

**PgBouncer como proxy:**
```
Camunda → PgBouncer (local) → Azure PostgreSQL
```

```bash
# docker-compose.yml
services:
  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      DB_HOST: camunda-dc-db.postgres.database.azure.com
      DB_PORT: 5432
      DB_USER: root_camunda
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_NAME: postgres
      POOL_MODE: transaction  # session, transaction, statement
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 25
      SERVER_IDLE_TIMEOUT: 300
    ports:
      - "6432:5432"
```

**Camunda conecta ao PgBouncer:**
```bash
DATABASE_URL=jdbc:postgresql://pgbouncer:5432/postgres?sslmode=disable
```

**Benefícios:**
- ✅ Reduz overhead de criação de conexões
- ✅ Pool compartilhado entre múltiplas instâncias Camunda
- ✅ Menor latência (conexões warm)

---

### 6. Plano de Migração Gradual

#### Fase 1: Diagnóstico (1 dia)

```bash
# Checklist
☐ Verificar firewall rules no Azure
☐ Confirmar IP da VM está na allowlist
☐ Testar conectividade: ping, telnet, psql
☐ Coletar métricas Azure (CPU, conexões, latência)
☐ Revisar logs de erro do Camunda
```

#### Fase 2: Quick Wins (2-3 dias)

```bash
☐ Adicionar IP da VM ao firewall Azure
☐ Otimizar connection pool (HikariCP)
☐ Configurar keepalive TCP
☐ Ajustar timeout parameters
☐ Testar e medir melhorias
```

#### Fase 3: Infraestrutura (1 semana)

```bash
☐ Criar VNet Service Endpoint
☐ Mover VM para mesma região do banco
☐ Configurar Private Link (opcional)
☐ Implementar PgBouncer
☐ Testes de carga
```

#### Fase 4: Performance Tuning (1 semana)

```bash
☐ Otimizar PostgreSQL parameters
☐ Criar índices específicos
☐ Implementar Redis cache
☐ Tuning JVM (Camunda)
☐ Benchmark final
```

---

### 7. Configuração Completa Recomendada

#### 7.1 Arquivo .env.production (Azure optimized)

```bash
# Camunda Platform - Production Environment (Azure Database)
ENVIRONMENT=production

# Network Configuration
NETWORK_DRIVER=bridge

# Database Mode Configuration
EXTERNAL_DATABASE_MODE=true

# PostgreSQL Configuration - Azure Database for PostgreSQL
POSTGRES_DB=camunda  # Criar database 'camunda' no Azure
POSTGRES_USER=camunda_admin@camunda-dc-db
POSTGRES_PASSWORD=<strong-password>
POSTGRES_PORT=5432

# Database Connection (URI-based) - Azure Database for PostgreSQL
# IMPORTANTE: Usar VNet endpoint se possível
DATABASE_URL=jdbc:postgresql://camunda-dc-db.postgres.database.azure.com:5432/camunda?sslmode=require&tcpKeepAlive=true&socketTimeout=30&connectTimeout=10&loginTimeout=10&ApplicationName=Camunda-Production

# Camunda Configuration
CAMUNDA_PORT=8080
CAMUNDA_JMX_PORT=9404
TZ=America/Sao_Paulo

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<strong-password>

# Scaling Configuration
CAMUNDA_REPLICAS=2  # HA mode

# Camunda Admin User Configuration
CAMUNDA_BPM_ADMIN_USER=admin
CAMUNDA_BPM_ADMIN_PASSWORD=<strong-password>

# JVM Memory Configuration (Optimized for Azure)
JAVA_OPTS_EXTRA=-Xms6g -Xmx8g -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:ParallelGCThreads=4 -XX:ConcGCThreads=2 -XX:+UseStringDeduplication -XX:G1ReservePercent=20 -XX:InitiatingHeapOccupancyPercent=45

# Database Connection Pool Optimization (HikariCP - Azure PostgreSQL)
# CRÍTICO: Ajustar para Azure
DB_CONNECTION_TIMEOUT=20000  # 20s
DB_IDLE_TIMEOUT=300000  # 5 min (antes do Azure idle timeout)
DB_MAX_LIFETIME=600000  # 10 min (reciclar antes do Azure timeout)
DB_MAXIMUM_POOL_SIZE=15  # Ajustar conforme tier Azure
DB_MINIMUM_IDLE=5  # Manter warm connections
DB_VALIDATION_TIMEOUT=3000
DB_KEEPALIVE_TIME=120000  # 2 min - CRÍTICO para Azure
DB_LEAK_DETECTION_THRESHOLD=60000  # 60s
DB_VALIDATE_ON_BORROW=true  # Validar conexões
```

#### 7.2 Docker Compose com PgBouncer

```yaml
# docker-compose.azure.yml
version: '3.8'

services:
  # PgBouncer - Connection Pooling Proxy
  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    environment:
      DB_HOST: ${AZURE_DB_HOST}
      DB_PORT: 5432
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_NAME: ${POSTGRES_DB}
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 500
      DEFAULT_POOL_SIZE: 25
      SERVER_IDLE_TIMEOUT: 300
      SERVER_LIFETIME: 3600
      SERVER_CONNECT_TIMEOUT: 15
    networks:
      - camunda_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "psql", "-h", "localhost", "-p", "5432", "-U", "${POSTGRES_USER}", "-c", "SELECT 1"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Redis - Caching Layer
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
      --tcp-keepalive 60
    networks:
      - camunda_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

  # Camunda BPM
  camunda:
    image: camunda/camunda-bpm-platform:run-7.23.0
    environment:
      DB_DRIVER: org.postgresql.Driver
      DB_URL: jdbc:postgresql://pgbouncer:5432/${POSTGRES_DB}?tcpKeepAlive=true&socketTimeout=30
      DB_USERNAME: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      TZ: ${TZ}
      JAVA_OPTS: ${JAVA_OPTS_EXTRA}
      DB_CONNECTION_TIMEOUT: ${DB_CONNECTION_TIMEOUT}
      DB_IDLE_TIMEOUT: ${DB_IDLE_TIMEOUT}
      DB_MAX_LIFETIME: ${DB_MAX_LIFETIME}
      DB_MAXIMUM_POOL_SIZE: ${DB_MAXIMUM_POOL_SIZE}
      DB_MINIMUM_IDLE: ${DB_MINIMUM_IDLE}
      DB_KEEPALIVE_TIME: ${DB_KEEPALIVE_TIME}
    depends_on:
      pgbouncer:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - camunda_network
    ports:
      - "${CAMUNDA_PORT}:8080"
      - "${CAMUNDA_JMX_PORT}:9404"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-q", "-O-", "http://localhost:8080/engine-rest/engine"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  redis_data:

networks:
  camunda_network:
    driver: bridge
```

---

### 8. Testes e Validação

#### 8.1 Script de Teste de Latência

```bash
#!/bin/bash
# test-azure-db-performance.sh

echo "=== Azure PostgreSQL Performance Test ==="
echo ""

# Variáveis
DB_HOST="camunda-dc-db.postgres.database.azure.com"
DB_USER="root_camunda"
DB_NAME="postgres"
ITERATIONS=10

echo "1. Network Latency Test"
echo "------------------------"
for i in $(seq 1 $ITERATIONS); do
    ping -c 1 $DB_HOST | grep 'time=' | awk -F'time=' '{print "Ping " $i ": " $2}'
done

echo ""
echo "2. Connection Test"
echo "-------------------"
for i in $(seq 1 $ITERATIONS); do
    { time psql "host=$DB_HOST port=5432 user=$DB_USER sslmode=require dbname=$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; } 2>&1 | grep real
done

echo ""
echo "3. Query Performance Test"
echo "--------------------------"
psql "host=$DB_HOST port=5432 user=$DB_USER sslmode=require dbname=$DB_NAME" <<EOF
\timing on
SELECT COUNT(*) FROM act_hi_procinst;
SELECT COUNT(*) FROM act_ru_execution;
SELECT COUNT(*) FROM act_re_deployment;
EOF

echo ""
echo "4. Connection Pool Test"
echo "------------------------"
docker exec camunda-platform-camunda-1 wget -q -O- http://localhost:9404/metrics | grep hikari

echo ""
echo "=== Test Complete ==="
```

#### 8.2 Benchmark Comparativo

```bash
# Comparar: Local vs Azure vs Azure+PgBouncer vs Azure+VNet

# Criar arquivo de resultados
cat > benchmark-results.md << 'EOF'
# Benchmark Results

| Configuração | Ping (ms) | Connect (ms) | Query (ms) | Startup (s) |
|--------------|-----------|--------------|------------|-------------|
| Local PostgreSQL | 0.1 | 127 | 50 | 7.8 |
| Azure PostgreSQL (Public) | ? | ? | ? | ? |
| Azure + PgBouncer | ? | ? | ? | ? |
| Azure + VNet Endpoint | ? | ? | ? | ? |
| Azure + Private Link | ? | ? | ? | ? |
EOF
```

---

### 9. Troubleshooting Checklist

```bash
# Checklist de diagnóstico rápido

# 1. Conectividade básica
☐ ping camunda-dc-db.postgres.database.azure.com
☐ telnet camunda-dc-db.postgres.database.azure.com 5432
☐ nslookup camunda-dc-db.postgres.database.azure.com

# 2. Firewall Azure
☐ Azure Portal > Networking > Firewall rules
☐ Verificar IP da VM está permitido
☐ Testar regra "Allow Azure Services" (temporário)

# 3. Credenciais
☐ psql "host=... port=5432 user=root_camunda sslmode=require"
☐ Verificar formato do username (pode precisar @server-name)

# 4. SSL/TLS
☐ sslmode=require está configurado
☐ Certificado Azure está válido
☐ Testar sslmode=prefer (debug only)

# 5. Métricas Azure
☐ Azure Portal > Monitoring > Metrics
☐ Verificar CPU, Conexões, Storage
☐ Revisar logs de diagnóstico

# 6. Logs Camunda
☐ docker logs camunda-platform-camunda-1
☐ Buscar: "connection", "timeout", "HikariPool"

# 7. Performance
☐ Query Performance Insights (Azure Portal)
☐ pg_stat_activity (conexões ativas)
☐ pg_stat_statements (queries lentas)
```

---

### 10. Estimativa de Custos Azure

| Componente | Tier | Especificação | Custo/mês (USD) |
|------------|------|---------------|-----------------|
| **Azure Database for PostgreSQL** | | | |
| Basic | 2 vCores, 50GB | Mínimo | ~$60 |
| General Purpose | 4 vCores, 100GB | Recomendado | ~$250 |
| Memory Optimized | 4 vCores, 32GB RAM | High Performance | ~$400 |
| **Networking** | | | |
| VNet Service Endpoint | - | Incluído | $0 |
| Private Link | - | Dados processados | ~$10 |
| **Backup** | | | |
| Automated Backups | 7 dias | Incluído | $0 |
| Long-term Retention | 35 dias | ~100GB | ~$10 |
| **Estimativa Total** | General Purpose + VNet | Produção | **~$260/mês** |

**Comparação:**
- Banco local (VM storage): ~$20/mês (100GB SSD)
- Azure Database: ~$260/mês (managed, HA, backups)

---

## Recomendações Finais

### Curto Prazo (Manter Banco Local)
✅ **Status atual é adequado** para:
- Ambientes de desenvolvimento
- QA/Testing
- Produção com requisitos de latência ultra-baixa
- Casos onde custo é prioridade

**Próximos passos:**
1. Implementar backup automatizado do banco local
2. Configurar replicação (opcional)
3. Monitorar métricas de performance

### Longo Prazo (Migrar para Azure se necessário)

**Quando migrar para Azure:**
- ✅ Necessidade de HA (High Availability)
- ✅ Backups gerenciados automáticos
- ✅ Escalabilidade vertical fácil
- ✅ Compliance e segurança Azure
- ✅ Disaster Recovery entre regiões

**Pré-requisitos para migração:**
1. ☑ Configurar VNet Service Endpoint (OBRIGATÓRIO)
2. ☑ Testar conectividade end-to-end
3. ☑ Implementar PgBouncer
4. ☑ Ajustar HikariCP parameters
5. ☑ Realizar testes de carga
6. ☑ Planejar janela de migração

---

## Contato e Suporte

**Documentação Azure:**
- https://learn.microsoft.com/azure/postgresql/
- https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-networking

**Camunda Database:**
- https://docs.camunda.org/manual/latest/user-guide/process-engine/database/

**Criado em:** 2025-11-03
**Última atualização:** 2025-11-03
**Autor:** Claude Code + DevOps Team
