#!/bin/bash
# Teste: ERRO_VALIDACAO_NOVA_PUBLICACAO
# Descrição: Submete uma nova publicação SEM campos obrigatórios

set -e

CAMUNDA_URL="${CAMUNDA_URL:-http://localhost:8080}"
PROCESS_KEY="fluxo_nova_publicacao"

echo "=========================================="
echo "Teste: ERRO_VALIDACAO_NOVA_PUBLICACAO"
echo "=========================================="
echo ""
echo "Enviando nova publicação com campos FALTANDO..."
echo "  ✗ texto_publicacao: AUSENTE"
echo "  ✗ tribunal: AUSENTE"
echo "  ✗ instancia: AUSENTE"
echo ""

RESPONSE=$(curl -s -X POST "${CAMUNDA_URL}/camunda/engine-rest/message" \
  -H "Content-Type: application/json" \
  -d '{
    "messageName": "Nova_publicacao",
    "businessKey": "test-validacao-'$(date +%s)'",
    "processVariables": {
      "numero_processo": {"value": "1234567-89.2024.8.13.0024", "type": "String"},
      "data_publicacao": {"value": "01/12/2024", "type": "String"},
      "fonte": {"value": "dw", "type": "String"}
    }
  }')

echo "Resposta:"
echo "$RESPONSE" | jq '.'
echo ""
echo "✅ Instância criada. Verificar logs do worker:"
echo "   docker logs publicacao-unified-worker | grep 'ERRO_VALIDACAO_NOVA_PUBLICACAO'"
echo ""
echo "✅ Verificar no Cockpit se boundary event capturou o erro:"
echo "   ${CAMUNDA_URL}/camunda/app/cockpit"
