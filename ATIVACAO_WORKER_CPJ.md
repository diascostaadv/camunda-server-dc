# 🚀 Guia de Ativação: Worker CPJ API

**Data**: 5 de Novembro de 2025
**Worker**: `cpj-api-worker`
**Status**: ✅ Configurado e Pronto para Deploy

---

## 📋 Pré-requisitos

Antes de ativar o worker CPJ, certifique-se de que:

1. ✅ **Gateway API está rodando** (`camunda-worker-api-gateway`)
2. ✅ **Camunda BPM está rodando** (`camunda-platform-standalone`)
3. ✅ **Credenciais CPJ-3C estão disponíveis** (usuário API tipo 3)
4. ✅ **Rede Docker configurada** (`camunda-worker-api-gateway_backend`)

---

## 🔧 Configuração

### 1. Variáveis de Ambiente CPJ

**Já configuradas automaticamente!** As variáveis foram adicionadas em:

#### Worker CPJ (`camunda-workers-platform/env.gateway`)
```bash
# CPJ API Configuration
CPJ_API_BASE_URL=https://cpj-server:porta/api/v2
CPJ_API_USER=1
CPJ_API_PASSWORD=abc
CPJ_TOKEN_EXPIRY_MINUTES=60
```

#### Gateway API (`camunda-worker-api-gateway/.env.local`)
```bash
# CPJ API Configuration
CPJ_BASE_URL=https://cpj-server:porta/api/v2
CPJ_LOGIN=1
CPJ_PASSWORD=abc
CPJ_TOKEN_EXPIRY_MINUTES=60
```

### 2. ⚠️ Atualizar Credenciais Reais

**IMPORTANTE**: Substitua os valores de exemplo pelas credenciais reais:

```bash
# Editar worker env
nano camunda-workers-platform/env.gateway

# Editar gateway env
nano camunda-worker-api-gateway/.env.local
```

**Substitua**:
- `https://cpj-server:porta/api/v2` → URL real do CPJ-3C
- `1` → Usuário API real (tipo 3 no CPJ)
- `abc` → Senha real da API

---

## 🏗️ Build do Worker

### Opção 1: Build Individual (Recomendado para Teste)

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Build apenas do worker CPJ
docker build -f workers/cpj_api_worker/Dockerfile -t worker-cpj-api:latest ./workers

# Verificar se foi criado
docker images | grep worker-cpj-api
```

### Opção 2: Build com Docker Compose

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Build de todos os workers (inclui CPJ)
docker-compose build

# Ou apenas CPJ
docker-compose build worker-cpj-api
```

---

## 🚀 Deploy

### Opção 1: Deploy Local (Desenvolvimento/Teste)

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Subir apenas o worker CPJ
docker-compose up -d worker-cpj-api

# Verificar logs
docker-compose logs -f worker-cpj-api
```

**Logs esperados**:
```
🚀 Iniciando CPJAPIWorker...
✅ Worker configurado em modo orquestrador (Gateway)
🔍 CPJAPIWorker iniciado - 22 tópicos CPJ-3C
✅ Worker iniciado - Monitorando 22 tópicos
```

### Opção 2: Deploy Completo (Todos os Workers)

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Subir todos os workers
docker-compose up -d

# Verificar status
docker-compose ps
```

### Opção 3: Deploy com Makefile

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Deploy local
make local-up

# Ou deploy produção
make deploy
```

---

## ✅ Verificação

### 1. Verificar se Container está Rodando

```bash
docker ps | grep worker-cpj-api
```

**Saída esperada**:
```
CONTAINER ID   IMAGE                     STATUS         PORTS
abc123def456   worker-cpj-api:latest    Up 10 seconds  8004/tcp
```

### 2. Verificar Logs do Worker

```bash
docker logs -f worker-cpj-api
```

**Logs esperados**:
```
2025-11-05 10:00:00 - INFO - 🚀 Iniciando CPJAPIWorker...
2025-11-05 10:00:01 - INFO - ✅ Worker configurado em modo orquestrador (Gateway)
2025-11-05 10:00:01 - INFO - 🔍 CPJAPIWorker iniciado - 22 tópicos CPJ-3C
2025-11-05 10:00:02 - INFO - ✅ Worker iniciado - Monitorando 22 tópicos
2025-11-05 10:00:02 - INFO - Polling for external tasks...
```

### 3. Verificar Métricas Prometheus

```bash
curl http://localhost:8004/metrics
```

**Métricas esperadas**:
```
# HELP worker_tasks_completed_total Total tasks completed
# TYPE worker_tasks_completed_total counter
worker_tasks_completed_total{worker_id="cpj-api-worker"} 0

# HELP worker_tasks_failed_total Total tasks failed
# TYPE worker_tasks_failed_total counter
worker_tasks_failed_total{worker_id="cpj-api-worker"} 0
```

### 4. Verificar Conexão com Gateway

```bash
docker exec worker-cpj-api python -c "
import requests
response = requests.get('http://gateway:8000/health', timeout=5)
print(f'Gateway Status: {response.status_code}')
"
```

**Saída esperada**:
```
Gateway Status: 200
```

### 5. Verificar Tópicos Ativos no Camunda

Acesse o Camunda Cockpit:
```
http://localhost:8080/camunda
Usuario: demo
Senha: demo
```

Navegue para: **Cockpit → External Tasks**

**Tópicos esperados** (22 tópicos CPJ):
- cpj_login
- cpj_refresh_token
- cpj_buscar_publicacoes_nao_vinculadas
- cpj_atualizar_publicacao
- cpj_consultar_pessoa
- cpj_cadastrar_pessoa
- cpj_atualizar_pessoa
- cpj_consultar_processos
- cpj_cadastrar_processo
- cpj_atualizar_processo
- ... (12 tópicos restantes)

---

## 🧪 Teste Básico

### Teste 1: Consultar Pessoa via API Gateway

```bash
curl -X POST http://localhost:8000/cpj/pessoas/consultar \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "codigo": {"_eq": 1}
    },
    "sort": "nome"
  }'
