# Padrão de Variáveis para Multi-Instance Loops no Camunda

## Visão Geral

Este documento descreve o padrão de nomenclatura de variáveis para endpoints do Gateway que processam tasks executadas em **Multi-Instance Loops** no Camunda BPM.

## O Problema

Quando uma Service Task no BPMN é configurada com `multiInstanceLoopCharacteristics`, ela executa **múltiplas iterações** sobre uma coleção (array). Cada iteração recebe um elemento da coleção através da variável `elementVariable`.

**Exemplo BPMN:**
```xml
<bpmn:multiInstanceLoopCharacteristics
  camunda:collection="${publicacoes_ids}"
  camunda:elementVariable="publicacao_id" />
```

**Comportamento:**
- **Entrada:** `publicacoes_ids = ["673abc...", "674def...", "675ghi..."]`
- **Iterações:** 3 execuções da task, cada uma com `publicacao_id` diferente

### ❌ Problema: Conflito de Variáveis

Se todas as iterações retornarem variáveis com **nomes idênticos**, elas **sobrescrevem-se mutuamente** no contexto global do processo:

```python
# INCORRETO: Variáveis sem prefixo
Iteração 1: publicacao_id="673abc..." → status_publicacao="nova"
Iteração 2: publicacao_id="674def..." → status_publicacao="repetida"  # SOBRESCREVE!
Iteração 3: publicacao_id="675ghi..." → status_publicacao="nova"      # SOBRESCREVE!

# Resultado no processo Camunda:
status_publicacao = "nova"  # ❌ SOMENTE O ÚLTIMO VALOR PERSISTE!
# Valores das iterações 1 e 2 foram PERDIDOS
```

## ✅ A Solução: Prefixar Variáveis com `{element_variable}_*`

Para evitar conflitos, **prefixar variáveis de negócio** com o valor da `elementVariable` atual:

```python
# CORRETO: Variáveis com prefixo {publicacao_id}_*
Iteração 1: publicacao_id="673abc..." → 673abc..._status_publicacao="nova"
Iteração 2: publicacao_id="674def..." → 674def..._status_publicacao="repetida"
Iteração 3: publicacao_id="675ghi..." → 675ghi..._status_publicacao="nova"

# Resultado no processo Camunda:
673abc..._status_publicacao = "nova"      # ✅ Preservado
674def..._status_publicacao = "repetida"  # ✅ Preservado
675ghi..._status_publicacao = "nova"      # ✅ Preservado
# TODOS OS VALORES PRESERVADOS!
```

## Quando Aplicar o Padrão

### ✅ USE o padrão `{element}_*` quando:

- [ ] A task/endpoint é executado **dentro de um Multi-Instance Loop**
- [ ] A variável `element_variable` (ex: `publicacao_id`) é definida no BPMN
- [ ] Você precisa **preservar dados individuais** de cada iteração
- [ ] Processos downstream precisam **acessar dados específicos** de cada elemento

### ❌ NÃO USE o padrão quando:

- [ ] A task executa **UMA ÚNICA VEZ** por processo
- [ ] Não há iterações concorrentes/paralelas
- [ ] As variáveis são temporárias/locais
- [ ] Não há `multiInstanceLoopCharacteristics` no BPMN

## Checklist de Implementação

### 1. Identificar Variáveis

**Separar variáveis em dois grupos:**

**a) Variáveis de CONTROLE (sem prefixo):**
- `status` - Status da operação (success/error)
- `task_id` - ID da task Camunda
- `message` - Mensagem de retorno
- IDs de referência (`publicacao_id`, `publicacao_prata_id`)

**b) Variáveis de NEGÓCIO (com prefixo):**
- Dados de processamento (`status_publicacao`, `score_similaridade`)
- Classificações (`n8n_processing`, `classificacao_tipo`)
- Informações extraídas (`numero_processo`, `nome_cliente`)
- Flags de negócio (`urgente`, `prazo_dias`)

### 2. Aplicar Prefixo nas Variáveis de Negócio

```python
# Antes (INCORRETO para Multi-Instance)
return {
    "status": "success",
    "n8n_processing": data,           # ❌ Sem prefixo
    "classificacao": "citacao",        # ❌ Sem prefixo
    "publicacao_id": publicacao_id,
}

# Depois (CORRETO para Multi-Instance)
return {
    "status": "success",                                    # ✅ Controle - sem prefixo
    "publicacao_id": publicacao_id,                         # ✅ Referência - sem prefixo
    f"{publicacao_id}_n8n_processing": data,                # ✅ Negócio - COM prefixo
    f"{publicacao_id}_classificacao": "citacao",            # ✅ Negócio - COM prefixo
    "message": "Classificação processada",                  # ✅ Controle - sem prefixo
}
```

