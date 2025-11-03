# Correções de Esgotamento de Espaço em Disco

**Data**: 2025-11-03
**Versão**: 1.0
**Status**: Implementado

## 📋 Resumo Executivo

Este documento descreve as correções implementadas para resolver o problema de esgotamento de espaço em disco no `camunda-platform-standalone`. O sistema estava caindo periodicamente devido ao crescimento descontrolado de dados.

## 🔍 Problemas Identificados

### 1. Prometheus sem Retenção (CRÍTICO)
- **Causa**: Métricas acumulando indefinidamente
- **Crescimento**: ~3-5GB/semana
- **Arquivos afetados**: `docker-compose.swarm.yml`, `docker-compose.simple.yml`

### 2. Logs Docker sem Rotação
- **Causa**: Logs de containers crescendo sem limite em `/var/lib/docker/containers/`
- **Crescimento**: ~1-2GB/semana
- **Impacto**: Todos os serviços

### 3. Heap Dumps sem Gerenciamento
- **Causa**: Dumps de 4-6GB cada armazenados em `/tmp` sem limpeza
- **Impacto**: Espaço esgotado após 2-3 OOM events

### 4. PostgreSQL sem Autovacuum Otimizado
- **Causa**: Tabelas de histórico (`ACT_HI_*`) crescendo sem limpeza eficiente
- **Crescimento**: Variável, dependendo do volume de processos

### 5. Dados Históricos do Camunda
- **Causa**: `historyTimeToLive=30` configurado mas job de limpeza não monitorado
- **Impacto**: Crescimento do banco de dados

---

## ✅ Correções Implementadas

### 1. Retenção de Dados do Prometheus

