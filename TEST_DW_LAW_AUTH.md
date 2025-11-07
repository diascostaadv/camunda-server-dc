# 🧪 Teste de Autenticação DW LAW

## ✅ Credenciais Configuradas

```
Email: integ_dias_cons@dwlaw.com.br
Senha: DC@Dwlaw2025
Chave Projeto: diascostacitacaoconsultaunica
```

## 🔍 Teste 1: Autenticação Direta na API DW LAW

Teste a autenticação diretamente na API DW LAW:

```bash
curl -X POST 'https://web-eprotocol-integration-cons-qa.azurewebsites.net/api/AUTENTICAR' \
-H 'Content-Type: application/json' \
-d '{
  "usuario": "integ_dias_cons@dwlaw.com.br",
  "senha": "DC@Dwlaw2025"
}'
```

**Resposta Esperada:**
```json
{
  "usuario": "integ_dias_cons@dwlaw.com.br",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "obs": "Solicitação efetuada com sucesso"
}
```

---

## 🔍 Teste 2: Testar via Gateway (Após Iniciar Serviços)

### Passo 1: Iniciar Serviços
```bash
cd camunda-server-dc
make start-full
```

### Passo 2: Aguardar Inicialização (30-60 segundos)
```bash
# Verificar se Gateway está rodando
curl http://localhost:8000/dw-law/health

# Deve retornar:
# {
#   "status": "healthy",
#   "service": "DW LAW e-Protocol Integration",
#   "timestamp": "..."
# }
```

### Passo 3: Testar Conexão e Autenticação
```bash
curl http://localhost:8000/dw-law/test-connection
```

**Resposta Esperada:**
```json
{
  "success": true,
  "dw_law": {
    "authenticated": true,
    "token_info": {
      "has_token": true,
      "usuario": "integ_dias_cons@dwlaw.com.br",
      "expires_at": "2025-11-07T14:00:00",
      "is_valid": true
    }
  },
  "camunda": {
    "success": true,
    "version": {
      "version": "7.21.0"
    }
  }
}
```

---

## 🔍 Teste 3: Inserir Processos de Teste

```bash
curl -X POST 'http://localhost:8000/dw-law/inserir-processos' \
-H 'Content-Type: application/json' \
-d '{
  "chave_projeto": "diascostacitacaoconsultaunica",
  "processos": [
    {
      "numero_processo": "0012205-60.2015.5.15.0077",
      "other_info_client1": "TESTE_AUTENTICACAO",
      "other_info_client2": "PRIMEIRA_INSERCAO"
    }
  ],
  "camunda_business_key": "teste-auth-001"
}'
```

**Resposta Esperada (Sucesso):**
```json
{
  "success": true,
  "message": "1 processos inseridos com sucesso",
  "data": {
    "chave_projeto": "diascostacitacaoconsultaunica",
    "total_inseridos": 1,
    "processos": [
      {
        "numero_processo": "0012205-60.2015.5.15.0077",
        "chave_de_pesquisa": "UUID-GERADO-PELO-DW-LAW",
        "tribunal": "TJPB",
        "sistema": "PJE",
        "instancia": "1"
      }
    ],
    "retorno": "SUCESSO"
  },
  "timestamp": "2025-11-07T12:00:00"
}
```

**Possíveis Erros:**

1. **Erro de Autenticação (401):**
```json
{
  "success": false,
  "error": "DW_LAW_ERROR",
  "message": "Erro na autenticação DW LAW: ..."
}
```
➡️ **Solução**: Verificar credenciais no `.env`

2. **Erro de Projeto Inválido (400):**
```json
{
  "success": false,
  "data": {
    "retorno": "ERRO_PROJETO_NAO_LOCALIZADO",
    "obs": "Projeto não localizado."
  }
}
```
➡️ **Solução**: Verificar `DW_LAW_CHAVE_PROJETO` ou solicitar chave correta ao suporte DW LAW

3. **Timeout:**
```json
{
  "success": false,
  "error": "DW_LAW_ERROR",
  "message": "Timeout ao inserir processos"
}
```
➡️ **Solução**: Aumentar `DW_LAW_TIMEOUT` no `.env`

---

## 🔍 Teste 4: Consultar Processo Inserido

Após inserir um processo, você receberá uma `chave_de_pesquisa`. Use-a para consultar:

```bash
curl -X POST 'http://localhost:8000/dw-law/consultar-processo' \
-H 'Content-Type: application/json' \
-d '{
  "chave_de_pesquisa": "UUID-RECEBIDO-NA-INSERCAO"
}'
```

**Resposta Esperada:**
```json
{
  "success": true,
  "message": "Processo consultado com sucesso",
  "data": {
    "chave_de_pesquisa": "UUID-RECEBIDO-NA-INSERCAO",
    "numero_processo": "0012205-60.2015.5.15.0077",
    "status_pesquisa": "S",
    "descricao_status_pesquisa": "Consulta realizada com sucesso",
    "classe_judicial": "...",
    "assunto": "...",
    "valor": "R$ ...",
    "citacao": "S",
    "polos": [...],
    "movimentacoes": [...],
    "audiencias": [...]
  }
}
```

