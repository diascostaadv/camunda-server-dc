# 🎛️ Makefile Orquestrador - Guia Completo

O Makefile na raiz do projeto funciona como um **orquestrador centralizado** para gerenciar os 3 projetos independentes de forma integrada.

## 🎯 Visão Geral

```
Makefile (Raiz)
├── Coordena os 3 projetos
├── Execução sequencial inteligente
├── Health checks automáticos
├── Cenários pré-definidos
└── Monitoramento centralizado

↓ Delega para ↓

├── camunda-platform-standalone/Makefile
├── camunda-worker-api-gateway/Makefile  
└── camunda-workers-platform/Makefile
```

## 🚀 Comandos Principais

### Inicialização do Ecosystem

```bash
# Ecosystem básico (Platform + Workers)
make start
# 1. Inicia Camunda Platform
# 2. Aguarda 30s para estabilizar
# 3. Inicia Workers Platform
# 4. Mostra status final

# Ecosystem completo (Platform + Gateway + Workers)
make start-full
# 1. Inicia Camunda Platform
# 2. Inicia Worker API Gateway
# 3. Aguarda 45s para estabilizar
# 4. Inicia Workers Platform
# 5. Mostra status final
```

### Parada do Ecosystem

```bash
# Parada ordenada
make stop
# 1. Para Workers Platform
# 2. Para Worker API Gateway
# 3. Para Camunda Platform
```

### Restart Completo

```bash
# Restart com parada segura
make restart
# 1. Executa make stop
# 2. Aguarda 5s
# 3. Executa make start
```

## 🎛️ Gerenciamento por Projeto

### Projeto 1: Camunda Platform

```bash
make platform-up       # Inicia apenas o platform
make platform-down     # Para apenas o platform
make platform-status   # Status do platform
make platform-logs     # Logs do platform
make platform-deploy   # Deploy em produção
```

### Projeto 2: Worker API Gateway

```bash
make gateway-up         # Inicia apenas o gateway
make gateway-down       # Para apenas o gateway
make gateway-status     # Status do gateway
make gateway-logs       # Logs do gateway
make gateway-deploy     # Deploy em produção
make gateway-test       # Testa endpoints
```

### Projeto 3: Workers Platform

```bash
make workers-up         # Inicia apenas os workers
make workers-down       # Para apenas os workers
make workers-status     # Status dos workers
make workers-logs       # Logs dos workers
make workers-deploy     # Deploy em produção
make workers-list       # Lista workers disponíveis
make workers-new        # Cria novo worker
make workers-build      # Build de todos os workers
```

## 📊 Monitoramento e Status

### Status Centralizado

```bash
# Status local (todos os projetos)
make status
# 📊 === CAMUNDA BPM ECOSYSTEM STATUS (LOCAL) ===
# 🏗️ Camunda Platform Status:
# 🌐 Worker API Gateway Status:
# 👷 Workers Platform Status:
# 🌐 === SERVICE URLS ===

# Status remoto (produção)
make status-remote
```

### Health Checks Automáticos

```bash
make health
# 💊 === HEALTH CHECKS ===
# 🏗️ Camunda Platform:
#   ✅ Camunda: OK
#   ✅ Prometheus: OK
#   ✅ Grafana: OK
# 🌐 Gateway:
#   ✅ Gateway: OK
# 👷 Workers:
#   ✅ Hello World Worker: OK
#   ✅ Publicacao Worker: OK
```

### URLs de Acesso

```bash
make urls
# 🌐 === SERVICE URLS ===
# 🏗️ Camunda Platform:
#   Camunda Web Apps: http://localhost:8080 (demo/demo)
#   Prometheus:       http://localhost:9090
#   Grafana:          http://localhost:3001 (admin/admin)
# 🌐 Worker API Gateway:
#   Gateway API:      http://localhost:8000
#   Gateway Docs:     http://localhost:8000/docs
#   RabbitMQ Mgmt:    http://localhost:15672 (admin/admin123)
# 👷 Workers:
#   Hello World:      http://localhost:8001/metrics
#   Publicacao:       http://localhost:8002/metrics
```

## 🎯 Cenários Pré-definidos

### Cenário 1: Desenvolvimento Local

```bash
make scenario-local
# 🏠 === CENÁRIO: DESENVOLVIMENTO LOCAL COMPLETO ===
# Todos os serviços em containers locais
# Equivale a: make start
```

### Cenário 2: Híbrido (Local + Cloud)

```bash
make scenario-hybrid
# 🌐 === CENÁRIO: HÍBRIDO (LOCAL + EXTERNAL) ===
# Platform local, Gateway externo
# 1. Platform com DB local
# 2. Gateway com serviços externos (Azure)
# 3. Workers conectam aos serviços locais/externos
```

### Cenário 3: Produção Completa

```bash
make scenario-production
# ☁️ === CENÁRIO: PRODUÇÃO COMPLETA ===
# Todos os serviços em modo produção
# Equivale a: make deploy-all
```

