# 🧹 Limpar e Rodar Gateway + Workers Localmente

**Situação**: Outras aplicações estão usando portas 8000 e 6379
**Solução**: Parar outros containers e rodar nosso projeto

---

## 🛑 PASSO 1: Parar Containers de Outros Projetos

```bash
# Parar Redis do outlawyer_api
docker stop outlawyer_api-redis-1

# Parar RabbitMQ do lops-rpa
docker stop lops-rpa-rabbitmq

# OU parar tudo que não é Camunda
docker stop $(docker ps -q --filter "name=outlawyer") 2>/dev/null || true
docker stop $(docker ps -q --filter "name=lops") 2>/dev/null || true
docker stop $(docker ps -q --filter "name=portal-rpa") 2>/dev/null || true
docker stop $(docker ps -q --filter "name=rpa-worker") 2>/dev/null || true
```

---

## ✅ PASSO 2: Verificar Portas Livres

```bash
lsof -i :8000
lsof -i :6379
lsof -i :5672

# Se alguma porta ainda estiver em uso, matar o processo:
# kill -9 <PID>
```

---

## 🚀 PASSO 3: Iniciar Gateway

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway

# Limpar containers antigos deste projeto
docker compose down -v

# Build
docker compose build

# Iniciar com perfil local-services (inclui MongoDB, RabbitMQ, Redis)
docker compose --profile local-services up -d

# Ver logs
docker compose logs -f gateway
```

**Aguardar mensagem**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ MongoDB connected
✅ Worker API Gateway started on port 8000
```

**Parar logs**: `Ctrl+C`

---

## 🔧 PASSO 4: Verificar Gateway

```bash
# Health check
curl http://localhost:8000/health

# Deve retornar:
# {"status":"healthy","service":"Worker API Gateway",...}

# Ver Swagger
open http://localhost:8000/docs
```

---

## 👷 PASSO 5: Iniciar Workers

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Limpar containers antigos
docker compose down -v

# Build
docker compose build

# Iniciar todos os workers
docker compose up -d

# Ver status
docker ps | grep worker
```

**Esperado ver**:
```
worker-dw-law               Up X seconds
worker-publicacao-unified   Up X seconds
worker-cpj-api              Up X seconds
```

---

## 🔍 PASSO 6: Verificar Workers

### Worker DW LAW
```bash
# Ver logs
docker logs worker-dw-law --tail=50

# Health
curl http://localhost:8010/health

# Métricas
curl http://localhost:8010/metrics | head -20
```

### Worker Publicacao
```bash
docker logs worker-publicacao-unified --tail=30
curl http://localhost:8003/metrics | head -20
```

### Worker CPJ
```bash
docker logs worker-cpj-api --tail=30
curl http://localhost:8004/metrics | head -20
```

---

## 🧪 PASSO 7: Testar DW LAW

### Teste 1: Conexão
```bash
curl http://localhost:8000/dw-law/test-connection | jq .
```

### Teste 2: Inserir Processo
```bash
curl -X POST 'http://localhost:8000/dw-law/inserir-processos' \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_projeto": "diascostacitacaoconsultaunica",
    "processos": [{
      "numero_processo": "0012205-60.2015.5.15.0077",
      "other_info_client1": "TESTE_LOCAL_COMPLETO"
    }],
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
    "processos": [{
      "numero_processo": "0012205-60.2015.5.15.0077",
      "chave_de_pesquisa": "UUID-GERADO",
      "tribunal": "TJPB",
      "sistema": "PJE",
      "instancia": "1"
    }]
  }
}
```

### Teste 3: Consultar Processo
```bash
# Usar chave_de_pesquisa do teste anterior
curl -X POST 'http://localhost:8000/dw-law/consultar-processo' \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_de_pesquisa": "COLE-A-CHAVE-AQUI"
  }' | jq .
```

---

## 📊 Monitoramento

### Containers Ativos
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Logs em Tempo Real
```bash
# Gateway
docker logs -f camunda-worker-api-gateway-gateway-1

# Worker DW LAW
docker logs -f worker-dw-law

# Todos
docker compose -f /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway/docker-compose.yml logs -f
```

### RabbitMQ Management
```bash
open http://localhost:15672
# Login: admin / admin123
```

---

## 🛑 Parar Tudo

```bash
# Parar Gateway + Serviços
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway
docker compose --profile local-services down

# Parar Workers
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform
docker compose down
```

---

## 🔄 Reiniciar Tudo

```bash
# Gateway
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway
docker compose --profile local-services restart

# Workers
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform
docker compose restart
```

---

## ✅ Resumo dos Comandos

```bash
# 1. Limpar ambiente
docker stop outlawyer_api-redis-1 lops-rpa-rabbitmq

# 2. Gateway
cd camunda-worker-api-gateway
docker compose --profile local-services up -d

# 3. Workers
cd ../camunda-workers-platform
docker compose up -d

# 4. Verificar
docker ps
curl http://localhost:8000/health
curl http://localhost:8010/health

# 5. Testar DW LAW
curl http://localhost:8000/dw-law/test-connection | jq .
```

---

**✅ Ambiente local pronto em 5 minutos!**
