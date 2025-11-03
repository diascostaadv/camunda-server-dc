# Guia Rápido - Manutenção de Espaço em Disco

## 🚨 Problema Resolvido
Sistema caindo periodicamente por falta de espaço em disco.

## ✅ Correções Aplicadas (2025-11-03)

1. **Prometheus**: Retenção de 30 dias / 10GB máximo
2. **Logs Docker**: Rotação automática (máx 500MB por serviço)
3. **Heap Dumps**: Volume dedicado com limpeza automática
4. **PostgreSQL**: Autovacuum otimizado
5. **Script de Limpeza**: Automação diária

---

## 📋 Comandos Essenciais

### Verificar Espaço em Disco
```bash
make disk-usage
```

### Executar Limpeza Manual
```bash
# Limpeza padrão (sem root)
make cleanup-maintenance

# Limpeza completa (requer root)
make cleanup-maintenance-full

# Apenas relatório
make cleanup-report
```

### Configurar Limpeza Automática (Primeira Vez)
```bash
# Configura cron para executar diariamente às 2 AM
make setup-cron
```

### Verificar Logs de Limpeza
```bash
ssh ubuntu@201.23.67.197 "tail -f /var/log/camunda-cleanup.log"
```

---

## 🚀 Deploy das Correções

```bash
# 1. Fazer backup
make backup-db

# 2. Deploy
cd camunda-platform-standalone
make deploy ENVIRONMENT=production

# 3. Configurar cron (primeira vez apenas)
make setup-cron

# 4. Verificar status
make remote-status
make cleanup-report
```

---

## 📊 Monitoramento

### Alerta: Disco > 80%
```bash
make disk-usage
```

### Alerta: Histórico Camunda > 50k instâncias
```bash
# Via API
curl -s -u demo:demo http://201.23.67.197:8080/engine-rest/history/process-instance/count
```

### Verificar Tamanho do Banco
```bash
make psql
# Dentro do psql:
SELECT pg_size_pretty(pg_database_size('camunda'));
```

---

## 🔧 Troubleshooting Rápido

### Espaço ainda esgotando?
1. Verificar logs de limpeza: `ssh ubuntu@201.23.67.197 "cat /var/log/camunda-cleanup.log"`
2. Executar limpeza completa: `make cleanup-maintenance-full`
3. Verificar cron está ativo: `ssh ubuntu@201.23.67.197 "crontab -l"`

### Prometheus > 10GB?
```bash
# Forçar limpeza manual do Prometheus
ssh ubuntu@201.23.67.197
docker exec -it <prometheus_container_id> promtool tsdb analyze /prometheus
docker exec -it <prometheus_container_id> promtool tsdb clean /prometheus
```

### Logs Docker crescendo?
```bash
# Verificar configuração de logging
docker inspect <container_id> | grep -A 5 LogConfig

# Se necessário, forçar recriação
make remote-restart
```

---

## 📝 Próximos Passos

- [ ] Configurar cron (se ainda não feito): `make setup-cron`
- [ ] Adicionar alertas no Grafana para disco > 80%
- [ ] Revisar logs semanalmente: `/var/log/camunda-cleanup.log`
- [ ] Executar backup mensal: `make backup-db`

---

## 📖 Documentação Completa

Para detalhes completos, consulte: [DISK_SPACE_FIXES.md](DISK_SPACE_FIXES.md)

---

## 📈 Resultado Esperado

| Métrica | Antes | Depois |
|---------|-------|--------|
| Crescimento semanal | ~3-5GB | ~500MB |
| Prometheus | Ilimitado | 10GB max |
| Logs | Ilimitado | ~1.3GB max |
| Estabilidade | ❌ Quedas frequentes | ✅ Estável |
