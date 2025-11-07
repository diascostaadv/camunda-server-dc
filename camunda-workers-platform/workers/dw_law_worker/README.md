# DW LAW e-Protocol Worker

Worker para integração com a API DW LAW e-Protocol - Sistema de Consulta Processual.

## 📋 Visão Geral

Este worker implementa a integração completa com a API DW LAW e-Protocol, permitindo:

- **Inserir Processos**: Adiciona processos ao monitoramento DW LAW
- **Excluir Processos**: Remove processos do monitoramento
- **Consultar Processos**: Obtém dados completos de processos por chave de pesquisa
- **Receber Callbacks**: Processa atualizações via webhook e envia mensagens BPMN ao Camunda

## 🏗️ Arquitetura

### Padrão de Orquestração

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────┐
│   Camunda   │─────>│  DW LAW      │─────>│  Gateway    │─────>│ DW LAW   │
│   Process   │      │  Worker      │      │  API        │      │   API    │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────┘
      ▲                                            │
      │                                            ▼
      │                                     ┌─────────────┐
      │                                     │  MongoDB    │
      │                                     │  Storage    │
      │                                     └─────────────┘
      │
      │               ┌──────────────┐
      └───────────────│   Callback   │
        (Message)     │   Webhook    │
                      └──────────────┘
```

### Fluxo de Dados

1. **Processo Camunda** executa task em um dos tópicos
2. **Worker** captura task, valida inputs e delega ao Gateway
3. **Gateway** chama API DW LAW, salva no MongoDB e retorna resultado
4. **Worker** completa task no Camunda com os dados retornados
5. **DW LAW** envia callback para o Gateway quando há atualizações
6. **Gateway** salva callback e envia mensagem BPMN para Camunda
7. **Camunda** correlaciona mensagem e continua processo

## 📝 Tópicos Suportados

### 1. INSERIR_PROCESSOS_DW_LAW

Insere uma lista de processos no monitoramento DW LAW.

**Payload de Entrada:**
```json
{
  "chave_projeto": "04b0cdc7-afd1-496d-a220-35a607bfcd42",
  "processos": [
    {
      "numero_processo": "0012205-60.2015.5.15.0077",
      "other_info_client1": "CODIGO_INTERNO_123",
      "other_info_client2": "PASTA_456"
    },
    {
      "numero_processo": "1000655-90.2016.5.02.0008",
      "other_info_client1": "CODIGO_INTERNO_124",
      "other_info_client2": "PASTA_457"
    }
  ]
}
```

**Variáveis de Retorno:**
```json
{
  "success": true,
  "message": "2 processos inseridos com sucesso",
  "data": {
    "chave_projeto": "04b0cdc7-afd1-496d-a220-35a607bfcd42",
    "total_inseridos": 2,
    "processos": [
      {
        "numero_processo": "0012205-60.2015.5.15.0077",
        "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169",
        "tribunal": "TJPB",
        "sistema": "PJE",
        "instancia": "1"
      }
    ],
    "retorno": "SUCESSO"
  }
}
```

**Códigos de Erro BPMN:**
- `ERRO_VALIDACAO_INTEGRACAO_DW`: Campos obrigatórios ausentes ou inválidos
- `ERRO_PROCESSAMENTO_INTEGRACAO_DW`: Erro no processamento
- `ERRO_CONFIGURACAO_INTEGRACAO_DW`: Configuração incorreta

### 2. EXCLUIR_PROCESSOS_DW_LAW

Exclui processos do monitoramento DW LAW.

**Payload de Entrada:**
```json
{
  "chave_projeto": "04b0cdc7-afd1-496d-a220-35a607bfcd42",
  "lista_de_processos": [
    {
      "numero_processo": "0012205-60.2015.5.15.0077"
    },
    {
      "numero_processo": "1000655-90.2016.5.02.0008"
    }
  ]
}
```

**Variáveis de Retorno:**
```json
{
  "success": true,
  "message": "2 processos excluídos com sucesso",
  "data": {
    "chave_projeto": "04b0cdc7-afd1-496d-a220-35a607bfcd42",
    "total_excluidos": 2,
    "processos": [
      {
        "numero_processo": "0012205-60.2015.5.15.0077",
        "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169"
      }
    ],
    "retorno": "SUCESSO"
  }
}
```

### 3. CONSULTAR_PROCESSO_DW_LAW

Consulta dados completos de um processo por chave de pesquisa.

**Payload de Entrada:**
```json
{
  "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169"
}
```

**Variáveis de Retorno:**
```json
{
  "success": true,
  "message": "Processo consultado com sucesso",
  "data": {
    "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169",
    "numero_processo": "0329056-75.2017.8.13.0000",
    "status_pesquisa": "S",
    "descricao_status_pesquisa": "Consulta realizada com sucesso",
    "classe_judicial": "Agravo de Instrumento-Cv",
    "assunto": "Inadimplemento < Obrigações < DIREITO CIVIL",
    "valor": "R$ 13.650,92",
    "citacao": "S",
    "indicio_citacao": "28/08/2025 - Texto exemplo do andamento...",
    "polos": [...],
    "movimentacoes": [...],
    "audiencias": [...]
  }
}
```

## 🔄 Callback Webhook

O DW LAW envia callbacks automaticamente quando há atualizações nos processos.

**URL do Callback:**
```
POST http://<gateway-url>/dw-law/callback
```

**Payload do Callback (enviado pelo DW LAW):**
```json
{
  "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169",
  "numero_processo": "0329056-75.2017.8.13.0000",
  "status_pesquisa": "S",
  "descricao_status_pesquisa": "Consulta realizada com sucesso",
  "classe_judicial": "...",
  "polos": [...],
  "movimentacoes": [...]
}
```

**Processamento do Callback:**

1. Gateway salva callback completo no MongoDB
2. Busca `camunda_business_key` do processo
3. Envia mensagem BPMN `retorno_dw_law` para Camunda:

```bash
curl --location 'http://camunda:8080/engine-rest/message' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic ZGVtbzpEaWFzQ29zdGFAISEyMDI1' \
--data '{
  "messageName": "retorno_dw_law",
  "businessKey": "0329056-75.2017.8.13.0000",
  "processVariables": {
    "dw_law_chave_pesquisa": { "value": "2c15b4ba-...", "type": "String" },
    "dw_law_numero_processo": { "value": "0329056-...", "type": "String" },
    "dw_law_status_pesquisa": { "value": "S", "type": "String" },
    "dw_law_descricao_status": { "value": "Consulta realizada...", "type": "String" },
    "dw_law_timestamp_callback": { "value": "2025-11-07T...", "type": "String" }
  }
}'
```

## ⚙️ Configuração

### Variáveis de Ambiente (Gateway)

```env
# DW LAW API
DW_LAW_BASE_URL=https://web-eprotocol-integration-cons-qa.azurewebsites.net
DW_LAW_USUARIO=usuario@email.com
DW_LAW_SENHA=senha_secreta
DW_LAW_TOKEN_EXPIRY_MINUTES=120
DW_LAW_TIMEOUT=120

