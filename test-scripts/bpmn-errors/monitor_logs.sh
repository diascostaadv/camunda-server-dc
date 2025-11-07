#!/bin/bash
# Script para monitorar logs do worker e detectar BPMN errors

WORKER_CONTAINER="${WORKER_CONTAINER:-publicacao-unified-worker}"

echo "=========================================="
echo "Monitorando BPMN Errors no Worker"
echo "Container: $WORKER_CONTAINER"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Logs em tempo real (Ctrl+C para parar):"
echo ""

docker logs -f "$WORKER_CONTAINER" 2>&1 | while read line; do
    if echo "$line" | grep -q "BPMN Error"; then
        echo -e "${RED}[BPMN ERROR]${NC} $line"
    elif echo "$line" | grep -q "ERRO_VALIDACAO"; then
        echo -e "${YELLOW}[VALIDAÇÃO]${NC} $line"
    elif echo "$line" | grep -q "ERRO_"; then
        echo -e "${RED}[ERRO]${NC} $line"
    elif echo "$line" | grep -q "✅"; then
        echo -e "${GREEN}$line${NC}"
    elif echo "$line" | grep -q "❌"; then
        echo -e "${RED}$line${NC}"
    else
        echo "$line"
    fi
done
