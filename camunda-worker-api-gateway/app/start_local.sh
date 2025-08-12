#!/bin/bash

# Script para iniciar aplicação localmente com MongoDB Atlas

export MONGODB_URI="mongodb+srv://camunda:Rqt0wVmEZhcME7HC@camundadc.os1avun.mongodb.net/?retryWrites=true&w=majority&appName=CamundaDC"
export MONGODB_DATABASE="worker_gateway"
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
export REDIS_URI="redis://localhost:6379"
export LOG_LEVEL="INFO"
export PORT=8000
export DEBUG=true
export ENVIRONMENT=local

echo "🚀 Iniciando Gateway com MongoDB Atlas..."
echo "   MONGODB_URI: ${MONGODB_URI:0:50}..."
echo "   DATABASE: $MONGODB_DATABASE"

python main.py