### 3. Documentar no Código

Adicionar comentários explicativos:

```python
# ========== PADRÃO MULTI-INSTANCE: Prefixar variáveis de negócio ==========
# Retorna no formato esperado pelo BPMN com prefixo {publicacao_id}_
# Isso evita conflito de variáveis em Multi-Instance Loops
return {
    "status": "success",  # Variável de controle - sem prefixo
    f"{element_id}_data": business_data,  # Variável de negócio COM prefixo
}
```

## Implementações Atuais

### Endpoint: `/publicacoes/processar-task-publicacao`

**Tópico Camunda:** `tratar_publicacao`

**Contexto BPMN:** Multi-Instance Loop sobre `publicacoes_ids`

**Implementação:**
```python
# camunda-worker-api-gateway/app/routers/publicacoes.py (linhas 484-495)
return {
    "status": "success",
    "task_id": task_data.task_id,
    "publicacao_id": str(result.inserted_id),  # ID da Prata (novo)
    "publicacao_prata_id": str(result.inserted_id),
    # Variáveis de negócio COM prefixo {publicacao_id}_ (ID do Bronze)
    f"{publicacao_id}_status_publicacao": pub_prata.status,
    f"{publicacao_id}_score_similaridade": pub_prata.score_similaridade,
    f"{publicacao_id}_numero_processo": numero_processo_final,
    "message": f"Publicação processada com status: {pub_prata.status}",
}
```

**Variáveis criadas:**
- `{bronze_id}_status_publicacao` - Status da deduplicação (nova/repetida/duvidosa)
- `{bronze_id}_score_similaridade` - Score de similaridade (0.0-100.0)
- `{bronze_id}_numero_processo` - Número CNJ formatado

### Endpoint: `/publicacoes/classificar`

**Tópico Camunda:** `classificar_publicacao`

**Contexto BPMN:** Pode ser usado em Multi-Instance Loop (preparado para isso)

**Implementação:**
```python
# camunda-worker-api-gateway/app/routers/publicacoes.py (linhas 750-757)
return {
    "status": "success",  # Controle
    "publicacao_id": publicacao_bronze_id,  # ID Bronze - referência
    "publicacao_prata_id": publicacao_prata_id,  # ID Prata - referência
    # Variável de negócio COM prefixo {publicacao_bronze_id}_
    f"{publicacao_bronze_id}_n8n_processing": n8n_data,
    "message": f"Classificação processada para publicação Bronze {publicacao_bronze_id}",
}
```

**Variáveis criadas:**
- `{bronze_id}_n8n_processing` - Estrutura completa com dados da classificação N8N
  - Contém: `classificacao`, `justificativa_classificacao`, `nome_cliente`, `advogado_habilitado`, etc.

## Relação com Global Variables

### Mudança Recente (Commit `d5e1352`)

O BaseWorker foi modificado para usar **global variables por padrão**:

```python
# ANTES
return self.complete_task(
    task,
    variables=camunda_variables,
    use_local_variables=True,  # ← Local scope
)

# DEPOIS
return self.complete_task(
    task,
    variables=camunda_variables,
    use_local_variables=False,  # ← Global scope
)
```

### Como os Padrões se Complementam

**Prefixo `{element}_*` + Global Variables =  Solução Completa**

1. **Prefixo previne conflitos** entre iterações do loop
2. **Global variables** torna dados acessíveis em todo o processo

```
┌─────────────────────────────────────────────────────────────┐
│ Multi-Instance Loop (3 iterações)                           │
├─────────────────────────────────────────────────────────────┤
│ Iteração 1: 673abc_status="nova"        ← Prefixo único    │
│ Iteração 2: 674def_status="repetida"    ← Prefixo único    │
│ Iteração 3: 675ghi_status="nova"        ← Prefixo único    │
└─────────────────────────────────────────────────────────────┘
                        ↓ Global Variables
┌─────────────────────────────────────────────────────────────┐
│ Escopo Global do Processo                                   │
├─────────────────────────────────────────────────────────────┤
│ ✅ 673abc_status="nova"      ← Acessível em qualquer etapa │
│ ✅ 674def_status="repetida"  ← Acessível em qualquer etapa │
│ ✅ 675ghi_status="nova"      ← Acessível em qualquer etapa │
└─────────────────────────────────────────────────────────────┘
```

**Conclusão:** O prefixo `{element}_*` **CONTINUA NECESSÁRIO** mesmo com global variables, pois:
- Global variables **ampliam a visibilidade** (do loop → processo inteiro)
- Prefixo **previne conflitos** (entre iterações do mesmo loop)

## Exemplos Práticos

