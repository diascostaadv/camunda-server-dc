# ✅ Marcação Automática com Auditoria Completa

## 📋 Visão Geral

Sistema implementado para marcar publicações como "exportadas" na Webjur **imediatamente após salvar no MongoDB**, com log completo de auditoria incluindo:

- ✅ Todas as tentativas de marcação
- ✅ Timestamps detalhados
- ✅ Duração de cada operação
- ✅ Mensagens de erro
- ✅ Snapshot dos dados da publicação
- ✅ Contexto de execução (lote_id, execução_id, etc.)

---

## 🔄 Fluxo Completo

```
┌──────────────────────────────────────────────────────────────┐
│ 1. BUSCA SOAP (Webjur API)                                  │
├──────────────────────────────────────────────────────────────┤
│ • GET /buscar-publicacoes/processar-task-v2                 │
│ • Busca publicações não exportadas                          │
│ • Retorna: 1821 publicações                                 │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. SALVAR NO MONGODB (Bronze - Chunking)                    │
├──────────────────────────────────────────────────────────────┤
│ • LoteService._salvar_publicacoes_bronze()                  │
│ • Processa em chunks de 200 publicações                     │
│ • Status inicial: "nova"                                     │
│ • Chunk 1/10: 200 salvas                                     │
│ • Chunk 2/10: 200 salvas                                     │
│ • ...                                                        │
│ • Chunk 10/10: 21 salvas                                     │
│ • Total: 1821 publicações bronze salvas                      │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. MARCAÇÃO AUTOMÁTICA (NOVO!)                              │
├──────────────────────────────────────────────────────────────┤
│ A. Criar Logs de Auditoria                                  │
│    • Para cada publicação: iniciar_log_marcacao()           │
│    • Salva snapshot dos dados                               │
│    • Status: PENDENTE                                        │
│                                                              │
│ B. Marcar em Lote no Webjur                                 │
│    • intimation_service.set_publicacoes([...1821])          │
│    • Formato: "cod1|cod2|...|cod1821|"                      │
│    • API Webjur marca como exportadas                       │
│                                                              │
│ C. Atualizar MongoDB (Bulk Write)                           │
│    • marcada_exportada_webjur: True                         │
│    • timestamp_marcacao_exportada: now()                    │
│    • marcacao_automatica: True                              │
│    • 1821 documentos atualizados                            │
│                                                              │
│ D. Registrar Sucesso nos Logs                               │
│    • Para cada publicação: marcar_como_sucesso()            │
│    • Status: SUCESSO                                         │
│    • Duração registrada                                      │
│    • Detalhes da marcação em lote                           │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. PRÓXIMA BUSCA (Evita Duplicatas)                         │
├──────────────────────────────────────────────────────────────┤
│ • apenas_nao_exportadas=true                                │
│ • Webjur NÃO retorna publicações marcadas                   │
│ • Resultado: 0 duplicatas                                    │
│ • Histórico completo preservado em logs_marcacao_publicacoes│
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Estrutura de Dados

### Coleção: `publicacoes_bronze`

```json
{
  "_id": ObjectId("..."),
  "cod_publicacao": 123456,
  "numero_processo": "0000000-00.0000.0.00.0000",
  "texto_publicacao": "...",
  "lote_id": "690e26a5cb8287c0f1a180c3",
  "status": "nova",

  // CAMPOS DE MARCAÇÃO
  "marcada_exportada_webjur": true,
  "timestamp_marcacao_exportada": ISODate("2025-11-07T20:30:45.123Z"),
  "marcacao_automatica": true,

  "timestamp_insercao": ISODate("2025-11-07T20:30:15.000Z")
}
```

### Coleção: `logs_marcacao_publicacoes` (NOVA!)

```json
{
  "_id": ObjectId("..."),

  // IDENTIFICAÇÃO
  "cod_publicacao": 123456,
  "lote_id": "690e26a5cb8287c0f1a180c3",
  "execucao_id": "690e2691cb8287c0f1a180c2",
  "publicacao_bronze_id": "690e26a6cb8287c0f1a180c4",

  // STATUS ATUAL
  "status_atual": "sucesso",
  "marcada_com_sucesso": true,

  // TIMESTAMPS
  "timestamp_primeira_tentativa": ISODate("2025-11-07T20:30:45.100Z"),
  "timestamp_ultima_tentativa": ISODate("2025-11-07T20:30:45.500Z"),
  "timestamp_sucesso": ISODate("2025-11-07T20:30:45.500Z"),

  // TENTATIVAS
  "total_tentativas": 1,
  "tentativas": [
    {
      "numero_tentativa": 1,
      "timestamp": ISODate("2025-11-07T20:30:45.500Z"),
      "status": "sucesso",
      "duracao_ms": 234.5,
      "mensagem_erro": null,
      "detalhes": {
        "marcacao_em_lote": true,
        "total_no_lote": 1821
      }
    }
  ],
  "duracao_total_ms": 234.5,

  // CONTEXTO
  "worker_id": null,
  "task_id": null,
  "process_instance_id": null,

  // SNAPSHOT (Auditoria Completa)
  "snapshot_publicacao": {
    "cod_publicacao": 123456,
    "numero_processo": "...",
    "texto_publicacao": "...",
    // ... todos os campos da publicação
  },

  // METADADOS
  "metadata": {
    "marcacao_automatica": true
  }
}
```

---

## 🎯 Endpoints de Auditoria

### 1. **Consultar Logs com Filtros**

```http
GET /auditoria/marcacoes?lote_id=690e26a5cb8287c0f1a180c3&limite=100
```

**Filtros disponíveis:**
- `cod_publicacao` - Código específico
- `lote_id` - Lote específico
- `status` - Status (sucesso, falha_webjur, etc.)
- `data_inicio` - Data inicial (ISO)
- `data_fim` - Data final (ISO)
- `apenas_falhas` - true/false
- `limite` - Paginação (1-1000)
- `offset` - Offset

**Response:**
```json
{
  "total_registros": 1821,
  "logs": [
    {
      "cod_publicacao": 123456,
      "status_atual": "sucesso",
      "total_tentativas": 1,
      "marcada_com_sucesso": true,
      "timestamp_sucesso": "2025-11-07T20:30:45.500Z",
      "duracao_total_ms": 234.5
    }
  ],
  "estatisticas": {
    "por_status": {
      "sucesso": {"count": 1821, "total_tentativas": 1821}
    },
    "total_registros": 1821
  }
}
```

### 2. **Log de Publicação Específica**

```http
GET /auditoria/marcacoes/publicacao/123456
```

Retorna o log mais recente da publicação com todas as tentativas.

### 3. **Estatísticas de um Lote**

```http
GET /auditoria/marcacoes/lote/690e26a5cb8287c0f1a180c3/estatisticas
```

**Response:**
```json
{
  "lote_id": "690e26a5cb8287c0f1a180c3",
  "estatisticas": {
    "total_publicacoes": 1821,
    "sucesso": 1821,
    "falhas": 0,
    "total_tentativas": 1821,
    "duracao_total_ms": 427234.5
  },
  "timestamp_consulta": "2025-11-07T20:35:00.000Z"
}
```

### 4. **Resumo Geral**

```http
GET /auditoria/marcacoes/resumo?data_inicio=2025-11-01T00:00:00Z
```

**Response:**
```json
{
  "total_marcacoes": 5000,
  "sucessos": 4950,
  "falhas": 50,
  "taxa_sucesso_percentual": 99.0,
  "distribuicao_por_status": {
    "sucesso": {"count": 4950},
    "falha_webjur": {"count": 30},
    "erro_interno": {"count": 20}
  }
}
```

### 5. **Falhas Recentes**

```http
GET /auditoria/marcacoes/falhas/recentes?limite=50
```

Útil para monitoramento e alertas em tempo real.

---

## ⚙️ Configuração

### Habilitar/Desabilitar Marcação Automática

A marcação automática é **controlada via variável de ambiente** no arquivo `.env`:

**Arquivo `.env.local` ou `.env.production`:**
```bash
# ============================================
# Marcação Automática de Publicações
# ============================================
# Define se publicações devem ser marcadas como exportadas
# imediatamente após salvar no MongoDB
# true = Marca automaticamente (padrão/recomendado)
# false = Desabilita marcação automática
MARCAR_AUTOMATICAMENTE=true
```

**Como funciona:**
1. ✅ **`true`** (padrão) - Marca automaticamente ao salvar no MongoDB
2. ❌ **`false`** - Desabilita marcação automática (modo manual via BPMN)

**Onde está configurado:**
- `core/config.py` - Lê a variável do .env
- `routers/buscar_publicacoes.py` - Usa `settings.MARCAR_AUTOMATICAMENTE`
- `services/lote_service.py` - Executa ou não baseado na flag

**Para desabilitar temporariamente:**
```bash
# Edite .env.local
MARCAR_AUTOMATICAMENTE=false