---

## 🔍 Teste 5: Verificar MongoDB

```bash
# Conectar ao MongoDB
mongosh "mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/worker_gateway"

# OU se estiver rodando localmente:
docker exec -it <mongodb-container> mongosh worker_gateway
```

### Ver Processos Inseridos
```javascript
db.dw_law_processos.find({
  chave_projeto: "diascostacitacaoconsultaunica"
}).pretty()
```

### Ver Consultas Realizadas
```javascript
db.dw_law_consultas.find().sort({timestamp_consulta: -1}).limit(5).pretty()
```

### Ver Callbacks Recebidos
```javascript
db.dw_law_callbacks.find().sort({timestamp_recebimento: -1}).limit(5).pretty()
```

---

## 🔍 Teste 6: Logs do Sistema

### Logs do Gateway
```bash
docker logs camunda-worker-api-gateway-gateway-1 -f --tail=100 | grep -i "dw_law"
```

**Logs Esperados:**
```
DWLawService inicializado - Base URL: https://web-eprotocol-integration-cons-qa.azurewebsites.net
🔐 Autenticando no DW LAW e-Protocol...
✅ Autenticação DW LAW bem-sucedida - Token válido até 2025-11-07T14:00:00
📤 Inserindo 1 processos no DW LAW - Projeto: diascostacitacaoconsultaunica
✅ Inserção DW LAW concluída - Retorno: SUCESSO
```

### Logs do Worker (quando testar via Camunda)
```bash
docker logs dw-law-worker -f --tail=100
```

---

## 📋 Checklist de Validação

- [ ] **Teste 1**: Autenticação direta na API DW LAW funcionando
- [ ] **Teste 2**: Gateway respondendo em `/dw-law/health`
- [ ] **Teste 3**: `/test-connection` retorna sucesso para DW LAW e Camunda
- [ ] **Teste 4**: Inserção de processos retorna sucesso
- [ ] **Teste 5**: Consulta de processo retorna dados completos
- [ ] **Teste 6**: MongoDB armazenando dados corretamente
- [ ] **Teste 7**: Logs sem erros de autenticação
- [ ] **Callback**: URL configurada no DW LAW (solicitar ao suporte)

---

## 🆘 Troubleshooting

### Erro: "Unable to import 'camunda.external_task.external_task'"
Isso é apenas um warning do linter. Os imports funcionam em runtime porque o PYTHONPATH é configurado no Docker.

**Não afeta o funcionamento!**

### Erro: "Connection refused" ao acessar Gateway
```bash
# Verificar se Gateway está rodando
docker ps | grep gateway

# Se não estiver, iniciar:
cd camunda-server-dc
make start-full
```

### Erro: "ERRO_EMPRESA_INVALIDA"
Significa que as credenciais estão incorretas ou a empresa não existe no ambiente DW LAW.

**Solução**:
1. Verificar se está usando ambiente correto (QA vs Produção)
2. Confirmar credenciais com suporte DW LAW

### Erro: "ERRO_PROJETO_NAO_LOCALIZADO"
A `chave_projeto` não existe ou está incorreta.

**Solução**:
1. Confirmar chave com suporte DW LAW
2. Verificar se projeto foi criado no painel e-Protocol

---

## 📞 Suporte DW LAW

Se encontrar problemas com autenticação ou chave do projeto:

**Email**: suporte@dwrpa.com.br
**Assunto**: Validação de Credenciais - e-Protocol Dias Costa

**Corpo do Email**:
```
Olá,

Estou integrando o sistema e-Protocol via API e gostaria de confirmar:

1. As credenciais de acesso:
   - Usuário: integ_dias_cons@dwlaw.com.br
   - Ambiente: QA (https://web-eprotocol-integration-cons-qa.azurewebsites.net)

2. A chave do projeto:
   - Chave: diascostacitacaoconsultaunica
   - Projeto existe e está ativo?

3. Configuração de Callback:
   - Necessito configurar URL de callback para receber atualizações
   - URL será: https://[seu-dominio]/dw-law/callback
   - Quando posso enviar a URL definitiva?

Aguardo retorno.

Obrigado!
```

---

## ✅ Próximos Passos Após Validação

1. ✅ Autenticação funcionando
2. ✅ Inserção de processos funcionando
3. ✅ Consulta de processos funcionando
4. 🔄 Configurar URL de callback (ver documentação anterior)
5. 🔄 Criar processo BPMN de teste no Camunda
6. 🔄 Testar fluxo end-to-end completo

---

**Data de Configuração**: 2025-11-07
**Versão**: 1.0.0
**Status**: ✅ Configurado e Pronto para Teste
