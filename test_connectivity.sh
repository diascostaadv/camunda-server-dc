#!/bin/bash

echo "🔍 Testando conectividade entre worker e gateway..."

# Verificar se os containers estão rodando
echo "📋 Status dos containers:"
docker ps | grep -E "(gateway|worker)"

echo ""
echo "🌐 Verificando redes:"
docker network ls | grep camunda

echo ""
echo "🔗 Testando conectividade de rede:"
if docker ps | grep -q "camunda-worker-api-gateway-gateway"; then
    echo "✅ Gateway container está rodando"
    
    # Testar conectividade do worker para o gateway
    if docker ps | grep -q "worker-publicacao-unified"; then
        echo "✅ Worker container está rodando"
        
        # Testar ping do worker para o gateway
        echo "📡 Testando ping do worker para o gateway..."
        docker exec camunda-workers-platform-worker-publicacao-unified-1 ping -c 3 camunda-worker-api-gateway-gateway-1 || echo "❌ Ping falhou"
        
        # Testar HTTP do worker para o gateway
        echo "🌐 Testando HTTP do worker para o gateway..."
        docker exec camunda-workers-platform-worker-publicacao-unified-1 curl -f http://camunda-worker-api-gateway-gateway-1:8000/health || echo "❌ HTTP falhou"
    else
        echo "❌ Worker container não está rodando"
    fi
else
    echo "❌ Gateway container não está rodando"
fi

echo ""
echo "📊 Informações da rede camunda-worker-api-gateway_backend:"
docker network inspect camunda-worker-api-gateway_backend --format '{{range .Containers}}{{.Name}} - {{.IPv4Address}}{{"\n"}}{{end}}'

echo ""
echo "✅ Teste de conectividade concluído!"
