# Camunda Platform Standalone

Plataforma Camunda BPM independente com monitoramento integrado (Prometheus + Grafana).

## Arquitetura

- **Camunda BPM 7.23.0** (Tomcat com JMX)
- **PostgreSQL 16.3** (Banco de dados)
- **Prometheus** (Métricas)
- **Grafana** (Dashboards)

## Uso Local

```bash
# Inicializar plataforma
make local-up

# Parar plataforma
make local-down

# Ver logs
make local-logs

# Status
make local-status
```

## Deploy Remoto

```bash
# Deploy completo
make deploy

# Parar remotamente
make remote-down

# Logs remotos
make remote-logs

# Status remoto
make remote-status
```

## URLs de Acesso

### Local
- Camunda: http://localhost:8080 (demo/demo)
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)

### Produção
- Camunda: http://201.23.67.197:8080 (demo/demo)
- Prometheus: http://201.23.67.197:9090
- Grafana: http://201.23.67.197:3001 (admin/admin)

## Configuração

### Arquivos de Ambiente
- `.env.local` - Desenvolvimento local
- `.env.production` - Produção remota

### Escalabilidade
```bash
# Escalar Camunda (apenas Swarm)
make scale N=3
```

## Utilitários

```bash
# Backup do banco
make backup-db

# Acesso ao PostgreSQL
make psql

# Instalar Docker no servidor
make install-docker

# Inicializar Docker Swarm
make init-swarm
```

## Monitoramento

- Métricas JMX do Camunda coletadas pelo Prometheus
- Dashboards pré-configurados no Grafana
- Configuração automática baseada no ambiente