# Solução para Problema de Publicações Repetidas

## Problema Identificado

Quando Rafael chama o tópico `buscar_publicacoes` a cada 3 minutos via Camunda BPM:
- **Sempre retorna as mesmas 50 publicações** (limite fixo)
- **Não há filtro incremental** para evitar reprocessamento
- **Publicações já processadas continuam sendo buscadas**

## Causa Raiz

De acordo com a documentação Webjur:

> **getPublicacoesNaoExportadas()**: Retorna até 3.000 publicações não marcadas como exportadas.
>
> **Fluxo recomendado**: Após importar publicações com sucesso, deve-se chamar **setPublicacoes()** passando os códigos das publicações para marcá-las como exportadas, evitando que sejam retornadas novamente.

**O sistema estava buscando publicações mas NÃO estava marcando como exportadas no Webjur**, causando reprocessamento infinito.

## Arquitetura Escolhida

⚠️ **IMPORTANTE**: Seguindo o **padrão arquitetural do projeto** (workers como orquestradores), a marcação de publicações é feita por um **tópico/worker DEDICADO**, não no mesmo fluxo de busca.

## Solução Implementada

### 1. Novo Tópico Dedicado: `marcar_publicacao_exportada_webjur`

**Arquivo**: `camunda-workers-platform/workers/common/config.py`
```python
Topics.MARCAR_PUBLICACAO_EXPORTADA_WEBJUR = "marcar_publicacao_exportada_webjur"
```

**Responsabilidade**: Tópico isolado para marcar UMA publicação como exportada no Webjur.

### 2. Handler no Worker (Orquestrador)

**Arquivo**: `camunda-workers-platform/workers/publicacao_unified/main.py`

**Método**: `handle_marcar_publicacao_exportada()`

**Comportamento**:
- Valida `cod_publicacao` (int obrigatório)
- Delega para Gateway via `/marcar-publicacoes/processar`
- **NÃO bloqueia processo** em caso de falha (retorna sucesso=False)
- Logs detalhados para auditoria

### 3. Endpoint no Gateway (Lógica de Negócio)

**Arquivo**: `camunda-worker-api-gateway/app/routers/marcar_publicacoes.py`

**Endpoint**: `POST /marcar-publicacoes/processar`

**Fluxo**:
1. Recebe `task_data` do worker com `cod_publicacao`
2. Chama `intimation_service.set_publicacoes([cod])` (SOAP Webjur)
3. Atualiza MongoDB: `marcada_exportada_webjur=True`
4. Retorna resultado ao worker

### 4. Endpoints Auxiliares (Marcação Manual)

**Arquivo**: `camunda-worker-api-gateway/app/routers/marcar_publicacoes.py`

Endpoints adicionais para testes e operações manuais:
- `POST /marcar-publicacoes/marcar-exportadas` - Marca lista de códigos
- `POST /marcar-publicacoes/marcar-por-lote/{lote_id}` - Marca lote inteiro
- `GET /marcar-publicacoes/status-exportacao/{cod_publicacao}` - Verifica status

### 5. Campos Adicionados ao Modelo MongoDB

**Arquivo**: `camunda-worker-api-gateway/app/models/publicacao.py`

**Novos campos em `PublicacaoBronze`**:
```python
marcada_exportada_webjur: Optional[bool] = Field(
    default=False,
    description="Flag indicando se foi marcada como exportada via setPublicacoes()"
)
timestamp_marcacao_exportada: Optional[datetime] = Field(
    None,
    description="Timestamp de quando foi marcada como exportada"
)
```

**Diferença para campo existente**:
- `publicacao_exportada` (int): Flag vinda DA API Webjur (estado original na fonte)
- `marcada_exportada_webjur` (bool): Flag controlada PELO nosso sistema (ação nossa)

## Comportamento Esperado Após Implementação

