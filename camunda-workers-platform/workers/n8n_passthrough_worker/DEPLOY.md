# Deploy n8n Passthrough Worker no Railway

## 📋 Pré-requisitos

1. ✅ Camunda rodando: `https://camunda-diascosta.up.railway.app`
2. ✅ n8n rodando com webhook: `/webhook/camunda-tasks`
3. ✅ Railway CLI instalado

## 🚀 Deploy via Railway CLI

### 1. Login no Railway

```powershell
railway login
```

### 2. Navegar para o projeto

```powershell
cd c:\www\camunda-server-dc\camunda-workers-platform
```

### 3. Link ao projeto Railway

```powershell
# Se ainda não linkado
railway link

# Escolha o projeto: camunda-server-dc
```

### 4. Criar novo serviço

```powershell
# Criar serviço para o worker
railway service create n8n-passthrough-worker
```

### 5. Configurar variáveis de ambiente

```powershell
# Camunda
railway variables set CAMUNDA_URL=https://camunda-diascosta.up.railway.app/engine-rest
railway variables set CAMUNDA_USERNAME=admin
railway variables set CAMUNDA_PASSWORD=sua_senha_aqui

# n8n Webhook
railway variables set N8N_WEBHOOK_URL=https://n8n-diascosta.up.railway.app/webhook/camunda-tasks

# Worker Config
railway variables set WORKER_ID=n8n-passthrough-worker
railway variables set MAX_TASKS=5
railway variables set LOG_LEVEL=INFO
railway variables set METRICS_PORT=8000

# Topics (opcional - modo AUTO)
# railway variables set CAMUNDA_TOPICS=buscar_publicacoes,tratar_publicacao,nova_publicacao,classificar_publicacao

# Disable Gateway
railway variables set GATEWAY_ENABLED=false
```

### 6. Deploy

```powershell
# Deploy do worker
railway up --service n8n-passthrough-worker
```

### 7. Verificar logs

```powershell
railway logs --service n8n-passthrough-worker
```

**Logs esperados**:
```
🚀 N8n Passthrough Worker iniciado
📡 n8n Webhook: https://n8n-diascosta.up.railway.app/webhook/camunda-tasks
📋 Topics registrados: ['buscar_publicacoes', 'tratar_publicacao', 'nova_publicacao', 'classificar_publicacao']
✅ Subscribed to all topics: ['buscar_publicacoes', 'tratar_publicacao', 'nova_publicacao', 'classificar_publicacao']
Started Prometheus metrics server on port 8000
Starting worker n8n-passthrough-worker
```

## 🔧 Deploy via GitHub (Alternativa)

### 1. Push para GitHub

```powershell
git add workers/n8n_passthrough_worker
git commit -m "Add n8n passthrough worker"
git push
```

### 2. Configurar no Railway Dashboard

1. Acesse: https://railway.app
2. Selecione projeto: `camunda-server-dc`
3. **New Service** → **GitHub Repo**
4. Selecione o repositório
5. **Settings**:
   - **Root Directory**: `camunda-workers-platform`
   - **Dockerfile Path**: `workers/n8n_passthrough_worker/Dockerfile`
   - **Service Name**: `n8n-passthrough-worker`

6. **Variables**: Adicione as mesmas variáveis do método CLI

7. **Deploy**: Railway detecta Dockerfile e faz deploy automático

## 📊 Verificar Status

### Health Check

```powershell
# Metrics endpoint (Prometheus)
curl https://n8n-passthrough-worker-production.up.railway.app/metrics
```

### Testar Workflow

1. **Iniciar processo no Camunda**:

```powershell
$body = @{
    businessKey = "teste-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    variables = @{
        cod_grupo = @{
            value = 5
            type = "Integer"
        }
        limite_publicacoes = @{
            value = 10
            type = "Integer"
        }
    }
} | ConvertTo-Json -Depth 10

$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:sua_senha"))
}

Invoke-RestMethod -Uri "https://camunda-diascosta.up.railway.app/engine-rest/process-definition/key/Fluxo_busca_publicacoes_lote/start" -Method POST -Headers $headers -Body $body
```

2. **Verificar logs do worker**:

```powershell
railway logs --service n8n-passthrough-worker --tail 50
```

3. **Verificar logs do n8n**:

```powershell
railway logs --service n8n
```

## 🔍 Troubleshooting

### Worker não conecta ao Camunda

**Problema**: `Connection refused` ou `timeout`

**Solução**:
```powershell
# Verificar CAMUNDA_URL
railway variables get CAMUNDA_URL

# Testar conexão
curl https://camunda-diascosta.up.railway.app/engine-rest/version
```

### n8n não recebe requests

**Problema**: Worker envia mas n8n não recebe

**Solução**:
```powershell
# Verificar N8N_WEBHOOK_URL
railway variables get N8N_WEBHOOK_URL

# Testar webhook manualmente
$body = @{
    topic = "buscar_publicacoes"
    task_id = "test-123"
    variables = @{
        cod_grupo = 5
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://n8n-diascosta.up.railway.app/webhook/camunda-tasks" -Method POST -Body $body -ContentType "application/json"
```

### Worker não pega tasks

**Problema**: Worker conectado mas não processa tasks

**Solução**:
```powershell
# Verificar topics registrados nos logs
railway logs --service n8n-passthrough-worker | Select-String "Topics registrados"

# Verificar tasks pendentes no Camunda
curl "https://camunda-diascosta.up.railway.app/engine-rest/external-task?topicName=buscar_publicacoes"
```

### Timeout no n8n

**Problema**: `n8n timeout para topic X`

**Solução**: Aumentar timeout no código ou verificar workflow n8n
```python
# Em main.py, linha do timeout:
timeout=180,  # 3 minutos (ajustar se necessário)
```

## 💰 Custo Estimado

- **Worker**: ~$5/mês (Railway Hobby Plan)
- **n8n**: ~$10/mês (se self-hosted no Railway)
- **Camunda**: ~$10/mês (já deployado)

**Total**: ~$25/mês para stack completa

## 📈 Próximos Passos

1. ✅ Worker deployado
2. ⏳ Configurar workflow no n8n
3. ⏳ Testar end-to-end com processo real
4. ⏳ Configurar alertas de erro
5. ⏳ Documentar workflows n8n

---

**Status**: Worker pronto para deploy! 🚀
