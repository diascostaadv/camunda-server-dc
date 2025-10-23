#!/bin/bash

# Script de inicialização do Docker Swarm
# Inicializa o Docker Swarm no servidor remoto

echo "🎯 Initializing Docker Swarm..."

# Verificar se já está em modo swarm
if docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
    echo "✅ Docker Swarm is already active"
    exit 0
fi

# Inicializar swarm
docker swarm init

# Verificar status
if docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
    echo "✅ Docker Swarm initialized successfully"
    echo "📋 Swarm info:"
    docker node ls
else
    echo "❌ Failed to initialize Docker Swarm"
    exit 1
fi
