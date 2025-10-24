#!/bin/bash

echo "🚀 Iniciando serviços Camunda com correção de DNS..."

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose -f camunda-worker-api-gateway/docker-compose.yml down
docker-compose -f camunda-workers-platform/docker-compose.yml down

# Aguardar um momento
sleep 2

# Iniciar o gateway primeiro
echo "🌐 Iniciando Worker API Gateway..."
cd camunda-worker-api-gateway
docker-compose up -d gateway
echo "⏳ Aguardando gateway ficar pronto..."
sleep 10

# Verificar se o gateway está rodando
if docker ps | grep -q "camunda-worker-api-gateway-gateway"; then
    echo "✅ Gateway iniciado com sucesso"
    
    # Testar health do gateway
    echo "🔍 Testando health do gateway..."
    docker exec camunda-worker-api-gateway-gateway-1 python -c "import requests; requests.get('http://localhost:8000/health')" 2>/dev/null && echo "✅ Gateway está saudável" || echo "⚠️ Gateway pode não estar totalmente pronto"
    
    # Iniciar o worker
    echo "👷 Iniciando Worker..."
    cd ../camunda-workers-platform
    docker-compose up -d worker-publicacao-unified
    
    # Aguardar worker ficar pronto
    echo "⏳ Aguardando worker ficar pronto..."
    sleep 5
    
    # Verificar se o worker está rodando
    if docker ps | grep -q "worker-publicacao-unified"; then
        echo "✅ Worker iniciado com sucesso"
        
        # Executar teste de conectividade
        echo "🔗 Testando conectividade..."
        cd ..
        ./test_connectivity.sh
        
    else
        echo "❌ Falha ao iniciar worker"
        docker-compose -f camunda-workers-platform/docker-compose.yml logs worker-publicacao-unified
    fi
    
else
    echo "❌ Falha ao iniciar gateway"
    docker-compose -f camunda-worker-api-gateway/docker-compose.yml logs gateway
fi

echo ""
echo "📊 Status final dos containers:"
docker ps | grep -E "(gateway|worker)"

echo ""
echo "✅ Script de inicialização concluído!"