# Reinicie o Gateway
docker restart camunda-worker-api-gateway
```

**Para habilitar novamente:**
```bash
# Edite .env.local
MARCAR_AUTOMATICAMENTE=true

# Reinicie o Gateway
docker restart camunda-worker-api-gateway
```

---

## 🎭 Cenários de Uso

### Cenário 1: Produção Normal (Recomendado)
```bash
MARCAR_AUTOMATICAMENTE=true
```
- ✅ Publicações marcadas imediatamente ao salvar
- ✅ Evita duplicatas na próxima busca
- ✅ Log de auditoria completo
- ✅ Performance otimizada (marcação em lote)

**Quando usar:** Ambiente de produção em operação normal

---

### Cenário 2: Testes/Debug
```bash
MARCAR_AUTOMATICAMENTE=false
```
- ✅ Publicações NÃO são marcadas automaticamente
- ✅ Permite testar múltiplas vezes com mesmos dados
- ✅ Útil para debug e desenvolvimento
- ✅ Marcação manual via tópico BPMN ainda funciona

**Quando usar:**
- Testes locais
- Debug de problemas
- Desenvolvimento de features
- Treinamento da equipe

---

### Cenário 3: Migração/Reprocessamento
```bash
MARCAR_AUTOMATICAMENTE=false
```
- ✅ Busca publicações antigas sem marcar
- ✅ Permite reprocessar dados históricos
- ✅ Não interfere com dados na Webjur
- ✅ Útil para correção de dados

**Quando usar:**
- Migração de dados
- Correção de registros
- Reprocessamento de lotes
- Auditoria de dados antigos

---

### Cenário 4: Monitoramento da API
```bash
MARCAR_AUTOMATICAMENTE=false
```
- ✅ Monitora quantas publicações chegam
- ✅ Não marca para não "consumir" as publicações
- ✅ Útil para dashboards de volume
- ✅ Análise sem side-effects

**Quando usar:**
- Criar métricas de volume
- Monitorar API Webjur
- Análise de dados sem impacto

---

## 📈 Benefícios

### 1. **Auditoria Completa**
- ✅ Histórico de todas as tentativas
- ✅ Timestamps precisos
- ✅ Mensagens de erro detalhadas
- ✅ Snapshot dos dados para forense

### 2. **Rastreabilidade**
- ✅ Sabe exatamente quando foi marcada
- ✅ Quanto tempo levou
- ✅ Quantas tentativas foram necessárias
- ✅ Em qual lote/execução aconteceu

### 3. **Monitoramento**
- ✅ Taxa de sucesso em tempo real
- ✅ Alertas de falhas recentes
- ✅ Estatísticas por lote
- ✅ Dashboard pronto (via endpoints)

### 4. **Performance**
- ✅ Marcação em lote (1821 de uma vez)
- ✅ Bulk updates no MongoDB
- ✅ Não bloqueia salvamento se falhar
- ✅ Logs assíncronos

### 5. **Confiabilidade**
- ✅ Evita duplicatas (Webjur + MongoDB)
- ✅ Não perde dados se falhar
- ✅ Retry automático possível (futuro)
- ✅ Logs nunca são perdidos

---

## 🧪 Testes

### Teste 1: Verificar marcação automática

```bash
# 1. Buscar publicações
curl -X POST http://localhost:8000/buscar-publicacoes/processar-task-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-123",
    "process_instance_id": "test-instance",
    "variables": {
      "cod_grupo": 5,
      "limite_publicacoes": 10
    }
  }'

