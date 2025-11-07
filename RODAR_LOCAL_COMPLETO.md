# 🏠 Guia Completo: Rodar Gateway + Workers Localmente

**Data**: 2025-11-07
**Objetivo**: Testar integração completa antes de deploy em produção

---

## 📋 Pré-requisitos

- [x] Docker Desktop instalado e rodando
- [x] Docker Compose instalado
- [x] Porta 8000 livre (Gateway)
- [x] Porta 8080 livre (Camunda) - ou usar Camunda remoto
- [x] Portas 8003, 8004, 8010 livres (Workers)
- [x] 8GB RAM disponível

---

## 🎯 Arquitetura Local

```
┌─────────────────────────────────────────────────────────┐
│  Sua Máquina Local                                      │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  camunda-worker-api-gateway                │        │
│  │  - Gateway :8000                            │        │
│  │  - MongoDB (Azure Cosmos DB)                │        │
│  │  - RabbitMQ :5672 (local container)         │        │
│  │  - Redis :6379 (local container)            │        │
│  └────────────────────────────────────────────┘        │
│           │                                              │
│           │ HTTP                                         │
│           ▼                                              │
│  ┌────────────────────────────────────────────┐        │
│  │  camunda-workers-platform                  │        │
│  │  - worker-publicacao-unified :8003         │        │
│  │  - worker-cpj-api :8004                    │        │
│  │  - worker-dw-law :8010 ✨ NOVO             │        │
│  └────────────────────────────────────────────┘        │
│           │                                              │
└───────────┼──────────────────────────────────────────────┘
            │
            │ External Task Client
            ▼
   ┌────────────────────────┐
   │  Camunda BPM           │
   │  201.23.67.197:8080    │  ← Usar Camunda remoto
   │  OU localhost:8080     │  ← OU rodar local
   └────────────────────────┘
```

---

## 🚀 OPÇÃO 1: Usar Camunda Remoto (Mais Simples)

### Vantagens
- ✅ Não precisa rodar Camunda local
- ✅ Usa Camunda de produção (já configurado)
- ✅ Menos recursos necessários

### Passo 1: Configurar Workers para Camunda Remoto

**Arquivo**: `camunda-workers-platform/.env.local`

Criar/editar:
```bash
# Camunda Configuration (Remoto)
CAMUNDA_URL=http://201.23.67.197:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=DiasCostaA!!2025

# Gateway Configuration (Local)
GATEWAY_ENABLED=true
GATEWAY_URL=http://localhost:8000
GATEWAY_COMMUNICATION_MODE=http
GATEWAY_HTTP_TIMEOUT=30

# Worker Configuration
MAX_TASKS=2
LOCK_DURATION=60000
ASYNC_RESPONSE_TIMEOUT=30000
RETRIES=3
RETRY_TIMEOUT=5000
SLEEP_SECONDS=30

# Monitoring
METRICS_PORT=8003
METRICS_ENABLED=true
LOG_LEVEL=INFO
ENVIRONMENT=local

# DW LAW Configuration
DW_LAW_BASE_URL=https://web-eprotocol-integration-cons-qa.azurewebsites.net
DW_LAW_USUARIO=integ_dias_cons@dwlaw.com.br
DW_LAW_SENHA=DC@Dwlaw2025
DW_LAW_CHAVE_PROJETO=diascostacitacaoconsultaunica
DW_LAW_TOKEN_EXPIRY_MINUTES=120
DW_LAW_TIMEOUT=120

# Scaling
WORKER_PUBLICACAO_UNIFIED_REPLICAS=1
WORKER_CPJ_API_REPLICAS=1
WORKER_DW_LAW_REPLICAS=1
```

### Passo 2: Configurar Gateway para Local

**Arquivo**: `camunda-worker-api-gateway/.env.local`