### Primeiro Ciclo (primeira chamada)
1. Worker chama `buscar_publicacoes` com `apenas_nao_exportadas=True`
2. API Webjur retorna 50 publicações não exportadas (limite)
3. Sistema salva no MongoDB como `publicacoes_bronze`
4. Sistema chama `setPublicacoes([cod1, cod2, ..., cod50])`
5. Webjur marca essas 50 como **exportadas**
6. MongoDB atualizado com `marcada_exportada_webjur=True`

### Segundo Ciclo (3 minutos depois)
1. Worker chama `buscar_publicacoes` novamente
2. API Webjur **NÃO retorna as 50 anteriores** (já marcadas como exportadas)
3. Retorna as **próximas 50 publicações não exportadas**
4. Ciclo se repete até processar todas

### Resultado Final
✅ **Sem duplicatas**: Cada publicação é processada apenas uma vez
✅ **Processamento incremental**: A cada chamada, processa lote novo
✅ **Auditoria completa**: Timestamp de marcação registrado

## Configuração Necessária

### Variáveis de Ambiente

Certifique-se que as credenciais SOAP estão configuradas:

```bash
# .env.production ou .env.local
SOAP_URL=https://intimation-panel.azurewebsites.net/wsPublicacao.asmx
SOAP_USUARIO=100049
SOAP_SENHA=DcDpW@24
SOAP_TIMEOUT=90
SOAP_MAX_RETRIES=3
```

### Parâmetros do Worker

No arquivo de configuração do worker (`camunda-workers-platform/workers/publicacao_unified/`):

```json
{
  "apenas_nao_exportadas": true,  // OBRIGATÓRIO para evitar repetições
  "cod_grupo": 5,                 // Filtro por grupo (opcional)
  "limite_publicacoes": 50        // Processa 50 por vez (recomendado)
}
```

## Limites da API Webjur

Conforme documentação oficial:

| Método | Limite | Observação |
|--------|--------|------------|
| `getPublicacoesNaoExportadas()` | 3.000 publicações | Retorna no máximo 3k por chamada |
| `setPublicacoes()` | Sem limite explícito | Recomendado processar em lotes de 50-100 |
| Período de busca por data | 90 dias | Períodos maiores causam timeout |

**IMPORTANTE**: O limite de 50 publicações no nosso sistema é uma **proteção de desempenho**, não uma limitação da API Webjur.

## Fluxo de Dados Completo (Nova Arquitetura)

```
┌──────────────────────────────────────────────────────────────────────┐
│ BPMN Process - Timer Event (a cada 3 minutos)                       │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Service Task: buscar_publicacoes                                     │
│  └─> Worker: PublicacaoUnifiedWorker.handle_buscar_publicacoes()    │
│      └─> Gateway: POST /buscar-publicacoes/processar-task-v2        │
│          ├─ SOAP: getPublicacoesNaoExportadas(cod_grupo=5)          │
│          ├─ Salva MongoDB: publicacoes_bronze                       │
│          └─ Retorna: {lote_id, publicacoes_ids[]}                   │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Multi-Instance Loop (para cada publicacao_id)                       │
│  ├─ Service Task: tratar_publicacao                                 │
│  ├─ Service Task: classificar_publicacao                            │
│  └─ Service Task: marcar_publicacao_exportada_webjur  ← NOVO!       │
│      ├─ Input: cod_publicacao (extraído do publicacao_id)           │
│      └─> Worker: handle_marcar_publicacao_exportada()               │
│          └─> Gateway: POST /marcar-publicacoes/processar            │
│              ├─ SOAP: setPublicacoes([cod_publicacao])              │
│              ├─ MongoDB: marcada_exportada_webjur=True              │
│              └─ Retorna: {sucesso: true, mensagem: "..."}           │
└──────────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Resultado Final                                                      │
│  ✅ Publicação processada E marcada como exportada                  │
│  ✅ Próxima busca NÃO retornará esta publicação                     │
│  ✅ Processo completo rastreado no Camunda                          │
└──────────────────────────────────────────────────────────────────────┘
```

### Vantagens da Nova Arquitetura

