# Solução: Publicações sem numero_processo

## Problema Identificado

Publicações chegavam ao BPMN sem `numero_processo` válido, impedindo a criação correta do `business_key`.

### Causas Raiz
1. **Tratamento inadequado**: String vazia `""` não era detectada pelo operador `or`
2. **Dados de origem**: API SOAP retorna publicações com `numero_processo` vazio/null
3. **Sem visibilidade**: Não havia logs ou métricas sobre o problema

## ✅ Solução Implementada: REJEITAR Publicações sem numero_processo

**DECISÃO**: Publicações sem `numero_processo` válido são **REJEITADAS** e não processadas.
Elas não entram no lote, não são salvas no MongoDB e não chegam ao Camunda.

### 1. Validação Estrita (buscar_request.py, linhas 360-370)

```python
# ANTES (tratava com fallback)
numero_processo = (
    publicacao.numero_processo or f"PROCESSO-{publicacao.cod_publicacao}"
)

# DEPOIS (rejeita se inválido)
numero_processo_original = getattr(publicacao, "numero_processo", None)
if not numero_processo_original or not numero_processo_original.strip():
    # REJEITAR: Publicação sem numero_processo não é válida
    raise ValueError(
        f"Publicação cod={publicacao.cod_publicacao} rejeitada: "
        f"numero_processo inválido ou vazio"
    )

numero_processo = numero_processo_original.strip()
```

**Comportamento**:
- ✅ Aceita: `numero_processo` com valor válido
- ❌ Rejeita: `None`, `""`, `"   "` (whitespace)
- 🔍 Exceção: `ValueError` com mensagem descritiva

### 2. Filtro de Rejeição (buscar_publicacoes.py, linhas 606-707)

**Implementado**:
- Captura `ValueError` ao converter publicações
- Contabiliza publicações rejeitadas
- Logs individuais para cada rejeição
- Log resumo com estatísticas
- Retorna erro se TODAS foram rejeitadas

**Exemplo de output**:
```
🔄 Convertendo 1000 publicações...
❌ Publicação cod=12345 rejeitada: numero_processo inválido ou vazio
❌ Publicação cod=12367 rejeitada: numero_processo inválido ou vazio
...
✅ Conversão concluída: 955 válidas, 45 rejeitadas de 1000 publicações
⚠️ ATENÇÃO: 45 publicações (4.5%) foram REJEITADAS (sem numero_processo válido)
💾 Criando lote com 955 publicações...
```

**Se todas forem rejeitadas**:
```
✅ Conversão concluída: 0 válidas, 1000 rejeitadas de 1000 publicações
⚠️ ATENÇÃO: 1000 publicações (100.0%) foram REJEITADAS
{
  "status": "error",
  "message": "Todas as 1000 publicações foram rejeitadas (sem numero_processo válido)",
  "total_rejeitadas": 1000,
  "lote_id": null
}
```

## Monitoramento

### Logs do Gateway
Buscar por publicações rejeitadas:
```bash
# Ver todas as rejeições
docker logs camunda-worker-api-gateway-gateway-1 2>&1 | grep "rejeitada:"

# Contar rejeições
docker logs camunda-worker-api-gateway-gateway-1 2>&1 | grep -c "rejeitada:"

# Ver resumo de conversões
docker logs camunda-worker-api-gateway-gateway-1 2>&1 | grep "Conversão concluída"

# Ver warnings de rejeição
docker logs camunda-worker-api-gateway-gateway-1 2>&1 | grep "foram REJEITADAS"
```

### MongoDB - Execuções

**Ver execuções com rejeições**:
```javascript
db.execucoes.find({
  "total_rejeitadas": { $gt: 0 }
}).sort({ data_inicio: -1 }).limit(10)
```