Criar/editar:
```bash
# ==================== APPLICATION ====================
APP_NAME=Worker API Gateway
VERSION=1.0.0
DEBUG=true
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=local
LOG_LEVEL=DEBUG

# ==================== MONGODB (Azure) ====================
MONGODB_URI=mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/
MONGODB_DATABASE=worker_gateway

# ==================== RABBITMQ (Local Container) ====================
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
RABBITMQ_EXCHANGE=worker_gateway

# ==================== REDIS (Local Container) ====================
REDIS_URI=redis://redis:6379

# ==================== CPJ API ====================
CPJ_BASE_URL=https://app.leviatan.com.br/dcncadv/cpj/agnes/api/v2
CPJ_LOGIN=api
CPJ_PASSWORD=2025
CPJ_TOKEN_EXPIRY_MINUTES=30

# ==================== N8N ====================
N8N_WEBHOOK_URL=https://nutec.app.n8n.cloud/webhook/1e5790e3-8efd-4246-88c1-fbb0ef3c68a7
N8N_TIMEOUT=120

# ==================== DW LAW E-PROTOCOL ====================
DW_LAW_BASE_URL=https://web-eprotocol-integration-cons-qa.azurewebsites.net
DW_LAW_USUARIO=integ_dias_cons@dwlaw.com.br
DW_LAW_SENHA=DC@Dwlaw2025
DW_LAW_TOKEN_EXPIRY_MINUTES=120
DW_LAW_TIMEOUT=120
DW_LAW_CHAVE_PROJETO=diascostacitacaoconsultaunica

# ==================== CAMUNDA REST API ====================
CAMUNDA_REST_URL=http://201.23.67.197:8080/engine-rest
CAMUNDA_REST_USER=demo
CAMUNDA_REST_PASSWORD=DiasCostaA!!2025

# ==================== TASK PROCESSING ====================
TASK_TIMEOUT=300
TASK_RETRY_LIMIT=3
TASK_RETRY_DELAY=60

# ==================== METRICS ====================
METRICS_ENABLED=true
METRICS_PORT=9000

# ==================== SECURITY ====================
SECRET_KEY=local-dev-secret-key
```

### Passo 3: Atualizar docker-compose do Gateway

**Arquivo**: `camunda-worker-api-gateway/docker-compose.yml`

Editar linha 68 para usar `.env.local`:
```yaml
  gateway:
    build:
      context: ./app
      dockerfile: Dockerfile
    env_file:
      - .env.local  # Alterar de .env.production para .env.local
```

E REMOVER `profiles` dos serviços locais (linhas 6, 26, 47):
```yaml
  mongodb:
    # profiles: ["local-services"]  # COMENTAR esta linha

  rabbitmq:
    # profiles: ["local-services"]  # COMENTAR esta linha

  redis:
    # profiles: ["local-services"]  # COMENTAR esta linha
```

### Passo 4: Atualizar docker-compose dos Workers

**Arquivo**: `camunda-workers-platform/docker-compose.yml`

Editar para usar `.env.local`:
```yaml
  worker-publicacao-unified:
    build:
      context: ./workers
      dockerfile: publicacao_unified/Dockerfile
    env_file:
      - .env.local  # Alterar de env.gateway para .env.local
```

Fazer o mesmo para `worker-cpj-api` e `worker-dw-law`.

---

## 📝 Comandos de Execução

### Terminal 1: Iniciar Gateway + Serviços

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway

# Build
docker compose build

# Iniciar Gateway + MongoDB + RabbitMQ + Redis
docker compose up

# OU em background:
docker compose up -d

# Ver logs
docker compose logs -f gateway
```

**Aguardar até ver**:
```
✅ Application startup complete
✅ Uvicorn running on http://0.0.0.0:8000
✅ MongoDB connected
✅ RabbitMQ connected
✅ Redis connected
```

### Terminal 2: Iniciar Workers

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Build
docker compose build

# Iniciar todos os workers
docker compose up

# OU em background:
docker compose up -d

# Ver logs específicos
docker logs -f worker-dw-law
docker logs -f worker-publicacao-unified
docker logs -f worker-cpj-api
```

