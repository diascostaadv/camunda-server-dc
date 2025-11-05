# Como Usar o Tópico `marcar_publicacao_exportada_webjur` no BPMN

## Objetivo

Este documento explica como configurar o processo BPMN para usar o novo tópico dedicado de marcação de publicações como exportadas no Webjur.

## Pré-requisitos

✅ Worker `publicacao_unified` deve estar rodando (subscrito ao tópico)
✅ Gateway API deve estar acessível (endpoint `/marcar-publicacoes/processar`)
✅ Credenciais SOAP Webjur configuradas (`SOAP_USUARIO`, `SOAP_SENHA`)

---

## Opção 1: Marcação Individual (Recomendado)

### Quando Usar

Use quando você quer marcar cada publicação **imediatamente após processá-la** com sucesso (dentro do Multi-Instance Loop).

### Configuração no Camunda Modeler

#### Passo 1: Adicionar Service Task

No Camunda Modeler, dentro do Multi-Instance Loop (após `classificar_publicacao`):

1. Arraste um **Service Task** para o diagrama
2. Nomeie: `Marcar como Exportada no Webjur`
3. ID: `Task_MarcarExportadaWebjur`

#### Passo 2: Configurar External Task

Na aba **General** do Service Task:

- **Implementation**: `External`
- **Topic**: `marcar_publicacao_exportada_webjur`

#### Passo 3: Mapear Variáveis de Entrada

Na aba **Input/Output** > **Input Parameters**:

| Local Variable Name | Value | Type |
|---------------------|-------|------|
| `cod_publicacao` | `${publicacao_bronze.cod_publicacao}` | Expression |

**Ou via XML**:

```xml
<serviceTask id="Task_MarcarExportadaWebjur" name="Marcar como Exportada no Webjur">
  <extensionElements>
    <camunda:topic>marcar_publicacao_exportada_webjur</camunda:topic>
    <camunda:inputOutput>
      <camunda:inputParameter name="cod_publicacao">
        ${publicacao_bronze.cod_publicacao}
      </camunda:inputParameter>
    </camunda:inputOutput>
  </extensionElements>
</serviceTask>
```

#### Passo 4: Mapear Variáveis de Saída (Opcional)

Se você quer capturar o resultado da marcação:

Na aba **Input/Output** > **Output Parameters**:

| Process Variable Name | Value | Type |
|-----------------------|-------|------|
| `marcacao_sucesso` | `${sucesso}` | Expression |
| `marcacao_mensagem` | `${mensagem}` | Expression |
| `marcacao_timestamp` | `${timestamp_marcacao}` | Expression |

**Ou via XML**:

```xml
<camunda:inputOutput>
  <!-- Input -->
  <camunda:inputParameter name="cod_publicacao">
    ${publicacao_bronze.cod_publicacao}
  </camunda:inputParameter>

  <!-- Output -->
  <camunda:outputParameter name="marcacao_sucesso">${sucesso}</camunda:outputParameter>
  <camunda:outputParameter name="marcacao_mensagem">${mensagem}</camunda:outputParameter>
  <camunda:outputParameter name="marcacao_timestamp">${timestamp_marcacao}</camunda:outputParameter>
</camunda:inputOutput>
```

---

### Exemplo de Fluxo Completo (Individual)

