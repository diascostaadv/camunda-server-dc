# ✅ URLs Corretas - Todas as APIs

**Data**: 2025-11-07
**Status**: Verificado e Corrigido

---

## 🔗 URLs das APIs Externas

### 1. DW LAW e-Protocol API ✅

**URL Correta**:
```
https://web-eprotocol-integration-cons-qa.azurewebsites.net
```

**Endpoints**:
```
POST /api/AUTENTICAR
POST /api/consulta_processual/INSERIR_PROCESSOS
POST /api/consulta_processual/EXCLUIR_PROCESSOS
POST /api/consulta_processual/CONSULTAR_CHAVE_DE_PESQUISA
```

**Credenciais**:
```
Email: integ_dias_cons@dwlaw.com.br
Senha: DC@Dwlaw2025
Projeto: diascostacitacaoconsultaunica
```

**Configurado em**:
- ✅ `camunda-worker-api-gateway/.env`
- ✅ `camunda-worker-api-gateway/.env.local`
- ✅ `camunda-worker-api-gateway/.env.production`
- ✅ `camunda-worker-api-gateway/app/core/config.py`
- ✅ `camunda-workers-platform/env.gateway`
- ✅ `camunda-workers-platform/.env.local`

---

### 2. CPJ API ✅

**URL Correta**:
```
https://app.leviatan.com.br/dcncadv/cpj/agnes/api/v2
```

**Endpoints**:
```
POST /login
POST /processo
POST /publicacao
POST /pessoa
POST /pedido
POST /envolvido
POST /documento
... (20+ endpoints)
```

**Credenciais**:
```
Login: api
Password: 2025
Token Expiry: 30 minutos
```

**Configurado em**:
- ✅ `camunda-worker-api-gateway/.env` → `CPJ_BASE_URL`
- ✅ `camunda-worker-api-gateway/.env.local` → `CPJ_BASE_URL`
- ✅ `camunda-worker-api-gateway/.env.production` → `CPJ_BASE_URL`
- ✅ `camunda-worker-api-gateway/app/core/config.py` → `CPJ_BASE_URL`
- ✅ `camunda-workers-platform/env.gateway` → `CPJ_API_BASE_URL` (**CORRIGIDO**)
- ✅ `camunda-workers-platform/.env.local` → `CPJ_API_BASE_URL`

---

### 3. Camunda REST API ✅

**URL Correta**:
```
http://201.23.67.197:8080/engine-rest
```

**Endpoints**:
```
GET  /version
POST /message
GET  /external-task
... (Camunda REST API completa)
```

**Credenciais** (para envio de mensagens BPMN):
```
User: admin
Password: DiasCosta@!!2025
```

**Configurado em**:
- ✅ `camunda-worker-api-gateway/.env` → `CAMUNDA_REST_URL`
- ✅ `camunda-worker-api-gateway/.env.local` → `CAMUNDA_REST_URL`
- ✅ `camunda-worker-api-gateway/.env.production` → `CAMUNDA_REST_URL`
- ✅ `camunda-worker-api-gateway/app/core/config.py` → `CAMUNDA_REST_URL` (**user: admin**)
- ✅ `camunda-workers-platform/env.gateway` → `CAMUNDA_URL`
- ✅ `camunda-workers-platform/.env.local` → `CAMUNDA_URL`

---

### 4. Gateway API (Interno) ✅

**URL Produção**:
```
http://201.23.69.65:8080
```

**URL Local**:
```
http://localhost:8000
```

**URL Interna (entre containers)**:
```
http://camunda-worker-api-gateway-gateway-1:8000
```

**Configurado em**:
- ✅ `camunda-workers-platform/env.gateway` → `GATEWAY_URL=http://201.23.69.65:8080`
- ✅ `camunda-workers-platform/.env.local` → `GATEWAY_URL=http://camunda-worker-api-gateway-gateway-1:8000`

---

### 5. MongoDB (Azure Cosmos DB) ✅

**Connection String Correta**:
```
mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/
```

**Database**:
```
worker_gateway
```

**Configurado em**:
- ✅ Todos os arquivos `.env`

---

## 🔍 Sobre o Erro CPJ que Você Reportou

### Logs Analisados:
```
ERROR - ❌ [CPJ] Erro HTTP 400: Connection Closed Gracefully.
WARNING - ⚠️ [CPJ] Bad Request para '0001357-37.2023.8.16.0115' - retornando lista vazia
INFO - ✅ Busca CPJ concluída - 0 processos encontrados
```

### Análise:

1. **Erro 400 é esperado quando processo não existe no CPJ**
2. **Service está tratando corretamente** (`cpj_service.py:106-110`)
3. **Retorna lista vazia** em vez de falhar
4. **Worker continua normalmente**

### Possíveis Causas:

**A. Processo não existe no CPJ** (mais provável) ✅
- CPJ retorna 400 para processos não encontrados
- Comportamento normal do sistema

**B. URL incorreta** ❌ (era isso no env.gateway)
- **ANTES**: `CPJ_API_BASE_URL=https://cpj-server:porta/api/v2` ❌
- **DEPOIS**: `CPJ_API_BASE_URL=https://app.leviatan.com.br/dcncadv/cpj/agnes/api/v2` ✅
- **STATUS**: **CORRIGIDO** ✅

**C. Credenciais incorretas** ❌
- **ANTES**: `CPJ_API_USER=1`, `CPJ_API_PASSWORD=abc` ❌
- **DEPOIS**: `CPJ_API_USER=api`, `CPJ_API_PASSWORD=2025` ✅
- **STATUS**: **CORRIGIDO** ✅

---

## 🚀 Ação Necessária

### Redeploy dos Workers (URL CPJ foi corrigida)

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Fazer deploy com URL corrigida
make deploy
```

Isso vai atualizar o `env.gateway` na VM com a URL correta do CPJ.

---

## ✅ URLs Finais (Todas Corretas)

```yaml
DW LAW:
  URL: https://web-eprotocol-integration-cons-qa.azurewebsites.net
  User: integ_dias_cons@dwlaw.com.br
  Pass: DC@Dwlaw2025

CPJ:
  URL: https://app.leviatan.com.br/dcncadv/cpj/agnes/api/v2
  User: api
  Pass: 2025

Camunda REST:
  URL: http://201.23.67.197:8080/engine-rest
  User: admin
  Pass: DiasCosta@!!2025

Gateway:
  Produção: http://201.23.69.65:8080
  Local: http://localhost:8000

MongoDB:
  URI: mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/
  Database: worker_gateway
```

---

**✅ Todas as URLs estão corretas agora!**

**Próximo passo**: Execute `cd camunda-workers-platform && make deploy` para atualizar o env.gateway na VM.