### Exemplo 1: Acesso a Variáveis Downstream

**Cenário:** Após processar 3 publicações, verificar quais são novas

**BPMN Script:**
```javascript
// Após o Multi-Instance Loop terminar
var publicacoes_ids = execution.getVariable("publicacoes_ids");
var novas = [];

for (var i = 0; i < publicacoes_ids.length; i++) {
    var pub_id = publicacoes_ids[i];
    var status = execution.getVariable(pub_id + "_status_publicacao");

    if (status === "nova_publicacao_inedita") {
        novas.push(pub_id);
    }
}

execution.setVariable("publicacoes_novas", novas);
```

**Resultado:** Array com IDs das publicações novas

### Exemplo 2: Agregação de Dados

**Cenário:** Calcular score médio de similaridade

**BPMN Script:**
```javascript
var publicacoes_ids = execution.getVariable("publicacoes_ids");
var total_score = 0;

for (var i = 0; i < publicacoes_ids.length; i++) {
    var pub_id = publicacoes_ids[i];
    var score = execution.getVariable(pub_id + "_score_similaridade");
    total_score += parseFloat(score);
}

var media = total_score / publicacoes_ids.length;
execution.setVariable("score_medio", media);
```

## Boas Práticas

### ✅ DO

1. **Sempre prefixar variáveis de negócio** em Multi-Instance contexts
2. **Documentar o padrão** nos comentários do código
3. **Usar f-strings** para construir nomes de variáveis: `f"{element_id}_data"`
4. **Testar com múltiplas iterações** (mínimo 3) para validar

### ❌ DON'T

1. **Não prefixar variáveis de controle** (`status`, `message`, `task_id`)
2. **Não omitir o prefixo** achando que "funciona" (só funciona com 1 iteração)
3. **Não usar prefixos diferentes** do `elementVariable` definido no BPMN
4. **Não assumir** que o endpoint está em Multi-Instance sem verificar o BPMN

## Debugging e Troubleshooting

### Sintoma: Valores sobrescritos

**Problema:** Só o último valor da iteração é preservado

**Causa:** Variáveis sem prefixo em Multi-Instance Loop

**Solução:** Aplicar prefixo `{element}_*` nas variáveis de negócio

### Sintoma: Variáveis não acessíveis downstream

**Problema:** Variáveis criadas no loop não existem após o loop

**Causa:** `use_local_variables=True` (escopo local)

**Solução:** Garantir `use_local_variables=False` (já padrão no BaseWorker)

### Ferramentas de Debug

**1. Cockpit Camunda:**
- Acessar processo → Variables
- Verificar se variáveis com prefixo `{id}_*` existem

**2. Logs do Gateway:**
```python
logger.info(f"✅ Retornando variáveis com prefixo {element_id}_ (padrão Multi-Instance)")
```

**3. BPMN Script de Validação:**
```javascript
// Inserir após Multi-Instance Loop
var ids = execution.getVariable("publicacoes_ids");
print("=== VALIDAÇÃO MULTI-INSTANCE ===");
for (var i = 0; i < ids.length; i++) {
    var id = ids[i];
    var status = execution.getVariable(id + "_status_publicacao");
    print("ID: " + id + " | Status: " + status);
}
```

## Referências

- **Arquivo:** `camunda-worker-api-gateway/app/routers/publicacoes.py`
- **Endpoints:** `/processar-task-publicacao`, `/classificar`
- **BPMN:** `camunda-platform-standalone/bpmn/Fluxo_publicacao_captura_intimacoes.bpmn`
- **BaseWorker:** `camunda-workers-platform/workers/common/base_worker.py`
- **Commit:** `d5e1352` - "refactor: Use global variables as default"

## FAQ

**Q: Devo prefixar TODAS as variáveis?**
A: Não. Apenas variáveis de **negócio**. Variáveis de controle (`status`, `message`) não precisam.

**Q: O que acontece se eu esquecer o prefixo?**
A: Com 1 iteração, funciona. Com 2+, apenas o último valor é preservado.

**Q: Posso usar outro separador além de `_`?**
A: Tecnicamente sim, mas `_` é o padrão recomendado para consistência.

**Q: Como saber se meu endpoint está em Multi-Instance?**
A: Verifique o BPMN. Procure por `<bpmn:multiInstanceLoopCharacteristics>` na service task.

**Q: Preciso atualizar o BPMN também?**
A: Não. O padrão é implementado apenas no backend (Gateway/Workers).

**Q: O prefixo afeta performance?**
A: Não significativamente. O overhead é apenas na construção da string.

---

**Última atualização:** 2025-01-18
**Autor:** Claude Code
**Status:** ✅ Implementado e Documentado
