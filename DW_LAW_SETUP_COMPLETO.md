# ✅ Setup Completo - Integração DW LAW e-Protocol

**Data**: 2025-11-07
**Status**: ✅ Configurado e Pronto para Uso
**Versão**: 1.0.0

---

## 🔐 Credenciais Configuradas

```yaml
Ambiente: QA/Homologação
URL Base: https://web-eprotocol-integration-cons-qa.azurewebsites.net

Autenticação:
  Email: integ_dias_cons@dwlaw.com.br
  Senha: DC@Dwlaw2025

Projeto:
  Chave: diascostacitacaoconsultaunica
  Nome: Dias Costa - Citação Consulta Única
```

---

## 📁 Arquivos Configurados

### ✅ Gateway (camunda-worker-api-gateway/)

1. **`.env`** - Configuração completa com credenciais DW LAW
   - `DW_LAW_USUARIO=integ_dias_cons@dwlaw.com.br`
   - `DW_LAW_SENHA=DC@Dwlaw2025`
   - `DW_LAW_CHAVE_PROJETO=diascostacitacaoconsultaunica`

2. **`app/core/config.py`** - Settings com defaults configurados
   - Variável `DW_LAW_CHAVE_PROJETO` adicionada

3. **`app/services/dw_law_service.py`** - Serviço de integração
4. **`app/services/camunda_message_service.py`** - Envio de mensagens BPMN
5. **`app/models/dw_law.py`** - Modelos Pydantic
6. **`app/routers/dw_law_router.py`** - Endpoints FastAPI
7. **`app/main.py`** - Router registrado

### ✅ Worker (camunda-workers-platform/)

8. **`workers/dw_law_worker/main.py`** - Worker orquestrador
9. **`workers/dw_law_worker/worker.json`** - Configuração
10. **`workers/dw_law_worker/requirements.txt`** - Dependências
11. **`workers/dw_law_worker/Dockerfile`** - Container
12. **`workers/dw_law_worker/README.md`** - Documentação completa

### ✅ Testes e Documentação

13. **`TEST_DW_LAW_AUTH.md`** - Guia de testes detalhado
14. **`test-scripts/test_dw_law_auth.sh`** - Script automatizado de testes
15. **`DW_LAW_SETUP_COMPLETO.md`** - Este documento

---

## 🚀 Como Iniciar

### Passo 1: Iniciar Serviços

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc
make start-full
```

Aguarde 30-60 segundos para todos os serviços iniciarem.

### Passo 2: Verificar Health

```bash
# Gateway
curl http://localhost:8000/dw-law/health

# Resposta esperada:
# {
#   "status": "healthy",
#   "service": "DW LAW e-Protocol Integration",
#   "timestamp": "..."
# }
```

### Passo 3: Executar Testes Automatizados

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc
./test-scripts/test_dw_law_auth.sh
```

O script executará 5 testes:
1. ✅ Autenticação direta na API DW LAW
2. ✅ Health check do Gateway
3. ✅ Teste de conexões (DW LAW + Camunda)
4. ✅ Inserção de processo de teste
5. ✅ Consulta do processo inserido

---

## 📊 Endpoints Disponíveis

### Gateway - DW LAW

```
Base URL: http://localhost:8000/dw-law

GET  /health              - Health check
GET  /test-connection     - Testar conexões DW LAW e Camunda
POST /inserir-processos   - Inserir processos no monitoramento
POST /excluir-processos   - Excluir processos do monitoramento
POST /consultar-processo  - Consultar processo por chave
POST /callback            - Receber callbacks do DW LAW (webhook)
```

### Worker - Tópicos Camunda

```
INSERIR_PROCESSOS_DW_LAW   - Inserir lista de processos
EXCLUIR_PROCESSOS_DW_LAW   - Excluir lista de processos
CONSULTAR_PROCESSO_DW_LAW  - Consultar processo por chave
```

---

## 🧪 Testes Rápidos

### Teste 1: Autenticação Direta

```bash
curl -X POST 'https://web-eprotocol-integration-cons-qa.azurewebsites.net/api/AUTENTICAR' \
-H 'Content-Type: application/json' \
-d '{
  "usuario": "integ_dias_cons@dwlaw.com.br",
  "senha": "DC@Dwlaw2025"
}'
```

### Teste 2: Testar via Gateway

```bash
curl http://localhost:8000/dw-law/test-connection | jq .
```

### Teste 3: Inserir Processo

```bash
curl -X POST 'http://localhost:8000/dw-law/inserir-processos' \
-H 'Content-Type: application/json' \
-d '{
  "chave_projeto": "diascostacitacaoconsultaunica",
  "processos": [
    {
      "numero_processo": "0012205-60.2015.5.15.0077",
      "other_info_client1": "TESTE_MANUAL"
    }
  ]
}' | jq .
```

---

## 🗄️ MongoDB Collections

```javascript
// Conectar ao MongoDB
mongosh "mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/worker_gateway"

// Ver processos inseridos
db.dw_law_processos.find({
  chave_projeto: "diascostacitacaoconsultaunica"
}).pretty()

// Ver consultas realizadas
db.dw_law_consultas.find().sort({timestamp_consulta: -1}).limit(5).pretty()

// Ver callbacks recebidos
db.dw_law_callbacks.find().sort({timestamp_recebimento: -1}).limit(5).pretty()
```

---

## 📝 Exemplo de Processo BPMN

### Service Task - Inserir Processos