## 🚢 Comandos de Produção

### Deploy Completo

```bash
# Deploy de todos os projetos
make deploy-all
# 1. make platform-deploy
# 2. make gateway-deploy
# 3. make workers-deploy
# 4. make status-remote

# Comandos individuais
make prod-deploy        # Alias para deploy-all
make prod-status        # Status produção
make prod-down          # Para produção
make prod-logs          # Logs produção
```

### Escalabilidade

```bash
# Escalar Camunda Platform
make scale-platform N=3

# Escalar Gateway
make scale-gateway N=2

# Escalar Worker específico
make scale-worker W=hello-world N=5
```

## 🛠️ Comandos de Desenvolvimento

### Setup e Limpeza

```bash
# Setup ambiente desenvolvimento
make dev-setup
# 1. Instala dependências Gateway
# 2. Instala dependências Workers
# 3. Prepara ambiente

# Limpeza completa
make dev-clean
# 1. Para todos os serviços
# 2. Remove containers, volumes, imagens
# 3. Libera espaço em disco

# Reset completo
make dev-reset
# 1. make dev-clean
# 2. make dev-setup
# 3. make start
```

## 🔧 Recursos Avançados

### Detecção Automática de Modo

O orquestrador detecta automaticamente o modo de operação:

```bash
make info
# 📋 === ECOSYSTEM CONFIGURATION ===
# Platform External DB: false        # Detecta .env.local
# Gateway External Services: true     # Detecta .env.local
```

### Logs Agregados

```bash
# Todos os logs em paralelo
make logs-all
# 📋 === ALL LOGS (press Ctrl+C to stop) ===
# Mostra logs de todos os projetos simultaneamente
```

### Backup de Dados

```bash
# Backup do banco Camunda
make backup-db
# Delega para: cd camunda-platform-standalone && make backup-db
```

## 📋 Fluxos de Trabalho Típicos

### Desenvolvimento Diário

```bash
# Início do dia
make start
make status
make urls

# Durante desenvolvimento
make workers-list              # Ver workers
make workers-new               # Criar worker
make gateway-test              # Testar gateway

# Fim do dia
make stop
```

### Deploy de Nova Versão

```bash
# Build e teste local
make workers-build
make start
make health

# Deploy produção
make deploy-all
make prod-status
```

### Debug de Problemas

```bash
# Verificar status
make status
make health

# Logs específicos
make platform-logs
make gateway-logs  
make workers-logs

# Ou todos juntos
make logs-all
```

### Escalabilidade em Produção

```bash
# Verificar carga
make prod-status

# Escalar conforme necessário
make scale-platform N=3
make scale-gateway N=2
make scale-worker W=publicacao N=5

# Verificar resultado
make prod-status
```

## ⚡ Dicas e Truques

### 1. Cores no Terminal
O orquestrador usa cores para facilitar identificação:
- 🔵 **Azul**: Camunda Platform
- 🔴 **Magenta**: Worker API Gateway  
- 🔵 **Cyan**: Workers Platform
- ⚪ **Branco**: Status geral

### 2. Execução Paralela
Comandos que podem rodar em paralelo:
```bash
# Logs em paralelo
make logs-all

# Deploy paralelo (com dependências respeitadas)
make deploy-all
```

### 3. Integração com CI/CD
```bash
# Pipeline de CI/CD
make dev-setup          # Setup
make health             # Verify
make deploy-all         # Deploy
make prod-status        # Verify production
```

### 4. Desenvolvimento Modular
```bash
# Trabalhar apenas com Platform
make platform-up

# Adicionar Gateway quando necessário
make gateway-up

# Adicionar Workers por último
make workers-up
```

## 🚨 Troubleshooting

### Problema: Comando não responde
```bash
# Verificar se projeto existe
ls -la camunda-*

# Verificar Makefiles individuais
cd camunda-platform-standalone && make help
```

### Problema: Serviços não iniciam
```bash
# Verificar configuração
make info

# Verificar status individual
make platform-status
make gateway-status
make workers-status
```

### Problema: Health check falha
```bash
# Aguardar mais tempo
sleep 30 && make health

# Verificar logs
make logs-all
```

## 🎉 Vantagens do Orquestrador

### ✅ **Simplicidade**
Um comando para gerenciar tudo: `make start`

### ✅ **Inteligência**
Aguarda serviços estabilizarem antes de prosseguir

### ✅ **Visibilidade**
Status consolidado de todos os projetos

### ✅ **Flexibilidade**
Pode gerenciar projetos individualmente ou em conjunto

### ✅ **Produtividade**
Reduz comandos manuais de dezenas para poucos

### ✅ **Padronização**
Interface consistente independente do projeto

---

O Makefile orquestrador **transforma a experiência** de gerenciar 3 projetos complexos em uma **interface simples e poderosa**! 🎛️✨