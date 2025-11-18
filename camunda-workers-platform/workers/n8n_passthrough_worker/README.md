# N8n Passthrough Worker

Worker **ultra simples** que apenas repassa tasks do Camunda para n8n.

## 🎯 Filosofia

**Worker é BURRO, n8n é INTELIGENTE**

```
┌─────────────────────────────────────────┐
│ Camunda BPMN                            │
│ ServiceTask topic="buscar_publicacoes"  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ N8n Passthrough Worker (100 linhas)    │
│ - Recebe task                           │
│ - Extrai topic + variáveis              │
│ - POST para n8n com tudo                │
│ - Retorna o que n8n mandou              │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ n8n - Webhook Único                     │
│ /webhook/camunda-tasks                  │
│                                          │
│ ┌─────────────────────────────────────┐ │
│ │ Switch (baseado no topic)           │ │
│ │ ├─ buscar_publicacoes → DW LAW API  │ │
│ │ ├─ tratar_publicacao → MongoDB      │ │
│ │ ├─ nova_publicacao → Validate+Save  │ │
│ │ └─ classificar → ML API             │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## ✅ Vantagens

1. **Worker simples**: ~100 linhas, fácil de manter
2. **Lógica no n8n**: Toda inteligência visual
3. **1 único webhook**: Sem múltiplos endpoints
4. **Fácil modificar**: Mexe no n8n sem redeploy do worker
5. **Custo baixo**: 1 worker (~$5/mês) + n8n (~$10/mês) = $15/mês total

## 🚀 Como Usar

### 1. Variáveis de Ambiente

```bash
# Camunda
CAMUNDA_URL=https://camunda-diascosta.up.railway.app/engine-rest
CAMUNDA_USERNAME=admin
CAMUNDA_PASSWORD=xxx

# n8n Webhook (ÚNICO)
N8N_WEBHOOK_URL=https://n8n-diascosta.up.railway.app/webhook/camunda-tasks

# Worker Config
WORKER_ID=n8n-passthrough-worker
MAX_TASKS=5

# Topics (OPCIONAL)
# Se não especificar, worker escuta TODOS os topics automaticamente
CAMUNDA_TOPICS=buscar_publicacoes,tratar_publicacao,nova_publicacao,classificar_publicacao

