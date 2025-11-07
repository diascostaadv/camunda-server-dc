#!/bin/bash
# Teste: ERRO_VALIDACAO_CLASSIFICACAO
# Descrição: Tenta classificar publicação SEM fornecer publicacao_id nem texto

set -e

CAMUNDA_URL="${CAMUNDA_URL:-http://localhost:8080}"

echo "=========================================="
echo "Teste: ERRO_VALIDACAO_CLASSIFICACAO"
echo "=========================================="
echo ""
echo "Tentando classificar publicação sem fornecer:"
echo "  ✗ publicacao_id: AUSENTE"
echo "  ✗ texto_publicacao: AUSENTE"
echo ""
echo "NOTA: Precisa de uma instância de processo rodando para testar"
echo "      classificacao_publicacao externamente."
echo ""

# Criar um processo simples apenas para teste
RESPONSE=$(curl -s -X POST "${CAMUNDA_URL}/camunda/engine-rest/process-definition/key/fluxo_publicacao_captura_intimacoes/start" \
  -H "Content-Type: application/json" \
  -d '{
    "businessKey": "test-classificacao-'$(date +%s)'",
    "variables": {
      "publicacoes_ids": {"value": "[123]", "type": "Json"}
    }
  }')

PROCESS_INSTANCE_ID=$(echo "$RESPONSE" | jq -r '.id')

echo "Processo criado: $PROCESS_INSTANCE_ID"
echo ""
echo "✅ Aguardar worker processar e verificar logs:"
echo "   docker logs publicacao-unified-worker | grep 'ERRO_VALIDACAO_CLASSIFICACAO'"
echo ""
echo "✅ Verificar no Cockpit:"
echo "   ${CAMUNDA_URL}/camunda/app/cockpit"
