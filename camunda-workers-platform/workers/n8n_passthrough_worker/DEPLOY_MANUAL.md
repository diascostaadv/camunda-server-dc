# Deploy Manual no Railway Dashboard

Como o Railway CLI está com problemas, vamos fazer via Dashboard (mais simples):

## 🚀 Passo a Passo

### 1. Acesse Railway Dashboard
```
https://railway.app/dashboard
```

### 2. Selecione seu Projeto
- Clique no projeto: `camunda-server-dc` (ou o nome do seu projeto)

### 3. Criar Novo Serviço

1. Clique em **"+ New"**
2. Selecione **"GitHub Repo"**
3. Selecione o repositório do projeto
4. Railway vai mostrar: "Deploy now?"
5. **NÃO clique em Deploy ainda!**

### 4. Configurar Root Directory

Antes de fazer deploy:

1. Clique em **"Settings"** (ícone de engrenagem)
2. Em **"Root Directory"**, coloque:
   ```
   camunda-workers-platform
   ```
3. Em **"Dockerfile Path"**, coloque:
   ```
   workers/n8n_passthrough_worker/Dockerfile
   ```
4. Em **"Service Name"**, coloque:
   ```
   n8n-passthrough-worker
   ```

### 5. Configurar Variáveis de Ambiente

1. Clique em **"Variables"** (aba superior)
2. Adicione as seguintes variáveis:

```
CAMUNDA_URL=https://camunda-diascosta.up.railway.app/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=demo

N8N_WEBHOOK_URL=https://seu-n8n.up.railway.app/webhook/camunda-tasks
N8N_WEBHOOK_URL_TEST=https://seu-n8n.up.railway.app/webhook-test/camunda-tasks

WORKER_ID=n8n-passthrough-worker
MAX_TASKS=5
LOG_LEVEL=INFO
METRICS_PORT=8000

GATEWAY_ENABLED=false
```

**Importante**: Substitua as URLs corretas do seu Camunda e n8n!

### 6. Deploy

1. Volte para aba **"Deployments"**
2. Clique em **"Deploy"**
3. Railway vai:
   - Detectar Dockerfile
   - Build da imagem
   - Deploy do container

### 7. Verificar Logs

1. Clique em **"View Logs"**
2. Procure por:
   ```
   🚀 N8n Passthrough Worker iniciado
   📡 n8n Webhook: https://...
   📋 Topics registrados: [...]
   ✅ Subscribed to all topics
   ```

### 8. Testar

Execute um processo no Camunda e veja os logs do worker!

## 🔍 Troubleshooting

### Build falha - "common not found"

**Causa**: Dockerfile tenta copiar `workers/common` mas não encontra

**Solução**: 
1. Verifique se a pasta `workers/common` existe no repo
2. Se não, copie do projeto original:
   ```powershell
   cp -r c:\www\camunda-server-dc\camunda-workers-platform\workers\common c:\www\seu-repo\workers\
   ```

### Worker conecta mas não processa tasks

**Causa**: Topics não registrados

**Solução**: Verifique logs - deve mostrar:
```
📋 Topics registrados: ['buscar_publicacoes', ...]
```

Se não aparecer, verifique o código em `main.py` linha ~60.

### n8n não recebe requests

**Causa**: URL errada ou n8n não configurado

**Solução**:
1. Teste o webhook manualmente:
   ```powershell
   $body = @{ topic = "test" } | ConvertTo-Json
   Invoke-RestMethod -Uri "https://seu-n8n.up.railway.app/webhook/camunda-tasks" -Method POST -Body $body -ContentType "application/json"
   ```
2. Se der 404, configure o webhook no n8n primeiro

## 📊 Status do Deploy

✅ Dockerfile criado
✅ railway.json configurado
✅ Worker pronto para deploy
⏳ Aguardando deploy manual via Dashboard

---

**Alternativa**: Se preferir CLI, primeiro faça `railway link` no projeto correto!
