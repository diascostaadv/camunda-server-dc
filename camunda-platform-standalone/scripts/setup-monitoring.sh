#!/bin/bash
# Script para configurar monitoramento baseado no ambiente

# Carrega configurações de ambiente
ENVIRONMENT=${ENVIRONMENT:-local}
WORKERS_MODE=${WORKERS_MODE:-separated}

echo "Configurando monitoramento para ambiente: $ENVIRONMENT, workers: $WORKERS_MODE"

# Verifica se estamos implantando via stack (parâmetro STACK_DEPLOY)
if [ "${STACK_DEPLOY:-false}" = "true" ] || docker stack ls 2>/dev/null | grep -q camunda; then
    echo "Modo Swarm Stack detectado - usando configuração Swarm"
    cp config/prometheus-swarm.yml config/prometheus.yml
    
    # Ajusta configuração baseada no modo de workers
    if [ "$WORKERS_MODE" = "embedded" ]; then
        echo "Ajustando configuração para workers embedded..."
        # Remove targets dos workers separados e adiciona target do Camunda com métricas dos workers
        sed -i.bak '
        /- job_name: '\''camunda-workers'\''/,/scrape_timeout: 10s/ {
            /static_configs:/,/scrape_timeout: 10s/ {
                s/- targets:/# Workers embedded - metrics available at camunda:8000/
                /worker-/d
                /scrape_interval:/i\
      - targets: ['\''camunda:8000'\'']
            }
        }' config/prometheus.yml
    fi
    
else
    echo "Modo Docker Compose detectado - criando configuração adequada"
    
    # Cria configuração baseada no modo de workers
    if [ "$WORKERS_MODE" = "embedded" ]; then
        echo "Criando configuração para workers embedded..."
        cat > config/prometheus.yml << 'EOF'
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'camunda-jmx'
    static_configs:
      - targets: ['camunda:9404']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'camunda-workers-embedded'
    static_configs:
      - targets: ['camunda:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['db:5432']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
EOF
    else
        echo "Criando configuração para workers separados..."
        cat > config/prometheus.yml << 'EOF'
global:
  scrape_interval: 30s
  evaluation_interval: 30s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'camunda-jmx'
    static_configs:
      - targets: ['camunda:9404']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'camunda-workers'
    static_configs:
      - targets: 
        - 'worker-validation:8001'
        - 'worker-processing:8002'
        - 'worker-publication:8003'
        - 'worker-notification:8004'
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['db:5432']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
EOF
    fi
fi

echo "✅ Configuração aplicada com sucesso!"
echo "Ambiente: $ENVIRONMENT"
echo "Workers: $WORKERS_MODE"