```

**Resposta esperada**:
```json
{
  "success": true,
  "total": 1,
  "pessoas": [...]
}
```

### Teste 2: Criar Process Instance no Camunda

```bash
curl -X POST http://localhost:8080/engine-rest/process-definition/key/cpj_consultar_pessoa/start \
  -H "Content-Type: application/json" \
  -u demo:demo \
  -d '{
    "variables": {
      "filter": {
        "value": "{\"codigo\": {\"_eq\": 1}}",
        "type": "Json"
      }
    }
  }'
```

### Teste 3: Verificar Task Processada

```bash
# Verificar logs do worker
docker logs worker-cpj-api | grep "consultar_pessoa"
```

**Log esperado**:
```
🔍 Consultando pessoas - filtros: ['codigo']
📤 Processando via Gateway
✅ Consulta pessoa CPJ concluída - 1 encontradas
```

---

## 📊 Monitoramento

### Métricas Disponíveis

**Endpoint**: `http://localhost:8004/metrics`

| Métrica | Descrição |
|---------|-----------|
| `worker_tasks_completed_total` | Total de tarefas completadas |
| `worker_tasks_failed_total` | Total de tarefas falhadas |
| `worker_active_tasks` | Tarefas ativas no momento |
| `worker_processing_time_seconds` | Tempo de processamento |

### Logs Estruturados

**Nível de Log**: `INFO` (configurável via `LOG_LEVEL`)

**Formato**:
```
timestamp - logger - level - message
```

**Localização**:
```bash
docker logs worker-cpj-api
docker logs -f worker-cpj-api  # Follow mode
```

---

## 🔧 Troubleshooting

### Problema 1: Worker Não Inicia

**Sintoma**: Container sai imediatamente após start

**Verificar**:
```bash
docker logs worker-cpj-api
```

**Soluções**:
1. Verificar se `CAMUNDA_URL` está correto no `env.gateway`
2. Verificar se Gateway está acessível
3. Verificar se rede Docker existe: `docker network ls | grep backend`

### Problema 2: Erro de Autenticação CPJ

**Sintoma**: Logs mostram "401 Unauthorized"

**Verificar**:
```bash
docker logs worker-cpj-api | grep "CPJ.*401"
```

**Soluções**:
1. Verificar credenciais no `env.gateway`
2. Verificar se usuário é tipo 3 (API) no CPJ
3. Verificar se CPJ_API_BASE_URL está correto

### Problema 3: Gateway Inacessível

**Sintoma**: Logs mostram "Connection refused" ou "Timeout"

**Verificar**:
```bash
docker exec worker-cpj-api ping gateway
```

**Soluções**:
1. Verificar se Gateway está rodando: `docker ps | grep gateway`
2. Verificar se está na mesma rede: `docker network inspect camunda-worker-api-gateway_backend`
3. Verificar `GATEWAY_URL` no `env.gateway`

### Problema 4: Tópicos Não Aparecem no Camunda

**Sintoma**: External tasks vazios no Cockpit

**Soluções**:
1. Verificar se worker conectou ao Camunda: `docker logs worker-cpj-api | grep "Polling"`
2. Verificar `CAMUNDA_URL` no `env.gateway`
3. Criar um processo BPMN com Service Task usando um dos 22 tópicos CPJ

---

## 🔄 Escalar Worker

### Escalar para 3 Instâncias

```bash
# Via docker-compose scale
docker-compose up -d --scale worker-cpj-api=3

# Via variável de ambiente
export WORKER_CPJ_API_REPLICAS=3
docker-compose up -d worker-cpj-api

# Verificar réplicas
docker ps | grep worker-cpj-api
```

### Produção com Docker Swarm

```bash
# Deploy com 3 réplicas
docker stack deploy -c docker-compose.swarm.yml workers

# Escalar dinamicamente
docker service scale workers_worker-cpj-api=5
```

---

## 🛑 Parar Worker

### Parar Worker Específico

```bash
docker-compose stop worker-cpj-api
```

### Parar e Remover

```bash
docker-compose down worker-cpj-api
```

### Remover Completamente

```bash
docker-compose down
docker rmi worker-cpj-api:latest
```

---

## 📚 Referências

- **Documentação Completa**: `IMPLEMENTACAO_CPJ_COMPLETA.md`
- **Tópicos Disponíveis**: Ver `common/config.py` linhas 157-192
- **Handlers**: Ver `cpj_api_worker/handlers/`
- **Routers Gateway**: Ver `camunda-worker-api-gateway/app/routers/cpj/`
- **Service CPJ**: Ver `camunda-worker-api-gateway/app/services/cpj_service.py`

---

## ✅ Checklist de Ativação

- [ ] Atualizar credenciais CPJ em `env.gateway`
- [ ] Atualizar credenciais CPJ em `.env.local` do Gateway
- [ ] Build do worker: `docker-compose build worker-cpj-api`
- [ ] Deploy do worker: `docker-compose up -d worker-cpj-api`
- [ ] Verificar logs: `docker logs -f worker-cpj-api`
- [ ] Verificar métricas: `curl http://localhost:8004/metrics`
- [ ] Verificar tópicos no Camunda Cockpit
- [ ] Teste básico: Consultar pessoa via Gateway
- [ ] Criar processo BPMN usando tópico CPJ
- [ ] Monitorar processamento da task

---

**Worker CPJ Pronto para Uso!** 🎉

Em caso de dúvidas, consulte os logs ou a documentação completa.