✅ **Separação de responsabilidades**: Busca ≠ Marcação (cada uma em seu tópico)
✅ **Rastreabilidade Camunda**: Task dedicada para marcação aparece no histórico
✅ **Retry isolado**: Se marcação falha, só ela é reprocessada (não toda a busca)
✅ **Flexibilidade BPMN**: Pode marcar individual (Multi-Instance) ou em lote
✅ **Não bloqueante**: Processo continua mesmo se marcação falhar (apenas loga erro)
✅ **Segue padrão do projeto**: Worker orquestrador + Gateway com lógica de negócio

## Como Configurar no BPMN

### Opção 1: Marcação Individual (Recomendado)

Adicionar Service Task dentro do Multi-Instance Loop:

```xml
<!-- No Camunda Modeler, adicionar após classificar_publicacao -->
<serviceTask id="Task_MarcarExportada" name="Marcar como Exportada no Webjur">
  <extensionElements>
    <camunda:topic>marcar_publicacao_exportada_webjur</camunda:topic>
    <camunda:inputOutput>
      <camunda:inputParameter name="cod_publicacao">${publicacao_bronze.cod_publicacao}</camunda:inputParameter>
    </camunda:inputOutput>
  </extensionElements>
</serviceTask>
```

**Quando usar**: Quando quer marcar DURANTE o processamento de cada publicação.

### Opção 2: Marcação em Lote

Adicionar Service Task APÓS o Multi-Instance Loop:

```bash
# Chamar endpoint de marcação por lote
curl -X POST http://gateway:8000/marcar-publicacoes/marcar-por-lote/${lote_id}
```

**Quando usar**: Quando quer marcar TODAS de uma vez, após todo processamento.

### Variáveis Necessárias no BPMN

Para a marcação individual funcionar, o BPMN precisa garantir que a variável `cod_publicacao` esteja disponível:

```xml
<!-- Exemplo de mapeamento de variáveis -->
<camunda:inputOutput>
  <!-- Extrair cod_publicacao do objeto publicacao_bronze -->
  <camunda:inputParameter name="cod_publicacao">
    ${execution.getVariable("publicacao_bronze").get("cod_publicacao")}
  </camunda:inputParameter>
</camunda:inputOutput>
```

**Importante**: O `publicacao_id` retornado pelo endpoint de busca é o **ObjectId do MongoDB**. Para obter o `cod_publicacao` (código Webjur), é necessário buscar o documento antes de marcar.

## Testes para Validar

### 1. Teste do Worker (Verificar Subscrição)

```bash
# Verificar se worker subscreveu ao tópico
docker logs publicacao-unified-worker 2>&1 | grep "marcar_publicacao_exportada_webjur"

# Deve aparecer:
# ✅ Worker configurado em modo orquestrador (Gateway)
#   • marcar_publicacao_exportada_webjur - Marcação Webjur
```

### 2. Teste de Marcação Manual (Endpoint Gateway)

```bash
# Marcar publicações específicas
curl -X POST http://localhost:8000/marcar-publicacoes/marcar-exportadas \
  -H "Content-Type: application/json" \
  -d '{
    "cod_publicacoes": [123456, 123457, 123458],
    "atualizar_mongodb": true
  }'
```

### 2. Teste de Marcação por Lote

```bash
# Marcar todas publicações de um lote
curl -X POST http://localhost:8000/marcar-publicacoes/marcar-por-lote/67891011121314151617181 \
  -H "Content-Type: application/json"
```

### 3. Verificar Status

```bash
# Verificar se publicação foi marcada
curl http://localhost:8000/marcar-publicacoes/status-exportacao/123456
```

### 4. Teste de Reprocessamento (validar que não repete)

