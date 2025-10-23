#!/bin/bash

# Script de configuração de monitoramento
# Configura Prometheus e Grafana para monitoramento da plataforma Camunda

ENVIRONMENT=${1:-production}

echo "📊 Setting up monitoring for environment: $ENVIRONMENT"

# Criar diretórios de dados
mkdir -p data/prometheus
mkdir -p data/grafana
mkdir -p data/grafana/dashboards
mkdir -p data/grafana/provisioning/dashboards
mkdir -p data/grafana/provisioning/datasources

# Configurar permissões
chmod 777 data/prometheus
chmod 777 data/grafana

# Copiar configurações de monitoramento
if [ -f "camunda-platform-standalone/config/prometheus.yml" ]; then
    cp camunda-platform-standalone/config/prometheus.yml data/prometheus/
    echo "✅ Prometheus configuration copied"
fi

if [ -f "camunda-platform-standalone/config/grafana/dashboards" ]; then
    cp -r camunda-platform-standalone/config/grafana/dashboards/* data/grafana/dashboards/
    echo "✅ Grafana dashboards copied"
fi

if [ -f "camunda-platform-standalone/config/grafana/provisioning" ]; then
    cp -r camunda-platform-standalone/config/grafana/provisioning/* data/grafana/provisioning/
    echo "✅ Grafana provisioning copied"
fi

echo "✅ Monitoring setup completed for $ENVIRONMENT"