# Response:
# {
#   "lote_id": "...",
#   "total_processadas": 10,
#   ...
# }

# 2. Verificar logs de auditoria
curl "http://localhost:8000/auditoria/marcacoes?lote_id=<LOTE_ID>&limite=10"

# 3. Verificar publicação específica
curl "http://localhost:8000/auditoria/marcacoes/publicacao/123456"
```

### Teste 2: Estatísticas do lote

```bash
curl "http://localhost:8000/auditoria/marcacoes/lote/<LOTE_ID>/estatisticas"

# Deve retornar:
# {
#   "total_publicacoes": 10,
#   "sucesso": 10,
#   "falhas": 0
# }
```

### Teste 3: Verificar MongoDB

```javascript
// MongoDB Shell
use worker_gateway;

// Ver publicações marcadas
db.publicacoes_bronze.find({
  marcada_exportada_webjur: true,
  marcacao_automatica: true
}).pretty();

// Ver logs de auditoria
db.logs_marcacao_publicacoes.find({
  status_atual: "sucesso"
}).pretty();

// Estatísticas
db.logs_marcacao_publicacoes.aggregate([
  {
    $group: {
      _id: "$status_atual",
      count: { $sum: 1 },
      duracao_media: { $avg: "$duracao_total_ms" }
    }
  }
]);
```

---

## 🔍 Status de Marcação

| Status | Descrição | Quando Ocorre |
|--------|-----------|---------------|
| `pendente` | Aguardando processamento | Log criado, mas ainda não tentou marcar |
| `sucesso` | Marcada com sucesso | Webjur e MongoDB atualizados |
| `falha_webjur` | Falha na API Webjur | setPublicacoes() retornou false |
| `falha_mongodb` | Falha ao atualizar MongoDB | MongoDB update falhou |
| `falha_timeout` | Timeout na operação | Operação excedeu tempo limite |
| `falha_validacao` | Erro de validação | cod_publicacao inválido |
| `erro_interno` | Erro inesperado | Exception durante processamento |

---

## 📊 Índices do MongoDB

O `AuditoriaService` cria automaticamente índices para otimizar consultas:

```javascript
// Criados automaticamente ao iniciar
db.logs_marcacao_publicacoes.createIndex({ "cod_publicacao": 1 });
db.logs_marcacao_publicacoes.createIndex({ "lote_id": 1 });
db.logs_marcacao_publicacoes.createIndex({ "status_atual": 1 });
db.logs_marcacao_publicacoes.createIndex({ "timestamp_primeira_tentativa": 1 });
db.logs_marcacao_publicacoes.createIndex({
  "lote_id": 1,
  "status_atual": 1,
  "timestamp_primeira_tentativa": -1
});
```

---

## 🚀 Próximos Passos (Opcional)

1. **Retry Automático** - Tentar novamente falhas após X minutos
2. **Alertas** - Notificar quando taxa de falha > 5%
3. **Dashboard** - UI para visualizar logs e estatísticas
4. **Exportar Logs** - Endpoint para exportar logs em CSV/Excel
5. **Limpeza Automática** - Limpar logs antigos (>90 dias)

---

## 📝 Resumo

✅ **Funcionalidade implementada com sucesso!**

- Publicações são marcadas automaticamente ao salvar no MongoDB
- Log completo de auditoria em coleção dedicada
- Endpoints para consultar histórico e estatísticas
- Performance otimizada (marcação em lote)
- Não bloqueia processo se falhar
- 100% rastreável e auditável

**Resultado:** Sistema robusto que garante que toda publicação baixada é imediatamente marcada como "cumprida" na Webjur, com log detalhado de toda a operação! 🎉