**Aguardar até ver** (em cada worker):
```
✅ Worker configurado em modo orquestrador (Gateway)
🔍 DWLawWorker iniciado - aguardando tarefas nos tópicos
📊 Prometheus metrics server started
🚀 Worker ready and waiting for external tasks
```

---

## ✅ Verificações

### 1. Gateway Health
```bash
curl http://localhost:8000/health

# Esperado:
# {"status":"healthy","service":"Worker API Gateway",...}
```

### 2. Gateway Docs (Swagger)
```bash
open http://localhost:8000/docs
```

### 3. Worker DW LAW Health
```bash
curl http://localhost:8010/health

# Esperado:
# {"status":"healthy","worker":"dw-law-worker",...}
```

### 4. Worker DW LAW Metrics
```bash
curl http://localhost:8010/metrics | grep external_task
```

### 5. Teste Conexão DW LAW
```bash
curl http://localhost:8000/dw-law/test-connection | jq .

# Esperado:
# {
#   "success": true,
#   "dw_law": {
#     "authenticated": true,
#     ...
#   },
#   "camunda": {
#     "success": true,
#     ...
#   }
# }
```

### 6. RabbitMQ Management
```bash
open http://localhost:15672
# Login: admin / admin123
```

### 7. Camunda Cockpit (Remoto)
```bash
open http://201.23.67.197:8080/camunda/app/cockpit
# Login: demo / DiasCostaA!!2025

# Verificar External Tasks
# Deve mostrar 9 tópicos:
# - nova_publicacao
# - BuscarPublicacoes
# - ... (outros)
# - INSERIR_PROCESSOS_DW_LAW ✅
# - EXCLUIR_PROCESSOS_DW_LAW ✅
# - CONSULTAR_PROCESSO_DW_LAW ✅
```

---

## 🧪 Testes de Integração

### Teste 1: Autenticação DW LAW
```bash
curl -X POST 'http://localhost:8000/dw-law/test-connection' | jq .
```

### Teste 2: Inserir Processo
```bash
curl -X POST 'http://localhost:8000/dw-law/inserir-processos' \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_projeto": "diascostacitacaoconsultaunica",
    "processos": [
      {
        "numero_processo": "0012205-60.2015.5.15.0077",
        "other_info_client1": "TESTE_LOCAL",
        "other_info_client2": "DESENVOLVIMENTO"
      }
    ],
    "camunda_business_key": "teste-local-001"
  }' | jq .
```

**Resposta esperada**:
```json
{
  "success": true,
  "message": "1 processos inseridos com sucesso",
  "data": {
    "chave_projeto": "diascostacitacaoconsultaunica",
    "total_inseridos": 1,
    "processos": [
      {
        "numero_processo": "0012205-60.2015.5.15.0077",
        "chave_de_pesquisa": "UUID-GERADO",
        "tribunal": "TJPB",
        ...
      }
    ]
  }
}
```

### Teste 3: Consultar Processo
```bash
# Usar chave_de_pesquisa do teste anterior
curl -X POST 'http://localhost:8000/dw-law/consultar-processo' \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_de_pesquisa": "UUID-GERADO-ACIMA"
  }' | jq .
```

### Teste 4: Simular Callback
```bash
curl -X POST 'http://localhost:8000/dw-law/callback' \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_de_pesquisa": "test-callback-123",
    "numero_processo": "1234567-89.2024.1.01.0001",
    "status_pesquisa": "S",
    "descricao_status_pesquisa": "Teste de callback local"
  }' | jq .
```

---

## 📊 Monitoramento Local

