# 🚀 Camunda Server DC - CI/CD Pipeline

Este repositório implementa um pipeline CI/CD completo para deploy da plataforma Camunda com todos os serviços necessários.

## 📋 Serviços Incluídos

- **Camunda Platform** - Motor de processos BPMN
- **API Gateway** - Gateway de API com integração de IA
- **Workers Platform** - Workers para processamento de tasks
- **Portainer** - Interface de gerenciamento Docker
- **N8N** - Automação de workflows
- **Prometheus** - Monitoramento
- **Grafana** - Dashboards de monitoramento

## 🏗️ Estrutura do Projeto

```
camunda-server-dc/
├── Makefile                           # Pipeline principal
├── scripts/
│   ├── deploy_bpmns.py               # Deploy automático de BPMNs
│   ├── install_docker.sh             # Instalação do Docker
│   ├── init_swarm.sh                 # Inicialização do Docker Swarm
│   └── setup-monitoring.sh           # Configuração de monitoramento
├── camunda-platform-standalone/
│   ├── Makefile                     # Deploy da plataforma Camunda
│   ├── docker-compose.yml           # Configuração Docker
│   └── resources/                   # Arquivos BPMN
├── camunda-worker-api-gateway/
│   ├── Makefile                     # Deploy do API Gateway
│   └── docker-compose.yml           # Configuração Docker
└── camunda-workers-platform/
    ├── Makefile                     # Deploy dos Workers
    └── docker-compose.yml           # Configuração Docker
```

## 🚀 Como Usar

### 1. Configuração Inicial

```bash
# Verificar requisitos do servidor remoto
make check-requirements

# Setup da infraestrutura (se necessário)
make setup-infrastructure
```

### 2. Deploy Completo

```bash
# Pipeline CI/CD completo
make ci-cd

# Ou deploy individual
make deploy-camunda-platform
make deploy-api-gateway
make deploy-workers
make deploy-bpmns
```

### 3. Deploy de Serviços Individuais

```bash

# Deploy do Portainer
make deploy-portainer

# Deploy do N8N
make deploy-n8n
```

### 4. Verificação e Monitoramento

```bash
# Status de todos os serviços
make status

# Logs de todos os serviços
make logs

# Backup do sistema
make backup
```

## 🔧 Comandos Disponíveis

### Comandos Principais

- `make ci-cd` - Pipeline completo
- `make deploy-all` - Deploy de todos os serviços
- `make deploy-bpmns` - Deploy dos processos BPMN

### Comandos de Deploy Individual

- `make deploy-camunda-platform` - Deploy da plataforma Camunda
- `make deploy-api-gateway` - Deploy do API Gateway
- `make deploy-workers` - Deploy dos Workers
- `make deploy-portainer` - Deploy do Portainer
- `make deploy-n8n` - Deploy do N8N

### Comandos de Infraestrutura

- `make setup-infrastructure` - Setup completo da infraestrutura
- `make install-docker` - Instalar Docker no servidor remoto
- `make install-make` - Instalar make no servidor remoto
- `make init-swarm` - Inicializar Docker Swarm
- `make setup-monitoring` - Configurar monitoramento

### Comandos de Manutenção

- `make status` - Verificar status dos serviços
- `make logs` - Visualizar logs dos serviços
- `make restart-all` - Reiniciar todos os serviços
- `make stop-all` - Parar todos os serviços
- `make cleanup` - Limpeza do servidor remoto
- `make backup` - Criar backup do sistema

## 📊 Monitoramento

Após o deploy, você terá acesso aos seguintes serviços:

- **Camunda**: http://dccamunda.duckdns.org:8080
- **API Gateway**: http://dccamunda.duckdns.org:8000
- **Portainer**: http://dccamunda.duckdns.org:9000
- **Grafana**: http://dccamunda.duckdns.org:3001 (admin/admin)
- **Prometheus**: http://dccamunda.duckdns.org:9090

## 🔒 Segurança

- Todos os arquivos `.env` estão protegidos pelo `.gitignore`
- Chaves API são gerenciadas através de variáveis de ambiente
- Scripts de deploy incluem verificações de segurança
- Backup automático antes de cada deploy

## 🛠️ Troubleshooting

### Problemas de Conectividade

```bash
# Verificar conectividade SSH
make check-requirements

# Verificar status dos serviços
make status
```

### Problemas de Deploy

```bash
# Ver logs de erro
make logs

# Reiniciar serviços
make restart-all
```

### Limpeza do Sistema

```bash
# Limpeza completa
make cleanup

# Backup antes de limpeza
make backup
```

## 📚 Documentação Adicional

- [Camunda Platform Documentation](https://docs.camunda.org/)
- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [Portainer Documentation](https://documentation.portainer.io/)

## 🤝 Suporte

Para problemas ou dúvidas:

1. Verifique os logs: `make logs`
2. Verifique o status: `make status`
3. Consulte a documentação específica de cada serviço
4. Execute `make help` para ver todos os comandos disponíveis
