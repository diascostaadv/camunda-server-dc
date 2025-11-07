#!/bin/bash

###############################################################################
# Script de Deploy: DW LAW Worker
# Data: 2025-11-07
# VM Produção: 201.23.69.65
#
# USO: Execute linha por linha ou todo o script
###############################################################################

set -e  # Exit on error

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Deploy DW LAW Worker - Camunda Platform                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# OPÇÃO 1: Deploy Automatizado via Makefile
###############################################################################
echo -e "${YELLOW}═══ OPÇÃO 1: Deploy via Makefile (Recomendado) ═══${NC}"
echo ""

echo -e "${GREEN}# Passo 1: Sincronizar arquivos para VM${NC}"
echo "cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform"
echo "make copy-files"
echo ""

echo -e "${GREEN}# Passo 2: SSH na VM${NC}"
echo "ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65"
echo ""

echo -e "${GREEN}# Passo 3: Navegar e fazer deploy${NC}"
echo "cd ~/camunda-server-dc/camunda-workers-platform"
echo "docker compose build worker-dw-law"
echo "docker compose up -d worker-dw-law"
echo ""

echo -e "${GREEN}# Passo 4: Verificar${NC}"
echo "docker ps | grep dw-law"
echo "docker logs -f worker-dw-law --tail=100"
echo ""

###############################################################################
# OPÇÃO 2: Deploy Manual via SCP
###############################################################################
echo -e "${YELLOW}═══ OPÇÃO 2: Deploy Manual (Passo a Passo) ═══${NC}"
echo ""

echo -e "${GREEN}# Passo 1: Copiar worker${NC}"
echo 'scp -i ~/.ssh/id_rsa -r workers/dw_law_worker ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/workers/'
echo ""

echo -e "${GREEN}# Passo 2: Copiar docker-compose.yml${NC}"
echo 'scp -i ~/.ssh/id_rsa docker-compose.yml ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/'
echo ""

echo -e "${GREEN}# Passo 3: Copiar env.gateway${NC}"
echo 'scp -i ~/.ssh/id_rsa env.gateway ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/'
echo ""

echo -e "${GREEN}# Passo 4: Copiar common${NC}"
echo 'scp -i ~/.ssh/id_rsa -r workers/common ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/workers/'
echo ""

echo -e "${GREEN}# Passo 5: SSH e Deploy${NC}"
echo "ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65 << 'EOF'"
echo "cd ~/camunda-server-dc/camunda-workers-platform"
echo "docker compose build worker-dw-law"
echo "docker compose up -d worker-dw-law"
echo "docker logs -f worker-dw-law --tail=100"
echo "EOF"
echo ""

###############################################################################
# COMANDOS DE VERIFICAÇÃO
###############################################################################
echo -e "${YELLOW}═══ Comandos de Verificação ═══${NC}"
echo ""

echo -e "${GREEN}# Verificar container rodando${NC}"
echo "docker ps | grep dw-law"
echo ""

echo -e "${GREEN}# Ver logs${NC}"
echo "docker logs -f worker-dw-law --tail=100"
echo ""

echo -e "${GREEN}# Health check${NC}"
echo "curl http://localhost:8010/health"
echo ""

echo -e "${GREEN}# Métricas${NC}"
echo "curl http://localhost:8010/metrics | grep external_task"
echo ""

echo -e "${GREEN}# Status de todos os workers${NC}"
echo "docker compose ps"
echo ""

###############################################################################
# COMANDOS DE TESTE
###############################################################################
echo -e "${YELLOW}═══ Comandos de Teste ═══${NC}"
echo ""

echo -e "${GREEN}# Teste 1: Health check externo (da sua máquina)${NC}"
echo "curl http://201.23.69.65:8010/health"
echo ""

echo -e "${GREEN}# Teste 2: Métricas externas${NC}"
echo "curl http://201.23.69.65:8010/metrics"
echo ""

echo -e "${GREEN}# Teste 3: Inserir processo via Gateway${NC}"
echo "curl -X POST http://201.23.69.65:8000/dw-law/inserir-processos \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '    "chave_projeto": "diascostacitacaoconsultaunica",'
echo '    "processos": [{'
echo '      "numero_processo": "0012205-60.2015.5.15.0077",'
echo '      "other_info_client1": "TESTE_DEPLOY"'
echo "    }]"
echo "  }'"
echo ""

###############################################################################
# COMANDOS DE OPERAÇÃO
###############################################################################
echo -e "${YELLOW}═══ Comandos de Operação ═══${NC}"
echo ""

echo -e "${GREEN}# Reiniciar worker${NC}"
echo "docker compose restart worker-dw-law"
echo ""

echo -e "${GREEN}# Parar worker${NC}"
echo "docker compose stop worker-dw-law"
echo ""

echo -e "${GREEN}# Iniciar worker${NC}"
echo "docker compose start worker-dw-law"
echo ""

echo -e "${GREEN}# Rebuild worker${NC}"
echo "docker compose build --no-cache worker-dw-law"
echo "docker compose up -d worker-dw-law"
echo ""

echo -e "${GREEN}# Escalar para 2 réplicas${NC}"
echo "docker compose up -d --scale worker-dw-law=2"
echo ""

echo -e "${GREEN}# Ver logs de erro${NC}"
echo "docker logs worker-dw-law 2>&1 | grep -i error"
echo ""

###############################################################################
# ROLLBACK
###############################################################################
echo -e "${YELLOW}═══ Rollback (Se Necessário) ═══${NC}"
echo ""

echo -e "${GREEN}# Parar e remover worker${NC}"
echo "docker compose stop worker-dw-law"
echo "docker compose rm -f worker-dw-law"
echo "docker rmi camunda-workers-platform-worker-dw-law:latest"
echo ""

echo -e "${GREEN}# Restaurar arquivos anteriores${NC}"
echo "git checkout HEAD -- docker-compose.yml env.gateway"
echo ""

###############################################################################
# FIREWALL
###############################################################################
echo -e "${YELLOW}═══ Configurar Firewall (Se Necessário) ═══${NC}"
echo ""

echo -e "${GREEN}# Adicionar regra UFW${NC}"
echo "sudo ufw allow 8010/tcp"
echo "sudo ufw reload"
echo ""

echo -e "${GREEN}# Verificar${NC}"
echo "sudo ufw status | grep 8010"
echo ""

###############################################################################
# MONITORAMENTO
###############################################################################
echo -e "${YELLOW}═══ URLs de Monitoramento ═══${NC}"
echo ""

echo -e "${GREEN}# Worker${NC}"
echo "Health: http://201.23.69.65:8010/health"
echo "Métricas: http://201.23.69.65:8010/metrics"
echo ""

echo -e "${GREEN}# Gateway${NC}"
echo "API: http://201.23.69.65:8000"
echo "Docs: http://201.23.69.65:8000/docs"
echo ""

echo -e "${GREEN}# Camunda${NC}"
echo "Cockpit: http://201.23.67.197:8080/camunda/app/cockpit"
echo "Login: demo / DiasCostaA!!2025"
echo ""

echo -e "${GREEN}# Prometheus${NC}"
echo "URL: http://201.23.69.65:9090"
echo ""

echo -e "${GREEN}# Grafana${NC}"
echo "URL: http://201.23.69.65:3001"
echo "Login: admin / admin"
echo ""

###############################################################################
# FIM
###############################################################################
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Comandos prontos! Copie e cole conforme necessário.      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