### Ver Containers Rodando
```bash
docker ps

# Esperado ver:
# - camunda-worker-api-gateway-gateway-1
# - camunda-worker-api-gateway-rabbitmq-1
# - camunda-worker-api-gateway-redis-1
# - worker-dw-law
# - worker-publicacao-unified
# - worker-cpj-api
```

### Ver Logs em Tempo Real
```bash
# Gateway
docker logs -f camunda-worker-api-gateway-gateway-1

# Worker DW LAW
docker logs -f worker-dw-law

# Todos os workers
cd camunda-workers-platform
docker compose logs -f
```

### Verificar MongoDB (Azure)
```bash
mongosh "mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/worker_gateway"

# Ver processos DW LAW
db.dw_law_processos.find().pretty()

# Ver consultas
db.dw_law_consultas.find().sort({timestamp_consulta: -1}).limit(5).pretty()

# Ver callbacks
db.dw_law_callbacks.find().sort({timestamp_recebimento: -1}).limit(5).pretty()
```

---

## 🛑 Parar Tudo

```bash
# Terminal 1: Parar Gateway
cd camunda-worker-api-gateway
docker compose down

# Terminal 2: Parar Workers
cd camunda-workers-platform
docker compose down

# Limpar tudo (CUIDADO: Remove volumes)
docker compose down -v
```

---

## 🔄 Reiniciar

```bash
# Gateway
cd camunda-worker-api-gateway
docker compose restart gateway

# Workers
cd camunda-workers-platform
docker compose restart worker-dw-law
```

---

## 🆘 Troubleshooting

### Gateway não inicia
```bash
# Ver logs
docker logs camunda-worker-api-gateway-gateway-1

# Verificar se portas estão livres
lsof -i :8000
lsof -i :5672
lsof -i :6379

# Rebuild
docker compose build --no-cache gateway
docker compose up gateway
```

### Worker não conecta ao Gateway
```bash
# Verificar se Gateway está acessível
curl http://localhost:8000/health

# Ver logs do worker
docker logs worker-dw-law

# Verificar variável GATEWAY_URL
docker exec worker-dw-law env | grep GATEWAY
```

### Worker não conecta ao Camunda
```bash
# Testar Camunda remoto
curl http://201.23.67.197:8080/engine-rest/version

# Verificar variável CAMUNDA_URL
docker exec worker-dw-law env | grep CAMUNDA
```

### RabbitMQ/Redis não funcionam
```bash
# Verificar se containers estão rodando
docker ps | grep rabbitmq
docker ps | grep redis

# Ver logs
docker logs camunda-worker-api-gateway-rabbitmq-1
docker logs camunda-worker-api-gateway-redis-1

# Testar conexão
docker exec camunda-worker-api-gateway-gateway-1 curl amqp://admin:admin123@rabbitmq:5672/
```

---

## ✅ Checklist de Validação Local

- [ ] Gateway rodando em http://localhost:8000
- [ ] Gateway /health retorna OK
- [ ] Gateway /docs acessível (Swagger)
- [ ] RabbitMQ rodando (:5672, :15672)
- [ ] Redis rodando (:6379)
- [ ] MongoDB (Azure) acessível
- [ ] Worker DW LAW rodando (:8010)
- [ ] Worker Publicacao rodando (:8003)
- [ ] Worker CPJ rodando (:8004)
- [ ] Workers conectados ao Gateway
- [ ] Workers conectados ao Camunda (remoto)
- [ ] Teste de autenticação DW LAW OK
- [ ] Teste de inserção de processo OK
- [ ] Teste de consulta de processo OK
- [ ] Teste de callback OK
- [ ] Tópicos registrados no Camunda
- [ ] Logs sem erros críticos

---

## 🎯 Próximos Passos

Após validar local:
1. ✅ Tudo funcionando local
2. 🚀 Deploy em produção (VM 201.23.69.65)
3. 📝 Documentar configurações finais
4. 🔄 Configurar callback no DW LAW

---

**✅ Ambiente local pronto para desenvolvimento e testes!**