# Ou deixe vazio para modo AUTO (recomendado)
# CAMUNDA_TOPICS=
```

### 2. Modo de Operação

**Modo AUTO (Recomendado)**:
```bash
# Não definir CAMUNDA_TOPICS ou deixar vazio
# Worker registra handlers para topics conhecidos
# Se adicionar novo topic no BPMN, adicione na lista known_topics no código
```

**Modo EXPLÍCITO**:
```bash
# Definir CAMUNDA_TOPICS com lista separada por vírgula
CAMUNDA_TOPICS=topic1,topic2,topic3
# Worker só escuta os topics especificados
```

### 3. Executar Worker

```bash
pip install -r requirements.txt
python main.py
```

**Saída esperada**:
```
🚀 N8n Passthrough Worker iniciado
📡 n8n Webhook: http://localhost:5678/webhook/camunda-tasks
📋 Topics registrados: ['buscar_publicacoes', 'tratar_publicacao', 'nova_publicacao', 'classificar_publicacao']
✅ Subscribed to all topics: ['buscar_publicacoes', 'tratar_publicacao', 'nova_publicacao', 'classificar_publicacao']
```

## 🔧 Configurar n8n

### Criar Workflow Único

1. **Webhook Node**:
   - Method: POST
   - Path: `/webhook/camunda-tasks`
   - Response Mode: Last Node

2. **Switch Node** (roteamento por topic):
   ```
   Condition 1: {{ $json.topic === 'buscar_publicacoes' }}
   Condition 2: {{ $json.topic === 'tratar_publicacao' }}
   Condition 3: {{ $json.topic === 'nova_publicacao' }}
   Condition 4: {{ $json.topic === 'classificar_publicacao' }}
   ```

3. **Sub-workflows** para cada topic:

   **buscar_publicacoes**:
   ```
   HTTP Request → DW LAW API
     ↓
   Function → Processar IDs
     ↓
   MongoDB → Salvar
     ↓
   Respond → { "variables": { "publicacoes_ids": [...] } }
   ```

   **tratar_publicacao**:
   ```
   MongoDB → Buscar publicação
     ↓
   Function → Deduplica
     ↓
   Function → Classifica
     ↓
   MongoDB → Atualizar
     ↓
   Respond → { "variables": { "status": "processada" } }
   ```

### Payload Recebido no n8n

```json
{
  "topic": "buscar_publicacoes",
  "task_id": "abc123",
  "business_key": "lote-001",
  "variables": {
    "cod_grupo": 5,
    "limite_publicacoes": 100
  }
}
```

### Resposta do n8n

```json
{
  "variables": {
    "publicacoes_ids": ["pub-001", "pub-002"],
    "total_encontradas": 2,
    "lote_id": "lote-123"
  }
}
```

Worker pega `variables` e completa task no Camunda.

## 📦 Deploy no Railway

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copiar código comum
COPY workers/common /app/common

# Copiar worker
COPY workers/n8n_passthrough_worker /app/n8n_passthrough_worker

WORKDIR /app/n8n_passthrough_worker

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

### Variáveis no Railway

```bash
CAMUNDA_URL=https://camunda-diascosta.up.railway.app/engine-rest
CAMUNDA_USERNAME=admin
CAMUNDA_PASSWORD=xxx
N8N_WEBHOOK_URL=https://n8n-diascosta.up.railway.app/webhook/camunda-tasks
```

## 🧪 Testar Localmente

### Terminal 1: Mock n8n

```bash
cd workers/n8n_passthrough_worker
python mock_n8n.py
```

### Terminal 2: Worker

```bash
python main.py
```

### Terminal 3: Iniciar processo

```powershell
# Ver TESTE_LOCAL.md
```

## 📊 Comparação de Abordagens

| Aspecto | Worker Monolítico | Micro Gateway + Functions | **n8n Passthrough** |
|---------|------------------|--------------------------|---------------------|
| **Linhas de código** | 400+ | 200 + functions | **~100** |
| **Lógica** | Python | Functions Python | **n8n visual** |
| **Endpoints** | N/A | 4+ functions | **1 webhook** |
| **Deploy** | 1 worker | 1 gateway + 4+ services | **1 worker + n8n** |
| **Custo** | $5/mês | $22/mês | **$15/mês** |
| **Modificar lógica** | Redeploy | Redeploy function | **Mexe no n8n** |
| **Complexidade** | Média | Alta | **Baixa** |

## 🎯 Quando Usar

### ✅ Use n8n Passthrough se:
- Time prefere UI visual
- Workflows podem mudar frequentemente
- Quer simplicidade máxima no código
- Orçamento limitado
- **Quer adicionar novos topics sem redeploy do worker**

### ❌ Não use se:
- Lógica muito complexa para n8n
- Time prefere código Python puro
- Precisa de ML/processamento pesado
- Vendor lock-in é preocupação

## 🆕 Adicionar Novo Topic

### Sem Redeploy (se usar modo AUTO):

1. **Adicione topic na lista `known_topics` no código**:
```python
known_topics = [
    "buscar_publicacoes",
    "tratar_publicacao", 
    "nova_publicacao",
    "classificar_publicacao",
    "seu_novo_topic",  # ← Adicione aqui
]
```

2. **Redeploy o worker** (necessário apenas 1 vez)

3. **Configure no n8n**: Adicione novo case no Switch node

### Com Variável de Ambiente:

1. **Atualize CAMUNDA_TOPICS**:
```bash
CAMUNDA_TOPICS=topic1,topic2,seu_novo_topic
```

2. **Restart o worker**

3. **Configure no n8n**: Adicione novo case no Switch node

**Vantagem**: n8n não precisa redeploy, só o worker precisa conhecer o topic!

## 🔒 Segurança

Worker valida resposta do n8n:

```python
# n8n DEVE retornar {"variables": {...}}
if "variables" not in result:
    raise ValueError("n8n response inválido")
```

## 📈 Próximos Passos

1. ✅ Worker criado (~100 linhas)
2. ⏳ Deploy n8n no Railway
3. ⏳ Criar workflow no n8n com Switch
4. ⏳ Deploy worker no Railway
5. ⏳ Teste end-to-end

---

**Arquitetura final**: Simples, visual, econômica! 🎉