```
┌─────────────────────────────────────────────────────────┐
│ Multi-Instance Loop                                     │
│ Collection: ${publicacoes_ids}                          │
│ Element Variable: publicacao_id                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────┐                   │
│  │ Service Task:                    │                   │
│  │ tratar_publicacao                │                   │
│  │ Topic: tratar_publicacao         │                   │
│  │ Output: publicacao_bronze        │                   │
│  └──────────┬───────────────────────┘                   │
│             │                                            │
│             ▼                                            │
│  ┌──────────────────────────────────┐                   │
│  │ Service Task:                    │                   │
│  │ classificar_publicacao           │                   │
│  │ Topic: classificar_publicacao    │                   │
│  └──────────┬───────────────────────┘                   │
│             │                                            │
│             ▼                                            │
│  ┌──────────────────────────────────┐ ← ADICIONAR AQUI  │
│  │ Service Task:                    │                   │
│  │ Marcar como Exportada no Webjur  │                   │
│  │ Topic: marcar_publicacao_        │                   │
│  │        exportada_webjur          │                   │
│  │ Input: cod_publicacao            │                   │
│  │ Output: marcacao_sucesso         │                   │
│  └──────────┬───────────────────────┘                   │
│             │                                            │
│             ▼                                            │
│  (Continua processo...)                                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Opção 2: Marcação em Lote

### Quando Usar

Use quando você quer marcar **todas as publicações de uma só vez**, após o Multi-Instance Loop terminar.

### Configuração no Camunda Modeler

#### Passo 1: Adicionar Service Task (APÓS Multi-Instance Loop)

1. Arraste um **Service Task** APÓS o Multi-Instance Loop terminar
2. Nomeie: `Marcar Lote como Exportado`
3. ID: `Task_MarcarLoteExportado`

#### Passo 2: Usar Script Task ou HTTP Connector

**Opção A: Script Task (Groovy)**

```xml
<scriptTask id="Task_MarcarLoteExportado" name="Marcar Lote como Exportado" scriptFormat="groovy">
  <script>
    <![CDATA[
    import org.camunda.bpm.engine.impl.util.json.JSONObject
    import java.net.http.*

    def lote_id = execution.getVariable("lote_id")
    def gateway_url = "http://gateway:8000"

    def client = HttpClient.newHttpClient()
    def request = HttpRequest.newBuilder()
        .uri(URI.create("${gateway_url}/marcar-publicacoes/marcar-por-lote/${lote_id}"))
        .POST(HttpRequest.BodyPublishers.noBody())
        .build()

    def response = client.send(request, HttpResponse.BodyHandlers.ofString())
    execution.setVariable("marcacao_lote_response", response.body())
    ]]>
  </script>
</scriptTask>
```

**Opção B: HTTP Connector (Camunda Connector)**

Na aba **Connector**:

- **Connector ID**: `http-connector`
- **HTTP Method**: `POST`
- **URL**: `http://gateway:8000/marcar-publicacoes/marcar-por-lote/${lote_id}`
- **Headers**: `Content-Type: application/json`

---

## Variáveis Disponíveis

### Entrada (`cod_publicacao`)

| Variável | Tipo | Obrigatório | Descrição |
|----------|------|-------------|-----------|
| `cod_publicacao` | int | **SIM** | Código da publicação no Webjur (campo `cod_publicacao` do objeto bronze) |

### Saída (Worker retorna)

| Variável | Tipo | Descrição | Exemplo |
|----------|------|-----------|---------|
| `sucesso` | boolean | Se marcação foi bem-sucedida | `true` |
| `mensagem` | string | Mensagem de sucesso/erro | `"Publicação 123456 marcada como exportada"` |
| `cod_publicacao` | int | Código da publicação marcada | `123456` |
| `timestamp_marcacao` | string (ISO) | Quando foi marcada | `"2025-03-11T21:30:45.123Z"` |
| `mongodb_atualizado` | boolean | Se MongoDB foi atualizado | `true` |
| `erro_validacao` | boolean | Se houve erro de validação | `false` |
| `erro_gateway` | boolean | Se houve erro no Gateway | `false` |
| `erro_webjur` | boolean | Se houve erro na API Webjur | `false` |
| `erro_exception` | boolean | Se houve exceção inesperada | `false` |

---

## Tratamento de Erros

### Comportamento Padrão

⚠️ **IMPORTANTE**: O worker **NÃO falha a tarefa** se a marcação não funcionar. Ele sempre retorna **sucesso** (status `completed`) ao Camunda, mas com `sucesso=false` na variável.

Isso garante que **o processo BPMN continue** mesmo se a marcação falhar (evita travar o fluxo).

### Como Detectar Falhas

Use um **Exclusive Gateway** após a marcação:

```xml
<sequenceFlow sourceRef="Task_MarcarExportadaWebjur" targetRef="Gateway_VerificarMarcacao" />

<exclusiveGateway id="Gateway_VerificarMarcacao" name="Marcação OK?">
  <incoming>...</incoming>
  <outgoing>Flow_Sucesso</outgoing>
  <outgoing>Flow_Erro</outgoing>
</exclusiveGateway>

<sequenceFlow id="Flow_Sucesso" sourceRef="Gateway_VerificarMarcacao" targetRef="Task_Proximo">
  <conditionExpression xsi:type="tFormalExpression">
    ${marcacao_sucesso == true}
  </conditionExpression>
</sequenceFlow>

<sequenceFlow id="Flow_Erro" sourceRef="Gateway_VerificarMarcacao" targetRef="Task_LogarErro">
  <conditionExpression xsi:type="tFormalExpression">
    ${marcacao_sucesso == false}
  </conditionExpression>
</sequenceFlow>
```

