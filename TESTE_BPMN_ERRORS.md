# Guia de Teste Local - BPMN Errors no Worker Unificado

Este guia explica como testar localmente as modificações feitas no `publicacao_unified` worker, onde todos os erros agora são reportados como **BPMN Errors** ao invés de `fail_task`.

## 📋 Códigos de Erro BPMN Implementados

| Handler | Código de Erro Validação | Código de Erro Processamento |
|---------|--------------------------|------------------------------|
| `handle_nova_publicacao` | `ERRO_VALIDACAO_NOVA_PUBLICACAO` | `ERRO_ORQUESTRACAO_NOVA_PUBLICACAO` |
| `handle_buscar_publicacoes` | `ERRO_VALIDACAO_BUSCA` | `ERRO_BUSCA_PUBLICACOES` |
| `handle_buscar_lote_por_id` | `ERRO_VALIDACAO_LOTE` | `ERRO_BUSCA_LOTE` |
| `handle_tratar_publicacao` | `ERRO_VALIDACAO_TRATAMENTO` | `ERRO_TRATAMENTO_PUBLICACAO` |
| `handle_classificar_publicacao` | `ERRO_VALIDACAO_CLASSIFICACAO` | `ERRO_CLASSIFICACAO` |
| `handle_verificar_processo_cnj` | `ERRO_VALIDACAO_VERIFICACAO_CPJ` | `ERRO_VERIFICACAO_CPJ` |
| `handle_marcar_publicacao_exportada` | `ERRO_VALIDACAO_MARCACAO` | `ERRO_MARCACAO_EXPORTACAO` |

---

## 🚀 Passo 1: Subir o Ambiente Local

### Opção A: Ambiente Core (Plataforma + Workers)
```bash
# No diretório raiz do projeto
make start
```

### Opção B: Ambiente Completo (com Gateway)
```bash
make start-full
```

### Verificar Status
```bash
make status
make health
```

### URLs de Acesso
- **Camunda BPM**: http://localhost:8080 (demo/demo)
- **Grafana**: http://localhost:3001 (admin/admin)
- **Worker Metrics**: http://localhost:8001/metrics

---

## 🔧 Passo 2: Adaptar Processos BPMN com Tratamento de Erros

Os processos BPMN precisam ter **Boundary Error Events** configurados para capturar os BPMN errors.

### 2.1. Abrir Camunda Modeler

