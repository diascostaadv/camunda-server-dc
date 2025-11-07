# 🚀 Início Rápido: Rodar Localmente

**Objetivo**: Rodar Gateway + Workers (incluindo DW LAW) na sua máquina local
**Tempo**: 10-15 minutos
**Data**: 2025-11-07

---

## ⚡ Opção 1: Script Automatizado (MAIS FÁCIL)

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc

# Executar script
./rodar-local.sh
```

**O script faz tudo automaticamente**:
1. ✅ Verifica Docker rodando
2. ✅ Verifica portas disponíveis
3. ✅ Build do Gateway
4. ✅ Inicia Gateway + MongoDB + RabbitMQ + Redis
5. ✅ Build dos Workers
6. ✅ Inicia todos os Workers (incluindo DW LAW)
7. ✅ Aguarda inicialização
8. ✅ Testa health checks
9. ✅ Testa conexão DW LAW
10. ✅ Mostra resumo com URLs

**Depois de executar, vá direto para "Testes"** (pular Opção 2)

---

## 📝 Opção 2: Manual (Passo a Passo)

### Passo 1: Iniciar Gateway

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway

# Build
docker compose build

# Iniciar Gateway + MongoDB + RabbitMQ + Redis
docker compose --profile local-services up -d

# Ver logs
docker compose logs -f gateway
```

**Aguardar até ver**:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ MongoDB connected
```

### Passo 2: Iniciar Workers

```bash
# Em outro terminal
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Build
docker compose build

# Iniciar todos os workers
docker compose up -d

# Ver logs do DW LAW worker
docker logs -f worker-dw-law
```

**Aguardar até ver**:
```
✅ Worker configurado em modo orquestrador (Gateway)
🔍 DWLawWorker iniciado - aguardando tarefas nos tópicos:
  • INSERIR_PROCESSOS_DW_LAW - Inserir processos
  • EXCLUIR_PROCESSOS_DW_LAW - Excluir processos
  • CONSULTAR_PROCESSO_DW_LAW - Consultar processo
🚀 Worker ready and waiting for external tasks...
```

---

## ✅ Verificações Rápidas

### 1. Gateway
```bash
curl http://localhost:8000/health
# Esperado: {"status":"healthy",...}
```

### 2. Swagger UI
```bash
open http://localhost:8000/docs
```

### 3. Worker DW LAW
```bash
curl http://localhost:8010/health
# Esperado: {"status":"healthy","worker":"dw-law-worker",...}
```

### 4. RabbitMQ Management
```bash
open http://localhost:15672
# Login: admin / admin123
```

### 5. Containers Rodando
```bash
docker ps

# Esperado ver:
# - camunda-worker-api-gateway-gateway-1     :8000, :9000
# - camunda-worker-api-gateway-rabbitmq-1    :5672, :15672
# - camunda-worker-api-gateway-redis-1       :6379
# - worker-dw-law                            :8010
# - worker-publicacao-unified                :8003
# - worker-cpj-api                           :8004
```

---

## 🧪 Testes

### Teste 1: Conexão DW LAW
```bash
curl http://localhost:8000/dw-law/test-connection | jq .
```

**Esperado**:
```json
{
  "success": true,
  "dw_law": {
    "authenticated": true,
    "usuario": "integ_dias_cons@dwlaw.com.br",
    "is_valid": true
  },
  "camunda": {
    "success": true,
    "version": {"version": "7.21.0"}
  }
}
```

### Teste 2: Inserir Processo
```bash
curl -X POST 'http://localhost:8000/dw-law/inserir-processos' \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_projeto": "diascostacitacaoconsultaunica",
    "processos": [{
      "numero_processo": "0012205-60.2015.5.15.0077",
      "other_info_client1": "TESTE_LOCAL"
    }],
    "camunda_business_key": "teste-local-001"
  }' | jq .
