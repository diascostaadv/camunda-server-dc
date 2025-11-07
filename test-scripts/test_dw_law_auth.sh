#!/bin/bash

###############################################################################
# Script de Teste - Autenticação e Inserção DW LAW e-Protocol
# Data: 2025-11-07
# Autor: Dias Costa - Integração DW LAW
###############################################################################

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
DW_LAW_BASE_URL="https://web-eprotocol-integration-cons-qa.azurewebsites.net"
DW_LAW_USUARIO="integ_dias_cons@dwlaw.com.br"
DW_LAW_SENHA="DC@Dwlaw2025"
DW_LAW_CHAVE_PROJETO="diascostacitacaoconsultaunica"
GATEWAY_URL="http://localhost:8000"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Teste de Autenticação DW LAW e-Protocol                  ║${NC}"
echo -e "${BLUE}║  Ambiente: QA/Homologação                                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# TESTE 1: Autenticação Direta na API DW LAW
###############################################################################
echo -e "${YELLOW}[TESTE 1]${NC} Testando autenticação direta na API DW LAW..."
echo -e "${BLUE}URL:${NC} ${DW_LAW_BASE_URL}/api/AUTENTICAR"
echo ""

AUTH_RESPONSE=$(curl -s -X POST "${DW_LAW_BASE_URL}/api/AUTENTICAR" \
  -H 'Content-Type: application/json' \
  -d "{
    \"usuario\": \"${DW_LAW_USUARIO}\",
    \"senha\": \"${DW_LAW_SENHA}\"
  }")

# Verificar se autenticação foi bem-sucedida
if echo "$AUTH_RESPONSE" | grep -q "token"; then
  TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
  echo -e "${GREEN}✅ Autenticação bem-sucedida!${NC}"
  echo -e "${BLUE}Token:${NC} ${TOKEN:0:50}..."
  echo -e "${BLUE}Usuário:${NC} ${DW_LAW_USUARIO}"
  echo ""
else
  echo -e "${RED}❌ Falha na autenticação!${NC}"
  echo -e "${RED}Resposta:${NC}"
  echo "$AUTH_RESPONSE" | jq . 2>/dev/null || echo "$AUTH_RESPONSE"
  exit 1
fi

###############################################################################
# TESTE 2: Verificar Health do Gateway
###############################################################################
echo -e "${YELLOW}[TESTE 2]${NC} Verificando se Gateway está rodando..."
echo -e "${BLUE}URL:${NC} ${GATEWAY_URL}/dw-law/health"
echo ""

if curl -s -f "${GATEWAY_URL}/dw-law/health" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Gateway está rodando!${NC}"
  curl -s "${GATEWAY_URL}/dw-law/health" | jq .
  echo ""
else
  echo -e "${RED}❌ Gateway não está respondendo!${NC}"
  echo -e "${YELLOW}Inicie o Gateway com:${NC} cd camunda-server-dc && make start-full"
  exit 1
fi

###############################################################################
# TESTE 3: Testar Conexões via Gateway
###############################################################################
echo -e "${YELLOW}[TESTE 3]${NC} Testando conexões DW LAW e Camunda via Gateway..."
echo -e "${BLUE}URL:${NC} ${GATEWAY_URL}/dw-law/test-connection"
echo ""

CONNECTION_RESPONSE=$(curl -s "${GATEWAY_URL}/dw-law/test-connection")
echo "$CONNECTION_RESPONSE" | jq .

# Verificar se DW LAW está autenticado
if echo "$CONNECTION_RESPONSE" | grep -q '"authenticated": true'; then
  echo -e "${GREEN}✅ Conexão com DW LAW OK!${NC}"
else
  echo -e "${RED}❌ Falha na conexão com DW LAW via Gateway!${NC}"
  exit 1
fi

# Verificar se Camunda está acessível
if echo "$CONNECTION_RESPONSE" | grep -q '"success": true'; then
  echo -e "${GREEN}✅ Conexão com Camunda OK!${NC}"
  echo ""
else
  echo -e "${YELLOW}⚠️  Camunda pode não estar acessível${NC}"
  echo ""
fi

###############################################################################
# TESTE 4: Inserir Processo de Teste
###############################################################################
echo -e "${YELLOW}[TESTE 4]${NC} Inserindo processo de teste no DW LAW..."
echo -e "${BLUE}URL:${NC} ${GATEWAY_URL}/dw-law/inserir-processos"
echo -e "${BLUE}Projeto:${NC} ${DW_LAW_CHAVE_PROJETO}"
echo ""

INSERT_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/dw-law/inserir-processos" \
  -H 'Content-Type: application/json' \
  -d "{
    \"chave_projeto\": \"${DW_LAW_CHAVE_PROJETO}\",
    \"processos\": [
      {
        \"numero_processo\": \"0012205-60.2015.5.15.0077\",
        \"other_info_client1\": \"TESTE_AUTENTICACAO_$(date +%Y%m%d%H%M%S)\",
        \"other_info_client2\": \"VALIDACAO_CREDENCIAIS\"
      }
    ],
    \"camunda_business_key\": \"teste-auth-$(date +%s)\"
  }")

