#!/usr/bin/env bash
# ========================================
# Script para verificar arquivos que serão copiados
# ========================================

set -e

echo "🔍 Verificando arquivos que serão copiados pelo rsync..."
echo ""

# Simula o rsync sem realmente copiar
rsync -avn --exclude-from=.rsyncignore ./ /tmp/rsync-test/ | grep -v "^building\|^sending\|^sent\|^total" | head -100

echo ""
echo "✅ Verificação concluída!"
echo ""
echo "📊 Estatísticas:"
echo "   Total de arquivos a copiar: $(rsync -avn --exclude-from=.rsyncignore ./ /tmp/rsync-test/ | grep -v "^building\|^sending\|^sent\|^total\|^\$" | wc -l | xargs)"
echo ""
echo "🚫 Arquivos EXCLUÍDOS (conforme .rsyncignore):"
echo "   - app/tests/ (diretório completo)"
echo "   - __pycache__/ (todos)"
echo "   - *.pyc, *.pyo, *.pyd"
echo "   - .venv/ (ambiente virtual)"
echo "   - .pytest_cache/, .coverage, htmlcov/"
echo "   - .vscode/, .idea/"
echo "   - .git/"
echo ""