### Logs para Monitoramento

```bash
# Logs do Worker (orquestração)
docker logs publicacao-unified-worker 2>&1 | grep "marcar_publicacao_exportada"

# Logs do Gateway (lógica de negócio)
docker logs camunda-worker-api-gateway 2>&1 | grep "Marcando publicação"

# Exemplo de log de sucesso:
# 🏷️ Iniciando marcação de publicação como exportada
# 📋 Marcando publicação 123456 como exportada no Webjur
# ✅ Publicação 123456 marcada com sucesso (MongoDB: 1 doc atualizado)

# Exemplo de log de erro:
# ❌ cod_publicacao não fornecido nas variáveis
# ⚠️ Erro ao chamar Gateway: Connection refused (não bloqueia processo)
```

---

## Testes

### 1. Testar Tópico Diretamente (sem BPMN)

```bash
# Criar task manual no Camunda para testar
curl -X POST http://localhost:8080/engine-rest/process-definition/key/YOUR_PROCESS/submit-form \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "cod_publicacao": {"value": 123456, "type": "Integer"}
    }
  }'
```

### 2. Verificar Worker Subscreveu

```bash
docker logs publicacao-unified-worker 2>&1 | grep "marcar_publicacao_exportada_webjur"

# Deve retornar:
#   • marcar_publicacao_exportada_webjur - Marcação Webjur
```

### 3. Testar Endpoint do Gateway Diretamente

```bash
curl -X POST http://localhost:8000/marcar-publicacoes/processar \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-123",
    "variables": {
      "cod_publicacao": 123456
    }
  }'

# Resposta esperada:
# {
#   "sucesso": true,
#   "mensagem": "Publicação 123456 marcada como exportada",
#   "cod_publicacao": 123456,
#   "timestamp_marcacao": "2025-03-11T21:35:00.000Z",
#   "mongodb_atualizado": true
# }
```

---

## Troubleshooting

### Problema: "cod_publicacao não fornecido"

**Causa**: A variável `publicacao_bronze` não está disponível ou não tem o campo `cod_publicacao`.

**Solução**: Verificar que o Service Task `tratar_publicacao` está retornando o objeto `publicacao_bronze` completo:

```xml
<camunda:outputParameter name="publicacao_bronze">${publicacao}</camunda:outputParameter>
```

### Problema: "Worker não pega tarefa"

**Causa**: Worker não subscreveu ao tópico ou está offline.

**Solução**:

```bash
# 1. Verificar se worker está rodando
docker ps | grep publicacao-unified

# 2. Verificar logs de subscrição
docker logs publicacao-unified-worker 2>&1 | grep "marcar_publicacao"

# 3. Reiniciar worker se necessário
docker restart publicacao-unified-worker
```

### Problema: "Falha na chamada setPublicacoes()"

**Causa**: Credenciais SOAP inválidas ou API Webjur indisponível.

**Solução**:

```bash
# Verificar variáveis de ambiente
docker exec camunda-worker-api-gateway env | grep SOAP

# Deve ter:
# SOAP_USUARIO=100049
# SOAP_SENHA=DcDpW@24
# SOAP_URL=https://intimation-panel.azurewebsites.net/wsPublicacao.asmx

# Testar conexão SOAP diretamente
docker exec camunda-worker-api-gateway python -c "
from app.services.intimation_service import get_intimation_service
client = get_intimation_service()
print('Conexão OK' if client.test_connection() else 'Conexão FALHOU')
"
```

---

## Resumo (TL;DR)

1. **Adicione Service Task** no BPMN com topic `marcar_publicacao_exportada_webjur`
2. **Mapeie variável de entrada**: `cod_publicacao` ← `${publicacao_bronze.cod_publicacao}`
3. **(Opcional) Mapeie saída**: `marcacao_sucesso` ← `${sucesso}`
4. **Deploy BPMN** e execute processo
5. **Monitore logs** para garantir que marcações acontecem
6. **Próxima busca** não retornará publicações já marcadas

---

## Suporte

Em caso de dúvidas:
- **Logs Worker**: `docker logs publicacao-unified-worker`
- **Logs Gateway**: `docker logs camunda-worker-api-gateway`
- **Documentação completa**: Ver `SOLUCAO_PUBLICACOES_REPETIDAS.md`