**Estatísticas de rejeição**:
```javascript
db.execucoes.aggregate([
  {
    $match: {
      total_encontradas: { $gt: 0 }
    }
  },
  {
    $project: {
      data_inicio: 1,
      total_encontradas: 1,
      total_processadas: 1,
      total_rejeitadas: 1,
      taxa_rejeicao: {
        $multiply: [
          { $divide: ["$total_rejeitadas", "$total_encontradas"] },
          100
        ]
      }
    }
  },
  { $sort: { taxa_rejeicao: -1 } },
  { $limit: 20 }
])
```

### MongoDB - Publicações (NÃO haverá registros rejeitados)

**IMPORTANTE**: Publicações rejeitadas **NÃO** são salvas no MongoDB.
Apenas publicações válidas com `numero_processo` estão na coleção `publicacoes_bronze`.

```javascript
// Todas as publicações têm numero_processo válido
db.publicacoes_bronze.find({
  "numero_processo": { $exists: true, $ne: "", $ne: null }
}).count()

// Não haverá publicações com padrão PROCESSO-*
db.publicacoes_bronze.countDocuments({
  "numero_processo": /^PROCESSO-\d+$/
})  // Deve retornar 0
```

## Estratégias Alternativas

### Opção A: Rejeitar Publicações sem Processo (Strict Mode)

Se quiser **rejeitar** publicações sem numero_processo válido:

```python
# Em buscar_publicacoes.py, linha ~611
if not numero_processo_original or not numero_processo_original.strip():
    logger.warning(f"❌ Rejeitando publicação cod={pub.cod_publicacao}: sem numero_processo")
    continue  # Pula essa publicação
```

**Pros**: Garantia de qualidade de dados
**Cons**: Perda de publicações que podem ser relevantes

### Opção B: Classificar para Triagem Manual

Marcar publicações com fallback para revisão:

```python
publicacoes_bronze.append({
    ...
    "requires_manual_review": pub_convertida.numero_processo.startswith("PROCESSO-"),
    "review_reason": "numero_processo_invalido",
    ...
})
```

### Opção C: Tentar Extrair do Texto

Usar regex para tentar extrair numero_processo do texto da publicação:

```python
import re

# Padrões comuns: 0000000-00.0000.0.00.0000
pattern = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'
match = re.search(pattern, publicacao.texto_publicacao or "")
if match:
    numero_processo = match.group(0)
else:
    numero_processo = f"PROCESSO-{publicacao.cod_publicacao}"
```

## ✅ Impacto no Business Key

Com a solução de rejeição, **APENAS publicações válidas** chegam ao Camunda:

**Publicações aceitas (com processo válido)**:
```
business_key = "mov_0001234-56.2024.8.13.0001_20251110193045"
business_key = "mov_5005678-90.2023.8.13.0024_20251110193046"
```

**Publicações rejeitadas (sem processo válido)**:
```
❌ NÃO chegam ao Camunda
❌ NÃO são salvas no MongoDB
❌ NÃO geram business_key
✅ São contabilizadas nos logs e na execução
```

**Resultado**: TODOS os business_keys no Camunda são válidos e baseados em `numero_processo` real!

## Métricas de Sucesso

Após deploy, monitorar:

1. **Taxa de fallback**: Deve ser < 5% (ideal)
2. **Logs de warning**: Verificar se há padrão (ex: sempre do mesmo tribunal)
3. **Business keys no Camunda**: Validar que todos são únicos
4. **MongoDB auditoria**: Usar `numero_processo_original` para análise

## Arquivos Modificados

1. `camunda-worker-api-gateway/app/models/buscar_request.py` (linhas 361-367)
2. `camunda-worker-api-gateway/app/routers/buscar_publicacoes.py` (linhas 609-670)

## Próximos Passos

1. ✅ Deploy das correções
2. ⏳ Monitorar logs por 24h
3. ⏳ Analisar percentual de fallbacks
4. ⏳ Investigar origem dos dados sem processo
5. ⏳ Considerar integração com N8N para enriquecimento de dados
