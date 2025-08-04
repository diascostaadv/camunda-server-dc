# Worker API Gateway

Sistema centralizado de gestão de tarefas para workers Camunda com processamento assíncrono via MongoDB e RabbitMQ.

## Quick Start

### 1. Configuração

```bash
# Copiar configuração de exemplo
cp ../.env.gateway.example .env

# Editar URIs dos clusters
nano .env
```

### 2. Execução Local (Desenvolvimento)

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar Gateway
python main.py
```

### 3. Execução via Docker

```bash
# Build da imagem
docker build -t worker-api-gateway .

# Executar container
docker run -p 8000:8000 --env-file .env worker-api-gateway
```

### 4. Deploy Completo

```bash
# Na raiz do projeto
docker compose --profile gateway --profile gateway-workers up -d
```

## API Endpoints

### Health Check
```
GET /health
```

### Submeter Tarefa
```
POST /tasks/submit
{
  "task_id": "camunda-task-123",
  "worker_id": "publicacao-worker",
  "topic": "nova_publicacao",
  "variables": {...}
}
```

### Consultar Status
```
GET /tasks/{task_id}/status
```

### Retry Tarefa
```
POST /tasks/{task_id}/retry
```

## Configuração

### Environment Variables

```env
# Application
PORT=8000
DEBUG=false

# MongoDB (External Cluster)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/worker_gateway
MONGODB_DATABASE=worker_gateway

# RabbitMQ (External Cluster)
RABBITMQ_URL=amqp://user:pass@rabbitmq-cluster.host:5672/
RABBITMQ_EXCHANGE=worker_gateway

# Task Processing
TASK_TIMEOUT=300
TASK_RETRY_LIMIT=3
```

## Desenvolvimento

### Estrutura do Projeto

```
worker-api-gateway/
├── main.py                 # FastAPI application
├── core/
│   └── config.py          # Configuration management
├── models/
│   └── task.py            # Pydantic models
├── services/
│   ├── task_manager.py    # MongoDB operations
│   ├── rabbitmq_consumer.py # RabbitMQ handling
│   └── task_processor.py  # Task processing logic
├── requirements.txt
├── Dockerfile
└── README.md
```

### Adicionar Novo Topic

1. **Adicionar topic em `core/config.py`**:
```python
SUPPORTED_TOPICS = [
    "nova_publicacao",
    "say_hello",
    "novo_topic"  # Adicionar aqui
]
```

2. **Implementar handler em `services/task_processor.py`**:
```python
async def _process_novo_topic(self, task_submission: TaskSubmission) -> Dict[str, Any]:
    # Sua lógica aqui
    return {"status": "success"}
```

3. **Mapear handler**:
```python
self.topic_handlers = {
    "novo_topic": self._process_novo_topic,
    # outros handlers...
}
```

## Monitoramento

### Métricas (Prometheus)
- Gateway disponível em `/metrics` (se habilitado)
- Workers mantêm métricas nas portas configuradas

### Logs
```bash
# Gateway logs
docker compose logs -f worker-api-gateway

# Logs estruturados em JSON para produção
LOG_LEVEL=INFO
```

### Health Checks
```bash
# Status geral
curl http://localhost:8000/health

# FastAPI docs
open http://localhost:8000/docs
```

## Troubleshooting

### Gateway não inicia
```bash
# Verificar logs
docker compose logs worker-api-gateway

# Testar MongoDB
curl http://localhost:8000/health
```

### Tarefas não processam
```bash
# Status das tarefas
curl http://localhost:8000/tasks/statistics

# Logs do processamento
docker compose logs worker-api-gateway | grep "task-id"
```

## Documentação Completa

Ver: `../docs/WORKER-API-GATEWAY.md`