# Camunda REST API
CAMUNDA_REST_URL=http://camunda:8080/engine-rest
CAMUNDA_REST_USER=demo
CAMUNDA_REST_PASSWORD=DiasCostaA!!2025

# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=worker_gateway
```

### Variáveis de Ambiente (Worker)

```env
GATEWAY_ENABLED=true
GATEWAY_URL=http://camunda-worker-api-gateway-gateway-1:8000
GATEWAY_TIMEOUT=120
CAMUNDA_URL=http://camunda:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=DiasCosta@!!2025
MAX_TASKS=3
LOCK_DURATION=120000
```

## 🗄️ Collections MongoDB

### dw_law_processos
Armazena processos inseridos no DW LAW.

```json
{
  "_id": "ObjectId",
  "chave_projeto": "04b0cdc7-afd1-496d-a220-35a607bfcd42",
  "numero_processo": "0012205-60.2015.5.15.0077",
  "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169",
  "tribunal": "TJPB",
  "sistema": "PJE",
  "instancia": "1",
  "status": "inserido",
  "timestamp_insercao": "2025-11-07T10:00:00",
  "camunda_instance_id": "abc123",
  "camunda_business_key": "0012205-60.2015.5.15.0077"
}
```

### dw_law_consultas
Armazena resultados de consultas processsuais.

```json
{
  "_id": "ObjectId",
  "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169",
  "numero_processo": "0329056-75.2017.8.13.0000",
  "status_pesquisa": "S",
  "classe_judicial": "...",
  "polos": [...],
  "movimentacoes": [...],
  "audiencias": [...],
  "timestamp_consulta": "2025-11-07T11:00:00"
}
```

### dw_law_callbacks
Armazena callbacks recebidos do DW LAW.

```json
{
  "_id": "ObjectId",
  "payload_completo": {...},
  "chave_de_pesquisa": "2c15b4ba-475d-447b-ae78-94ab7e29c169",
  "numero_processo": "0329056-75.2017.8.13.0000",
  "status_pesquisa": "S",
  "timestamp_recebimento": "2025-11-07T12:00:00",
  "processado": true,
  "mensagem_camunda_enviada": true,
  "camunda_business_key": "0329056-75.2017.8.13.0000"
}
```

## 🚀 Deploy

### Local (Docker Compose)
```bash
cd camunda-workers-platform
make local-up
```

### Produção (Docker Swarm)
```bash
make deploy
make scale-worker W=dw-law-worker N=2
```

## 📊 Monitoramento

### Métricas Prometheus
```
http://localhost:8010/metrics
```

### Health Check
```
http://localhost:8010/health
```

### Logs
```bash
docker logs dw-law-worker -f
```

## 🧪 Testes

### Testar Conexões
```bash
curl http://localhost:8000/dw-law/test-connection
```

### Simular Callback
```bash
curl -X POST http://localhost:8000/dw-law/callback \
-H "Content-Type: application/json" \
-d '{
  "chave_de_pesquisa": "test-123",
  "numero_processo": "1234567-89.2024.1.01.0001",
  "status_pesquisa": "S",
  "descricao_status_pesquisa": "Teste"
}'
```

## 📚 Documentação Adicional

- [API DW LAW e-Protocol](./DW_LAW_API_DOCS.pdf)
- [Worker Architecture](../../docs/WORKER_ARCHITECTURE.md)
- [Gateway Integration](../../docs/GATEWAY_INTEGRATION.md)

## 🐛 Troubleshooting

### Worker não conecta ao Camunda
```bash
# Verificar conectividade
docker exec dw-law-worker curl http://camunda:8080/engine-rest/version

# Verificar variáveis de ambiente
docker exec dw-law-worker env | grep CAMUNDA
```

### Gateway não conecta ao DW LAW
```bash
# Testar autenticação
curl http://localhost:8000/dw-law/test-connection

# Verificar logs do Gateway
docker logs camunda-worker-api-gateway-gateway-1 -f --tail=100
```

### Callbacks não estão chegando
1. Verificar URL do callback configurada no DW LAW
2. Verificar firewall/port forwarding
3. Testar endpoint manualmente (curl)
4. Verificar logs do MongoDB

## 📞 Suporte

Para dúvidas ou problemas, contate:
- Email: suporte@diascosta.com.br
- Documentação: https://docs.diascosta.com.br