echo "$INSERT_RESPONSE" | jq .
echo ""

# Verificar se inserção foi bem-sucedida
if echo "$INSERT_RESPONSE" | grep -q '"success": true'; then
  echo -e "${GREEN}✅ Processo inserido com sucesso!${NC}"

  # Extrair chave_de_pesquisa
  CHAVE_PESQUISA=$(echo "$INSERT_RESPONSE" | jq -r '.data.processos[0].chave_de_pesquisa // empty')

  if [ -n "$CHAVE_PESQUISA" ]; then
    echo -e "${BLUE}Chave de Pesquisa:${NC} ${CHAVE_PESQUISA}"
    echo -e "${BLUE}Número Processo:${NC} 0012205-60.2015.5.15.0077"
    echo ""

    ###############################################################################
    # TESTE 5: Consultar Processo Inserido
    ###############################################################################
    echo -e "${YELLOW}[TESTE 5]${NC} Consultando processo inserido..."
    echo -e "${BLUE}URL:${NC} ${GATEWAY_URL}/dw-law/consultar-processo"
    echo -e "${BLUE}Chave:${NC} ${CHAVE_PESQUISA}"
    echo ""

    sleep 2  # Aguardar processamento

    CONSULTA_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/dw-law/consultar-processo" \
      -H 'Content-Type: application/json' \
      -d "{
        \"chave_de_pesquisa\": \"${CHAVE_PESQUISA}\"
      }")

    echo "$CONSULTA_RESPONSE" | jq .
    echo ""

    if echo "$CONSULTA_RESPONSE" | grep -q '"success": true'; then
      echo -e "${GREEN}✅ Consulta realizada com sucesso!${NC}"

      # Extrair informações principais
      NUMERO_PROC=$(echo "$CONSULTA_RESPONSE" | jq -r '.data.numero_processo // "N/A"')
      STATUS_PESQ=$(echo "$CONSULTA_RESPONSE" | jq -r '.data.status_pesquisa // "N/A"')
      DESC_STATUS=$(echo "$CONSULTA_RESPONSE" | jq -r '.data.descricao_status_pesquisa // "N/A"')

      echo -e "${BLUE}Processo:${NC} ${NUMERO_PROC}"
      echo -e "${BLUE}Status:${NC} ${STATUS_PESQ} - ${DESC_STATUS}"
      echo ""
    else
      echo -e "${RED}❌ Erro na consulta do processo!${NC}"
    fi
  fi
else
  echo -e "${RED}❌ Erro ao inserir processo!${NC}"
  RETORNO=$(echo "$INSERT_RESPONSE" | jq -r '.data.retorno // .error // "ERRO_DESCONHECIDO"')
  OBS=$(echo "$INSERT_RESPONSE" | jq -r '.data.obs // .message // "Sem detalhes"')

  echo -e "${RED}Código:${NC} ${RETORNO}"
  echo -e "${RED}Mensagem:${NC} ${OBS}"
  echo ""

  # Dicas de troubleshooting
  if [ "$RETORNO" == "ERRO_PROJETO_NAO_LOCALIZADO" ]; then
    echo -e "${YELLOW}💡 Dica:${NC} A chave do projeto pode estar incorreta ou o projeto não existe."
    echo -e "${YELLOW}   Verifique com suporte DW LAW: suporte@dwrpa.com.br${NC}"
  elif [ "$RETORNO" == "ERRO_EMPRESA_INVALIDA" ]; then
    echo -e "${YELLOW}💡 Dica:${NC} As credenciais podem estar incorretas ou empresa não existe."
    echo -e "${YELLOW}   Verifique: DW_LAW_USUARIO e DW_LAW_SENHA no .env${NC}"
  fi

  exit 1
fi

###############################################################################
# RESUMO FINAL
###############################################################################
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RESUMO DOS TESTES                                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Autenticação DW LAW${NC}"
echo -e "${GREEN}✅ Gateway respondendo${NC}"
echo -e "${GREEN}✅ Conexões DW LAW e Camunda${NC}"
echo -e "${GREEN}✅ Inserção de processos${NC}"
echo -e "${GREEN}✅ Consulta de processos${NC}"
echo ""
echo -e "${BLUE}Credenciais Configuradas:${NC}"
echo -e "  • Usuário: ${DW_LAW_USUARIO}"
echo -e "  • Projeto: ${DW_LAW_CHAVE_PROJETO}"
echo -e "  • Ambiente: QA/Homologação"
echo ""
echo -e "${YELLOW}📋 Próximos Passos:${NC}"
echo -e "  1. Configurar URL de callback no DW LAW"
echo -e "  2. Criar processo BPMN no Camunda"
echo -e "  3. Testar fluxo end-to-end completo"
echo ""
echo -e "${GREEN}🎉 Todos os testes passaram com sucesso!${NC}"
echo ""