```

### Teste 3: Verificar MongoDB
```bash
mongosh "mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/worker_gateway"

# Ver processos inseridos
db.dw_law_processos.find({chave_projeto: "diascostacitacaoconsultaunica"}).pretty()
```

### Teste 4: Verificar Camunda
```bash
open http://201.23.67.197:8080/camunda/app/cockpit
# Login: demo / DiasCostaA!!2025

# Navegar: External Tasks
# Verificar: INSERIR_PROCESSOS_DW_LAW aparece na lista
```

---

## 📊 URLs Importantes

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Gateway API** | http://localhost:8000 | - |
| **Swagger Docs** | http://localhost:8000/docs | - |
| **Worker DW LAW** | http://localhost:8010 | - |
| **RabbitMQ Mgmt** | http://localhost:15672 | admin / admin123 |
| **Camunda Cockpit** | http://201.23.67.197:8080/camunda | demo / DiasCostaA!!2025 |

---

## 🛑 Parar Tudo

```bash
# Parar Gateway
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway
docker compose down

# Parar Workers
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform
docker compose down
```

---

## 🔄 Reiniciar

```bash
# Reiniciar apenas Gateway
cd camunda-worker-api-gateway
docker compose restart gateway

# Reiniciar apenas Worker DW LAW
cd camunda-workers-platform
docker compose restart worker-dw-law
```

---

## 📝 Ver Logs

```bash
# Gateway
docker logs -f camunda-worker-api-gateway-gateway-1

# Worker DW LAW
docker logs -f worker-dw-law

# Worker Publicacao
docker logs -f worker-publicacao-unified

# Worker CPJ
docker logs -f worker-cpj-api

# RabbitMQ
docker logs -f camunda-worker-api-gateway-rabbitmq-1

# Todos
docker compose -f camunda-worker-api-gateway/docker-compose.yml logs -f
docker compose -f camunda-workers-platform/docker-compose.yml logs -f
```

---

## 🆘 Problemas Comuns

### "Port already in use"
```bash
# Descobrir o que está usando a porta
lsof -i :8000

# Parar processo
kill -9 <PID>

# OU mudar porta no .env.local
PORT=8001
```

### "Docker not running"
```bash
# Abrir Docker Desktop
open -a Docker

# Aguardar inicializar
```

### Gateway não responde
```bash
# Ver logs
docker logs camunda-worker-api-gateway-gateway-1 --tail=100

# Verificar se RabbitMQ e Redis estão OK
docker ps | grep -E "(rabbitmq|redis)"

# Rebuild
docker compose build --no-cache gateway
docker compose up -d gateway
```

### Worker não conecta ao Gateway
```bash
# Verificar URL do Gateway
docker exec worker-dw-law env | grep GATEWAY_URL

# Deve ser: http://camunda-worker-api-gateway-gateway-1:8000

# Testar conectividade
docker exec worker-dw-law curl http://camunda-worker-api-gateway-gateway-1:8000/health
```

---

## ✅ Checklist de Sucesso

- [ ] Docker Desktop rodando
- [ ] Script `./rodar-local.sh` executado com sucesso
- [ ] Gateway em http://localhost:8000/health retorna OK
- [ ] Worker DW LAW em http://localhost:8010/health retorna OK
- [ ] RabbitMQ em http://localhost:15672 acessível
- [ ] `/dw-law/test-connection` retorna sucesso
- [ ] Teste de inserção de processo funciona
- [ ] Tópicos DW LAW aparecem no Camunda Cockpit
- [ ] Logs sem erros críticos

---

## 🎯 Após Validar Local

Quando tudo estiver funcionando:
1. ✅ Commit das alterações
2. 🚀 Deploy em produção (VM 201.23.69.65)
3. 📧 Solicitar configuração de callback ao DW LAW
4. 🧪 Testar fluxo end-to-end completo

---

**✅ Pronto para rodar! Execute `./rodar-local.sh` e comece a testar!**