Baixe e instale o [Camunda Modeler](https://camunda.com/download/modeler/) se ainda não tiver.

### 2.2. Adicionar Boundary Error Event

1. Abra o arquivo BPMN (ex: `fluxo_publicacao_captura_intimacoes.bpmn`)
2. Selecione uma **Service Task** (ex: "Buscar publicações")
3. Clique no ícone de **chave inglesa** → **Boundary Event** → **Error Boundary Event**
4. Configure o erro:
   - **Error Code**: Use um dos códigos da tabela acima (ex: `ERRO_VALIDACAO_BUSCA`)
   - **Error Message Variable**: `errorMessage`

### 2.3. Exemplo de Configuração BPMN

```xml
<bpmn:serviceTask id="Activity_01sx4ib"
                  name="Buscar publicações"
                  camunda:type="external"
                  camunda:topic="buscar_publicacoes">
  <bpmn:incoming>Flow_0ixo3fl</bpmn:incoming>
  <bpmn:outgoing>Flow_10m1f05</bpmn:outgoing>
</bpmn:serviceTask>

<!-- Boundary Error Event -->
<bpmn:boundaryEvent id="Event_Error_Busca"
                    name="Erro na Busca"
                    attachedToRef="Activity_01sx4ib">
  <bpmn:outgoing>Flow_TratarErro</bpmn:outgoing>
  <bpmn:errorEventDefinition id="ErrorEventDefinition_1"
                             errorRef="Error_Busca" />
</bpmn:boundaryEvent>

<!-- Definição do Erro -->
<bpmn:error id="Error_Busca"
            name="Erro Busca Publicações"
            errorCode="ERRO_BUSCA_PUBLICACOES" />

<!-- Task de Tratamento de Erro -->
<bpmn:userTask id="Task_TratarErro" name="Tratar Erro de Busca">
  <bpmn:incoming>Flow_TratarErro</bpmn:incoming>
  <bpmn:outgoing>Flow_Fim</bpmn:outgoing>
</bpmn:userTask>
```

### 2.4. Deploy do Processo Atualizado

Após adicionar os boundary events, faça o deploy:

**Via Camunda Cockpit:**
1. Acesse http://localhost:8080/camunda/app/cockpit
2. Login: `demo` / `demo`
3. **Deployments** → **Create Deployment**
4. Upload do arquivo `.bpmn` modificado

**Via API REST:**
```bash
curl -X POST http://localhost:8080/camunda/engine-rest/deployment/create \
  -F "deployment-name=fluxo_publicacoes_v2" \
  -F "enable-duplicate-filtering=true" \
  -F "deployment-source=local" \
  -F "file=@camunda-platform-standalone/bpmn/Fluxo_publicacao_captura_intimacoes.bpmn"
```

---

## 🧪 Passo 3: Scripts de Teste

### 3.1. Teste de Erro de Validação

**Teste: `ERRO_VALIDACAO_NOVA_PUBLICACAO` (campo obrigatório ausente)**

```bash
# Script: test_erro_validacao_nova_publicacao.sh
curl -X POST http://localhost:8080/camunda/engine-rest/process-definition/key/fluxo_nova_publicacao/start \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "numero_processo": {"value": "1234567-89.2024.8.13.0024", "type": "String"},
      "data_publicacao": {"value": "01/12/2024", "type": "String"},
      "fonte": {"value": "dw", "type": "String"}
      # FALTANDO: texto_publicacao, tribunal, instancia
    }
  }'
```

**Resultado Esperado:**
- Worker lança `ERRO_VALIDACAO_NOVA_PUBLICACAO`
- Boundary event captura o erro
- Processo vai para task de tratamento de erro
- Logs mostram: `BPMN Error on task XXX: ERRO_VALIDACAO_NOVA_PUBLICACAO`

---

### 3.2. Teste de Erro de Busca

**Teste: `ERRO_VALIDACAO_BUSCA` (parâmetros inválidos)**

```bash
# Script: test_erro_validacao_busca.sh
curl -X POST http://localhost:8080/camunda/engine-rest/process-definition/key/fluxo_buscar_publicacoes_diarias/start \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "cod_grupo": {"value": 5, "type": "Integer"},
      "limite_publicacoes": {"value": 100, "type": "Integer"}
      # limite_publicacoes = 100 (INVÁLIDO, máximo é 50)
    }
  }'
```

**Resultado Esperado:**
- Worker valida `limite_publicacoes > 50`
- Lança `ERRO_VALIDACAO_BUSCA`
- Boundary event captura o erro

---

### 3.3. Teste de Erro de Classificação

**Teste: `ERRO_VALIDACAO_CLASSIFICACAO` (inputs ausentes)**

```bash
# Script: test_erro_validacao_classificacao.sh
curl -X POST http://localhost:8080/camunda/engine-rest/message \
  -H "Content-Type: application/json" \
  -d '{
    "messageName": "classificar_publicacao",
    "processVariables": {
      # FALTANDO: publicacao_id e texto_publicacao
    }
  }'
```

---

### 3.4. Teste de Erro de Verificação CPJ

**Teste: `ERRO_VALIDACAO_VERIFICACAO_CPJ` (numero_cnj ausente)**

```bash
# Script: test_erro_verificacao_cpj.sh
curl -X POST http://localhost:8080/camunda/engine-rest/external-task/fetchAndLock \
  -H "Content-Type: application/json" \
  -d '{
    "workerId": "test-worker",
    "maxTasks": 1,
    "topics": [
      {
        "topicName": "verificar_processo_cnj",
        "lockDuration": 10000
      }
    ]
  }'

# Depois completa com variáveis inválidas
# (numero_cnj ausente)
```

---

## 📊 Passo 4: Monitorar Logs e Validar

### 4.1. Logs do Worker

```bash
# Acompanhar logs do worker em tempo real
docker logs -f publicacao-unified-worker

# Buscar por BPMN errors específicos
docker logs publicacao-unified-worker | grep "BPMN Error"
docker logs publicacao-unified-worker | grep "ERRO_VALIDACAO"
docker logs publicacao-unified-worker | grep "ERRO_CLASSIFICACAO"
```

**Log Esperado:**
```
2024-12-XX XX:XX:XX - CamundaWorker-publicacao-unified-worker - WARNING - BPMN Error on task abc123: ERRO_VALIDACAO_NOVA_PUBLICACAO - Campos obrigatórios ausentes: texto_publicacao, tribunal, instancia
2024-12-XX XX:XX:XX - CamundaWorker-publicacao-unified-worker - INFO - Task abc123 reported BPMN error: ERRO_VALIDACAO_NOVA_PUBLICACAO
```

### 4.2. Camunda Cockpit

1. Acesse http://localhost:8080/camunda/app/cockpit
2. **Processes** → Selecione o processo de teste
3. **Process Instances** → Veja as instâncias em execução
4. Clique em uma instância para ver:
   - **Incidents**: Devem estar vazios (não há incidents técnicos)
   - **Activity History**: Deve mostrar o boundary error event ativado
   - **Variables**: Deve conter `errorMessage` com a mensagem de erro

### 4.3. Verificar Métricas Prometheus

```bash
# Acessar métricas do worker
curl http://localhost:8001/metrics | grep camunda_tasks_total
```

Procure por métricas como:
```
camunda_tasks_total{topic="nova_publicacao",status="gateway_success"} X
camunda_tasks_total{topic="buscar_publicacoes",status="gateway_failure"} Y
```

---

## ✅ Checklist de Validação

### Para Cada Handler:

- [ ] **Erro de Validação**
  - [ ] Submeter payload sem campos obrigatórios
  - [ ] Verificar que `ERRO_VALIDACAO_*` é lançado
  - [ ] Confirmar que boundary event captura o erro
  - [ ] Validar mensagem de erro no Cockpit

- [ ] **Erro de Processamento**
  - [ ] Simular erro inesperado (ex: Gateway offline)
  - [ ] Verificar que `ERRO_*` (processamento) é lançado
  - [ ] Confirmar captura pelo boundary event
  - [ ] Validar logs do worker

- [ ] **Sem Retry**
  - [ ] Confirmar que task NÃO entra em retry loop
  - [ ] Erro vai direto para boundary event
  - [ ] Não aparecem incidents no Cockpit

---

## 🐛 Troubleshooting

### Problema: Erro não é capturado pelo Boundary Event

**Causa:** Código de erro no BPMN não corresponde ao código no worker

**Solução:**
1. Verificar no Camunda Modeler: erro configurado como `ERRO_VALIDACAO_BUSCA`
2. Verificar no código: `error_code="ERRO_VALIDACAO_BUSCA"`
3. Códigos devem ser **exatamente iguais** (case-sensitive)

### Problema: Worker não inicia

**Causa:** Container não está rodando ou variáveis de ambiente incorretas

**Solução:**
```bash
# Verificar status do container
docker ps | grep publicacao-unified

# Verificar logs de inicialização
docker logs publicacao-unified-worker | head -50

# Reconstruir e reiniciar
cd camunda-workers-platform
make build-workers
docker-compose restart publicacao-unified-worker
```

### Problema: Gateway timeout

**Causa:** Gateway não está rodando ou worker não consegue conectar

**Solução:**
```bash
# Verificar se Gateway está rodando
docker ps | grep gateway

# Verificar conectividade
docker exec publicacao-unified-worker ping camunda-worker-api-gateway-gateway-1

# Verificar variável GATEWAY_URL no worker
docker exec publicacao-unified-worker env | grep GATEWAY_URL
```

---

## 📝 Exemplo Completo de Teste

### Criar Processo BPMN de Teste

Crie um arquivo `test_bpmn_errors.bpmn` com:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:camunda="http://camunda.org/schema/1.0/bpmn">

  <bpmn:process id="test_nova_publicacao" name="Teste Nova Publicação" isExecutable="true">

    <bpmn:startEvent id="start" />

    <bpmn:serviceTask id="task_nova_pub"
                      name="Processar Nova Publicação"
                      camunda:type="external"
                      camunda:topic="nova_publicacao">
      <bpmn:incoming>start_to_task</bpmn:incoming>
      <bpmn:outgoing>task_to_end</bpmn:outgoing>
    </bpmn:serviceTask>

    <!-- Captura ERRO_VALIDACAO -->
    <bpmn:boundaryEvent id="erro_validacao"
                        name="Erro Validação"
                        attachedToRef="task_nova_pub">
      <bpmn:outgoing>validacao_to_user</bpmn:outgoing>
      <bpmn:errorEventDefinition errorRef="Error_Validacao" />
    </bpmn:boundaryEvent>

    <!-- Captura ERRO_ORQUESTRACAO -->
    <bpmn:boundaryEvent id="erro_orquestracao"
                        name="Erro Orquestração"
                        attachedToRef="task_nova_pub">
      <bpmn:outgoing>orquestracao_to_user</bpmn:outgoing>
      <bpmn:errorEventDefinition errorRef="Error_Orquestracao" />
    </bpmn:boundaryEvent>

    <bpmn:userTask id="user_corrigir_validacao"
                   name="Corrigir Dados de Validação">
      <bpmn:incoming>validacao_to_user</bpmn:incoming>
      <bpmn:outgoing>correcao_to_end</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:userTask id="user_analisar_erro"
                   name="Analisar Erro de Orquestração">
      <bpmn:incoming>orquestracao_to_user</bpmn:incoming>
      <bpmn:outgoing>analise_to_end</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:endEvent id="end_sucesso" />
    <bpmn:endEvent id="end_erro_validacao" />
    <bpmn:endEvent id="end_erro_orquestracao" />

    <bpmn:sequenceFlow id="start_to_task" sourceRef="start" targetRef="task_nova_pub" />
    <bpmn:sequenceFlow id="task_to_end" sourceRef="task_nova_pub" targetRef="end_sucesso" />
    <bpmn:sequenceFlow id="validacao_to_user" sourceRef="erro_validacao" targetRef="user_corrigir_validacao" />
    <bpmn:sequenceFlow id="orquestracao_to_user" sourceRef="erro_orquestracao" targetRef="user_analisar_erro" />
    <bpmn:sequenceFlow id="correcao_to_end" sourceRef="user_corrigir_validacao" targetRef="end_erro_validacao" />
    <bpmn:sequenceFlow id="analise_to_end" sourceRef="user_analisar_erro" targetRef="end_erro_orquestracao" />

  </bpmn:process>

  <bpmn:error id="Error_Validacao"
              name="Erro Validação Nova Publicação"
              errorCode="ERRO_VALIDACAO_NOVA_PUBLICACAO" />

  <bpmn:error id="Error_Orquestracao"
              name="Erro Orquestração Nova Publicação"
              errorCode="ERRO_ORQUESTRACAO_NOVA_PUBLICACAO" />

</bpmn:definitions>
```

### Testar

```bash
# 1. Deploy do processo
curl -X POST http://localhost:8080/camunda/engine-rest/deployment/create \
  -F "file=@test_bpmn_errors.bpmn"

# 2. Iniciar instância com dados INVÁLIDOS (vai gerar ERRO_VALIDACAO)
curl -X POST http://localhost:8080/camunda/engine-rest/process-definition/key/test_nova_publicacao/start \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "numero_processo": {"value": "1234567-89.2024.8.13.0024", "type": "String"}
    }
  }'

# 3. Verificar no Cockpit que uma User Task "Corrigir Dados de Validação" foi criada

# 4. Verificar logs
docker logs publicacao-unified-worker | grep "ERRO_VALIDACAO_NOVA_PUBLICACAO"
```

---

## 📚 Referências

- [Camunda BPMN Error Events](https://docs.camunda.org/manual/latest/reference/bpmn20/events/error-events/)
- [External Task Error Handling](https://docs.camunda.org/manual/latest/user-guide/process-engine/external-tasks/#error-handling)
- [Worker API Base Class](camunda-workers-platform/workers/common/base_worker.py:588-615)