```xml
<serviceTask id="inserir_processos_dw" name="Inserir Processos DW LAW">
  <extensionElements>
    <camunda:inputOutput>
      <camunda:inputParameter name="chave_projeto">diascostacitacaoconsultaunica</camunda:inputParameter>
      <camunda:inputParameter name="processos">
        [
          {
            "numero_processo": "#{numeroProcesso}",
            "other_info_client1": "#{codigoInterno}"
          }
        ]
      </camunda:inputParameter>
    </camunda:inputOutput>
  </extensionElements>
  <property name="type" value="external" />
  <property name="topic" value="INSERIR_PROCESSOS_DW_LAW" />
</serviceTask>
```

### Message Event - Receber Callback

```xml
<intermediateCatchEvent id="aguardar_callback" name="Aguardar Retorno DW LAW">
  <messageEventDefinition messageRef="retorno_dw_law" />
</intermediateCatchEvent>

<message id="retorno_dw_law" name="retorno_dw_law">
  <extensionElements>
    <camunda:property name="businessKey" value="#{numeroProcesso}" />
  </extensionElements>
</message>
```

### Script Task - Processar Retorno

```javascript
// Variáveis disponíveis após callback:
// - dw_law_chave_pesquisa
// - dw_law_numero_processo
// - dw_law_status_pesquisa
// - dw_law_descricao_status
// - dw_law_timestamp_callback

var status = execution.getVariable("dw_law_status_pesquisa");
var descricao = execution.getVariable("dw_law_descricao_status");

if (status === "S") {
  execution.setVariable("processamento_sucesso", true);
  print("✅ Consulta bem-sucedida: " + descricao);
} else {
  execution.setVariable("processamento_sucesso", false);
  print("❌ Erro na consulta: " + descricao);
}
```

---

## 🔄 Configuração de Callback

### URL do Callback

Para receber atualizações automáticas do DW LAW, configure a URL:

**Desenvolvimento (ngrok)**:
```
https://abc123.ngrok.io/dw-law/callback
```

**Produção**:
```
https://seu-dominio.com/dw-law/callback
```

### Como Configurar

**Email para**: suporte@dwrpa.com.br
**Assunto**: Configuração de Callback - e-Protocol Dias Costa

```
Olá,

Gostaria de configurar o callback para o projeto:

Dados do Cliente:
- Empresa: Dias Costa
- Usuário: integ_dias_cons@dwlaw.com.br
- Projeto: diascostacitacaoconsultaunica

URL de Callback:
https://[seu-dominio]/dw-law/callback

Método: POST
Content-Type: application/json

Aguardo confirmação.

Obrigado!
```

---

## 📊 Monitoramento

### Logs do Gateway

```bash
docker logs camunda-worker-api-gateway-gateway-1 -f --tail=100 | grep -i "dw_law"
```

### Logs do Worker

```bash
docker logs dw-law-worker -f --tail=100
```

### Métricas Prometheus

```bash
# Gateway
curl http://localhost:9000/metrics | grep dw_law

# Worker
curl http://localhost:8010/metrics | grep external_task
```

---

## 🆘 Troubleshooting

### Erro: "ERRO_PROJETO_NAO_LOCALIZADO"

**Causa**: Chave do projeto incorreta ou projeto não existe
**Solução**: Verificar com suporte DW LAW se chave `diascostacitacaoconsultaunica` está ativa

### Erro: "ERRO_EMPRESA_INVALIDA"

**Causa**: Credenciais incorretas
**Solução**: Verificar email e senha no `.env`

### Callback não chega

**Causa**: URL não configurada ou inacessível
**Solução**:
1. Testar endpoint: `curl -X POST http://localhost:8000/dw-law/callback -d '{...}'`
2. Verificar firewall/proxy
3. Confirmar URL com suporte DW LAW

### Worker não conecta

**Causa**: Gateway não está rodando ou URL incorreta
**Solução**:
```bash
# Verificar Gateway
docker ps | grep gateway

# Verificar worker.json
cat workers/dw_law_worker/worker.json | grep GATEWAY_URL
# Deve ser: http://camunda-worker-api-gateway-gateway-1:8000
```

---

## 📞 Contatos

### Suporte DW LAW
- **Email**: suporte@dwrpa.com.br
- **Assunto**: [e-Protocol] Dias Costa - [Sua Dúvida]

### Documentação
- **API DW LAW**: Ver `workers/dw_law_worker/README.md`
- **Testes**: Ver `TEST_DW_LAW_AUTH.md`
- **Arquitetura**: Ver `CLAUDE.md` na raiz do projeto

---

## ✅ Checklist Final

- [x] Credenciais configuradas no `.env`
- [x] Gateway com endpoints DW LAW
- [x] Worker com 3 tópicos Camunda
- [x] Models MongoDB (Pydantic)
- [x] Serviço de mensagens BPMN
- [x] Script de testes automatizado
- [x] Documentação completa
- [ ] **Testes executados com sucesso** ⬅️ Próximo passo
- [ ] **Callback configurado no DW LAW** ⬅️ Solicitar ao suporte
- [ ] **Processo BPMN criado** ⬅️ Criar no Camunda Modeler
- [ ] **Teste end-to-end completo** ⬅️ Validar fluxo completo

---

## 🎯 Próximos Passos

1. **Executar testes**:
   ```bash
   ./test-scripts/test_dw_law_auth.sh
   ```

2. **Solicitar configuração de callback** ao suporte DW LAW

3. **Criar processo BPMN** de teste no Camunda

4. **Validar fluxo completo**:
   - Inserir processo via Camunda
   - Aguardar callback
   - Verificar mensagem BPMN recebida
   - Consultar dados completos

---

**🎉 Integração DW LAW e-Protocol configurada e pronta para uso!**

---

**Desenvolvido por**: Claude Code + Dias Costa Team
**Data**: 2025-11-07
**Versão**: 1.0.0