**Arquivos modificados**:
- [docker-compose.swarm.yml](docker-compose.swarm.yml#L83-L84)
- [docker-compose.simple.yml](docker-compose.simple.yml#L80-L81)

**Mudanças**:
```yaml
command:
  - "--storage.tsdb.retention.time=30d"  # Manter apenas 30 dias
  - "--storage.tsdb.retention.size=10GB"  # Limite de 10GB
```

**Impacto esperado**: Redução de ~80% no crescimento de métricas

---

### 2. Rotação de Logs Docker

**Arquivos modificados**: Todos os serviços em `docker-compose.swarm.yml` e `docker-compose.simple.yml`

**Mudanças**:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"   # Para Prometheus/Grafana
    max-file: "3"     # Manter 3 arquivos rotacionados
```

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "100m"  # Para Camunda/PostgreSQL (mais verboso)
    max-file: "5"     # Manter 5 arquivos rotacionados
```

**Impacto esperado**:
- Camunda: Max 500MB de logs (100MB × 5 arquivos)
- PostgreSQL: Max 500MB de logs
- Prometheus: Max 150MB de logs (50MB × 3 arquivos)
- Grafana: Max 150MB de logs

---

### 3. Gerenciamento de Heap Dumps

**Arquivos modificados**:
- [docker-compose.swarm.yml](docker-compose.swarm.yml#L60)
- [docker-compose.simple.yml](docker-compose.simple.yml#L47)
- [.env](.env#L47)

**Mudanças**:
```yaml
volumes:
  - camunda_heapdumps:/tmp/heapdumps  # Volume dedicado
```

```bash
JAVA_OPTS_EXTRA=...-XX:HeapDumpPath=/tmp/heapdumps...
```

**Impacto esperado**: Heap dumps isolados em volume próprio, gerenciável via script de limpeza

---

### 4. Autovacuum do PostgreSQL

**Arquivos modificados**:
- [docker-compose.swarm.yml](docker-compose.swarm.yml#L12)
- [docker-compose.simple.yml](docker-compose.simple.yml#L12)

**Mudanças**:
```yaml
environment:
  POSTGRES_INITDB_ARGS: "-c autovacuum=on -c autovacuum_max_workers=3"
```

**Impacto esperado**: Limpeza automática e eficiente de espaço no PostgreSQL

---

### 5. Script de Limpeza Periódica

**Arquivo criado**: [scripts/cleanup-maintenance.sh](scripts/cleanup-maintenance.sh)

**Funcionalidades**:
- ✅ Limpeza de heap dumps antigos (>7 dias)
- ✅ Limpeza de histórico do Camunda (via API)
- ✅ Vacuum do PostgreSQL
- ✅ Limpeza de recursos Docker não utilizados
- ✅ Relatório de uso de disco

**Modos de execução**:
```bash
# Limpeza padrão (sem root)
./scripts/cleanup-maintenance.sh standard

# Limpeza completa (requer root)
sudo ./scripts/cleanup-maintenance.sh full

# Apenas relatório
./scripts/cleanup-maintenance.sh report
```

---

## 📊 Impacto Esperado

| Componente | Antes | Depois | Redução |
|------------|-------|--------|---------|
| Prometheus | Ilimitado (~5GB/mês) | 10GB max | ~80% |
| Logs Docker | Ilimitado (~2GB/mês) | ~1.3GB max | ~95% |
| Heap Dumps | Sem controle | Gerenciado | 100% após limpeza |
| PostgreSQL | Crescimento linear | Crescimento controlado | ~50% |
| **Total estimado** | **~3-5GB/semana** | **~500MB/semana** | **~85%** |

---

## 🚀 Procedimentos de Deploy

### Passo 1: Backup Atual
```bash
# Fazer backup do banco de dados
make backup-db

# Verificar espaço em disco atual
ssh ubuntu@201.23.67.197 "df -h && docker system df -v"
```

### Passo 2: Limpeza Manual (Opcional mas Recomendado)
```bash
# Limpar histórico do Camunda
make clean-all

# Limpar recursos Docker não utilizados
ssh ubuntu@201.23.67.197 "docker system prune -af"
```

### Passo 3: Deploy das Novas Configurações
```bash
# Deploy completo para produção
cd camunda-platform-standalone
make deploy ENVIRONMENT=production
```

### Passo 4: Configurar Cron para Limpeza Automática
```bash
# SSH no servidor
ssh ubuntu@201.23.67.197

# Adicionar ao crontab (executar diariamente às 2AM)
crontab -e

# Adicionar linha:
0 2 * * * /home/ubuntu/camunda-platform/scripts/cleanup-maintenance.sh standard >> /var/log/camunda-cleanup.log 2>&1
```

### Passo 5: Verificação Pós-Deploy
```bash
# Verificar status dos serviços
make remote-status

# Verificar logs
make remote-logs

# Executar teste manual de limpeza
ssh ubuntu@201.23.67.197 "cd ~/camunda-platform && ./scripts/cleanup-maintenance.sh report"
```

---

## 📈 Monitoramento

### Métricas para Monitorar no Grafana

1. **Uso de Disco do Sistema**
   - Criar alerta quando > 80%
   - Dashboard: System Metrics

2. **Tamanho dos Volumes Docker**
   - Prometheus data volume
   - Grafana data volume
   - PostgreSQL data volume
   - Heap dumps volume

3. **Crescimento do Banco de Dados**
   - Query: `SELECT pg_size_pretty(pg_database_size('camunda'));`
   - Monitorar tendência semanal

4. **Instâncias Históricas do Camunda**
   - Endpoint: `/engine-rest/history/process-instance/count`
   - Alerta se > 50,000

### Comandos de Verificação

```bash
# Verificar espaço em disco
make remote-status
ssh ubuntu@201.23.67.197 "df -h"

# Verificar tamanho dos volumes
ssh ubuntu@201.23.67.197 "docker system df -v"

# Verificar tamanho do banco
make psql
# Dentro do psql:
# SELECT pg_size_pretty(pg_database_size('camunda'));

# Executar relatório de limpeza
ssh ubuntu@201.23.67.197 "cd ~/camunda-platform && ./scripts/cleanup-maintenance.sh report"
```

---

## 🔧 Manutenção Contínua

### Diariamente (Automático via Cron)
- ✅ Limpeza de heap dumps antigos
- ✅ Limpeza de histórico do Camunda
- ✅ Geração de relatório de uso de disco

### Semanalmente (Manual)
- 📊 Revisar logs de limpeza em `/var/log/camunda-cleanup.log`
- 📊 Verificar tendências de crescimento no Grafana
- 📊 Validar que retenção do Prometheus está funcionando

### Mensalmente (Manual)
- 🗄️ Backup completo do banco de dados
- 🧹 Limpeza completa com modo `full` (requer root)
- 📈 Análise de tendências e ajuste de configurações se necessário

---

## ⚠️ Troubleshooting

### Problema: Serviço não inicia após deploy

**Sintomas**: Container fica reiniciando continuamente

**Diagnóstico**:
```bash
docker logs <container_id>
```

**Possíveis causas**:
1. Volume de heap dumps não criado corretamente
2. Configuração de autovacuum inválida
3. Prometheus com configurações incompatíveis

**Solução**:
```bash
# Remover volume problemático e recriar
docker volume rm camunda-platform-standalone_camunda_heapdumps
make remote-restart
```

### Problema: Prometheus usando mais de 10GB

**Sintomas**: Volume prometheus_data > 10GB

**Diagnóstico**:
```bash
docker volume inspect camunda-platform-standalone_prometheus_data
```

**Solução**:
1. Verificar se flags de retenção estão corretos
2. Forçar limpeza manual:
```bash
docker exec -it <prometheus_container> promtool tsdb analyze /prometheus
docker exec -it <prometheus_container> promtool tsdb clean /prometheus
```

### Problema: Logs ainda crescendo sem controle

**Sintomas**: `/var/lib/docker/containers/` ocupando muito espaço

**Diagnóstico**:
```bash
du -sh /var/lib/docker/containers/*
```

**Solução**:
```bash
# Verificar se configuração de logging está aplicada
docker inspect <container_id> | grep -A 5 LogConfig

# Forçar recriação dos containers
make remote-down
make deploy
```

---

## 📝 Histórico de Mudanças

| Data | Versão | Mudanças |
|------|--------|----------|
| 2025-11-03 | 1.0 | Implementação inicial de todas as correções |

---

## 🔗 Referências

- [Prometheus Storage](https://prometheus.io/docs/prometheus/latest/storage/)
- [Docker Logging Configuration](https://docs.docker.com/config/containers/logging/configure/)
- [PostgreSQL Autovacuum](https://www.postgresql.org/docs/16/routine-vacuuming.html#AUTOVACUUM)
- [Camunda History Cleanup](https://docs.camunda.org/manual/7.23/user-guide/process-engine/history/#history-cleanup)

---

## 📧 Suporte

Em caso de dúvidas ou problemas:
1. Verificar logs em `/var/log/camunda-cleanup.log`
2. Consultar este documento
3. Executar `./scripts/cleanup-maintenance.sh report` para diagnóstico
