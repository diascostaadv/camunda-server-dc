# Worker API Gateway

Gateway independente para processamento assíncrono de tarefas Camunda com MongoDB, RabbitMQ e Redis.

## Arquitetura

- **FastAPI Gateway** (API REST para workers)
- **MongoDB** (Armazenamento de tarefas)
- **RabbitMQ** (Fila de processamento)
- **Redis** (Cache e sessions)

## Uso Local

```bash
# Inicializar gateway
make local-up

# Parar gateway
make local-down

# Ver logs
make local-logs

# Status
make local-status

# Testar API
make local-test
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

# Testar remoto
make remote-test
```

## URLs de Acesso

### Local
- Gateway API: http://localhost:8000
- Gateway Metrics: http://localhost:9000/metrics
- RabbitMQ Management: http://localhost:15672 (admin/admin123)

### Produção
- Gateway API: http://201.23.67.197:8000
- Gateway Metrics: http://201.23.67.197:9000/metrics
- RabbitMQ Management: http://201.23.67.197:15672

## API Endpoints

### Principais
- `GET /` - Informações do gateway
- `GET /health` - Health check detalhado
- `POST /tasks/submit` - Submeter nova tarefa
- `GET /tasks/{task_id}/status` - Status da tarefa
- `POST /tasks/{task_id}/retry` - Reprocessar tarefa

### Exemplo de Uso

```bash
# Health check
curl http://localhost:8000/health

# Submeter tarefa
curl -X POST http://localhost:8000/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "12345",
    "worker_id": "hello-world-worker",
    "topic": "say_hello",
    "variables": {"name": "World"}
  }'

# Verificar status
curl http://localhost:8000/tasks/12345/status
```

## Configuração

### Arquivos de Ambiente
- `.env.local` - Desenvolvimento local
- `.env.production` - Produção remota

### Escalabilidade
```bash
# Escalar Gateway (apenas Swarm)
make scale-gateway N=3
```

## Utilitários

```bash
# Health check completo
make health-check

# Shell MongoDB
make mongodb-shell

# Estatísticas RabbitMQ
make rabbitmq-queue-stats
```

## Desenvolvimento

```bash
# Setup ambiente dev
make dev-setup

# Executar em modo dev
make dev-run

# Testar API
make test-api
```

## Monitoramento

- Métricas Prometheus no endpoint `/metrics`
- Health checks automáticos
- Logs estruturados
- Dashboard RabbitMQ para filas