```bash
# Primeira chamada
curl -X POST http://localhost:8000/buscar-publicacoes/processar-task-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-1",
    "process_instance_id": "test-instance-1",
    "variables": {
      "apenas_nao_exportadas": true,
      "cod_grupo": 5,
      "limite_publicacoes": 10
    }
  }'

# Segunda chamada (deve retornar PUBLICAÇÕES DIFERENTES)
curl -X POST http://localhost:8000/buscar-publicacoes/processar-task-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-2",
    "process_instance_id": "test-instance-2",
    "variables": {
      "apenas_nao_exportadas": true,
      "cod_grupo": 5,
      "limite_publicacoes": 10
    }
  }'
```

**Validação esperada**: Os códigos de publicação (`cod_publicacao`) da segunda chamada devem ser DIFERENTES da primeira.

## Monitoramento

### Logs para Acompanhar

```
# Busca bem-sucedida
📤 Buscando publicações não exportadas: cod_grupo=5
📥 Obtidas 50 publicações não exportadas (grupo 5)

# Marcação bem-sucedida
Marcando 50 publicações como exportadas no Webjur...
✅ Sucesso ao marcar 50 publicações como exportadas
MongoDB atualizado: 50 registros marcados como exportados

# Próxima execução (sem repetição)
📤 Buscando publicações não exportadas: cod_grupo=5
📥 Obtidas 50 publicações não exportadas (grupo 5)
# NOTA: Códigos de publicação serão DIFERENTES
```

### Queries MongoDB para Monitoramento

```javascript
// Contar publicações marcadas como exportadas
db.publicacoes_bronze.countDocuments({ marcada_exportada_webjur: true })

// Últimas 10 publicações marcadas
db.publicacoes_bronze.find(
  { marcada_exportada_webjur: true }
).sort({ timestamp_marcacao_exportada: -1 }).limit(10)

// Publicações ainda não marcadas
db.publicacoes_bronze.countDocuments({ marcada_exportada_webjur: { $ne: true } })
```

## Troubleshooting

### Problema: Ainda recebe publicações repetidas

**Possíveis causas**:
1. `apenas_nao_exportadas` está **false** → mudar para **true**
2. Chamada `setPublicacoes()` está falhando → verificar logs
3. Credenciais SOAP inválidas → verificar `SOAP_USUARIO` e `SOAP_SENHA`
4. Timeout na chamada SOAP → aumentar `SOAP_TIMEOUT`

**Solução**:
```bash
# Verificar logs do Gateway
docker logs camunda-worker-api-gateway --tail 100

# Testar conexão SOAP manualmente
curl http://localhost:8000/test-camunda
```

### Problema: MongoDB não atualiza

**Solução**:
```python
# Verificar se campo existe no documento
db.publicacoes_bronze.findOne({ cod_publicacao: 123456 })

# Criar índice para performance
db.publicacoes_bronze.createIndex({ cod_publicacao: 1 })
db.publicacoes_bronze.createIndex({ marcada_exportada_webjur: 1 })
```

## Próximos Passos (Opcional)

### 1. Worker Dedicado para Marcação

Criar worker separado que apenas marca como exportadas (desacoplado do processamento):

```
BPMN Topic: marcar_publicacao_exportada_clovis
Input: cod_publicacao (int)
Output: success/failure
```

### 2. Retry Automático

Adicionar retry em caso de falha na marcação:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def marcar_com_retry(cod_publicacoes):
    return soap_client.set_publicacoes(cod_publicacoes)
```

### 3. Dashboard de Monitoramento

Criar dashboard Grafana com métricas:
- Total de publicações processadas por dia
- Taxa de marcação bem-sucedida
- Latência da API Webjur
- Publicações pendentes de marcação

## Conclusão

✅ **Problema resolvido**: Sistema agora marca publicações como exportadas após processamento
✅ **Reprocessamento eliminado**: Próximas chamadas retornam publicações novas
✅ **Auditoria completa**: Timestamps registrados para rastreabilidade
✅ **Endpoints adicionais**: Marcação manual disponível via API

**Comportamento esperado**: A cada ciclo de 3 minutos, o sistema processa lote novo de 50 publicações, sem repetir as já processadas.
