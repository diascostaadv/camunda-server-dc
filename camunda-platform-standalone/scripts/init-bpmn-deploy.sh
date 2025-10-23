#!/bin/bash
"""
Script para deploy automático de BPMN files após o Camunda estar rodando
"""

set -e

# Configurações
CAMUNDA_BASE_URL=${CAMUNDA_BASE_URL:-"http://localhost:8080"}
CAMUNDA_USERNAME=${CAMUNDA_USERNAME:-"admin"}
CAMUNDA_PASSWORD=${CAMUNDA_PASSWORD:-"admin"}
BPMN_DIR=${BPMN_DIR:-"bpmn"}
MAX_ATTEMPTS=${MAX_ATTEMPTS:-30}
DELAY=${DELAY:-10}

echo "🚀 Starting BPMN auto-deployment..."
echo "📁 BPMN Directory: $BPMN_DIR"
echo "🌐 Camunda URL: $CAMUNDA_BASE_URL"

# Função para aguardar Camunda estar disponível
wait_for_camunda() {
    echo "⏳ Waiting for Camunda to be available..."
    
    for attempt in $(seq 1 $MAX_ATTEMPTS); do
        if curl -s -f "$CAMUNDA_BASE_URL/engine-rest/version" \
            -u "$CAMUNDA_USERNAME:$CAMUNDA_PASSWORD" >/dev/null 2>&1; then
            echo "✅ Camunda is available!"
            return 0
        fi
        
        if [ $attempt -lt $MAX_ATTEMPTS ]; then
            echo "⏳ Attempt $attempt/$MAX_ATTEMPTS - Waiting for Camunda..."
            sleep $DELAY
        fi
    done
    
    echo "❌ Camunda not available after $MAX_ATTEMPTS attempts"
    return 1
}

# Função para deploy dos BPMN files
deploy_bpmn_files() {
    echo "📋 Looking for BPMN files in $BPMN_DIR..."
    
    if [ ! -d "$BPMN_DIR" ]; then
        echo "❌ BPMN directory $BPMN_DIR not found"
        return 1
    fi
    
    # Encontrar arquivos BPMN
    bpmn_files=$(find "$BPMN_DIR" -name "*.bpmn" -type f)
    
    if [ -z "$bpmn_files" ]; then
        echo "❌ No BPMN files found in $BPMN_DIR"
        return 1
    fi
    
    echo "📋 Found BPMN files:"
    echo "$bpmn_files" | while read -r file; do
        echo "  - $file"
    done
    
    # Deploy cada arquivo BPMN
    success_count=0
    total_count=0
    
    echo "$bpmn_files" | while read -r bpmn_file; do
        if [ -n "$bpmn_file" ]; then
            total_count=$((total_count + 1))
            echo "🚀 Deploying $(basename "$bpmn_file")..."
            
            if deploy_single_bpmn "$bpmn_file"; then
                success_count=$((success_count + 1))
                echo "✅ Successfully deployed $(basename "$bpmn_file")"
            else
                echo "❌ Failed to deploy $(basename "$bpmn_file")"
            fi
        fi
    done
    
    echo "✅ BPMN deployment completed! $success_count/$total_count files deployed successfully"
}

# Função para deploy de um arquivo BPMN individual
deploy_single_bpmn() {
    local bpmn_file="$1"
    local filename=$(basename "$bpmn_file")
    local deployment_name="deployment-$(basename "$bpmn_file" .bpmn)"
    
    # Usar curl para fazer o deploy
    response=$(curl -s -w "%{http_code}" -o /tmp/deploy_response.json \
        -X POST \
        -u "$CAMUNDA_USERNAME:$CAMUNDA_PASSWORD" \
        -F "deployment-name=$deployment_name" \
        -F "deployment-source=auto-deploy-script" \
        -F "file=@$bpmn_file" \
        "$CAMUNDA_BASE_URL/engine-rest/deployment/create" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        deployment_id=$(cat /tmp/deploy_response.json | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        echo "✅ Deployed $filename - ID: $deployment_id"
        return 0
    else
        echo "❌ Failed to deploy $filename (HTTP $response)"
        cat /tmp/deploy_response.json 2>/dev/null || true
        return 1
    fi
}

# Execução principal
main() {
    # Aguardar Camunda estar disponível
    if ! wait_for_camunda; then
        echo "💥 Cannot proceed without Camunda"
        exit 1
    fi
    
    # Aguardar um pouco mais para garantir que o Camunda esteja totalmente pronto
    echo "⏳ Waiting additional 30 seconds for Camunda to be fully ready..."
    sleep 30
    
    # Deploy dos BPMN files
    if deploy_bpmn_files; then
        echo "🎉 BPMN auto-deployment completed successfully!"
    else
        echo "💥 BPMN auto-deployment failed!"
        exit 1
    fi
}

# Executar se chamado diretamente
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
