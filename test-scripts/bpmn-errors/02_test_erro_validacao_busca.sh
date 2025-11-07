#!/bin/bash
# Teste: ERRO_VALIDACAO_BUSCA
# Descrição: Inicia busca de publicações com parâmetros INVÁLIDOS

set -e

CAMUNDA_URL="${CAMUNDA_URL:-http://localhost:8080}"
PROCESS_KEY="fluxo_buscar_publicacoes_diarias"

echo "=========================================="
echo "Teste: ERRO_VALIDACAO_BUSCA"
echo "=========================================="
echo ""
echo "Enviando busca com parâmetros INVÁLIDOS..."
echo "  ✗ limite_publicacoes: 100 (máximo permitido: 50)"
echo "  ✗ timeout_soap: 500 (máximo permitido: 300)"
echo ""

RESPONSE=$(curl -s -X POST "${CAMUNDA_URL}/camunda/engine-rest/process-definition/key/${PROCESS_KEY}/start" \
  -H "Content-Type: application/json" \
  -d '{
    "businessKey": "test-busca-validacao-'$(date +%s)'",
    "variables": {
      "cod_grupo": {"value": 5, "type": "Integer"},
      "limite_publicacoes": {"value": 100, "type": "Integer"},
      "timeout_soap": {"value": 500, "type": "Integer"}
    }
  }')

echo "Resposta:"
echo "$RESPONSE" | jq '.'
echo ""
echo "✅ Instância criada. Verificar logs do worker:"
echo "   docker logs publicacao-unified-worker | grep 'ERRO_VALIDACAO_BUSCA'"
echo ""
echo "✅ Verificar no Cockpit se boundary event capturou o erro:"
echo "   ${CAMUNDA_URL}/camunda/app/cockpit"
