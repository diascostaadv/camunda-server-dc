# Camunda BPM Platform - Arquitetura Modular

Sistema Camunda BPM completo separado em 3 projetos independentes com suporte a bancos de dados locais e gerenciados (Azure).

## 🏗️ Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMUNDA BPM ECOSYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   PROJETO 1     │  │   PROJETO 2     │  │   PROJETO 3     │ │
│  │                 │  │                 │  │                 │ │
│  │  🏗️ PLATFORM    │  │  🌐 GATEWAY     │  │  👷 WORKERS     │ │
│  │                 │  │                 │  │                 │ │
│  │  • Camunda BPM  │  │  • FastAPI      │  │  • Auto-discover│ │
│  │  • PostgreSQL   │  │  • MongoDB      │  │  • Templates    │ │
│  │  • Prometheus   │  │  • RabbitMQ     │  │  • Base Classes │ │
│  │  • Grafana      │  │  • Redis        │  │  • Metrics      │ │
│  │                 │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                     │                     │         │
│           │ HTTP REST API       │ Task Processing     │ External│
│           │                     │                     │ Task    │
│           └─────────────────────┼─────────────────────┘ Client  │
│                                 │                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    AZURE MANAGED SERVICES                  │ │
│  │  • Azure Database for PostgreSQL                           │ │
│  │  • Azure Cosmos DB (MongoDB API)                           │ │
│  │  • Azure Cache for Redis                                   │ │
│  │  • Azure Service Bus                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Projetos Independentes

### 📊 Projeto 1: `camunda-platform-standalone`
**Infraestrutura Base do Camunda**

```
Responsabilidades:
├── Camunda BPM Platform 7.23.0
├── PostgreSQL 16.3 (local ou Azure)
├── Prometheus (métricas)
└── Grafana (dashboards)

Portas:
├── 8080 - Camunda Web Apps
├── 9090 - Prometheus
└── 3001 - Grafana
```

**Comandos:**
```bash
cd camunda-platform-standalone

# Desenvolvimento local
make local-up              # Auto-detecta modo (local DB)
make local-up-external     # Força uso de DB externa

# Produção
make deploy               # Deploy com Azure PostgreSQL
make remote-status        # Status dos serviços
```

### 🌐 Projeto 2: `camunda-worker-api-gateway`
**Gateway de Processamento Assíncrono**

```
Responsabilidades:
├── FastAPI Gateway
├── MongoDB (local ou Azure Cosmos DB)
├── RabbitMQ (local ou Azure Service Bus)
└── Redis (local ou Azure Cache)

Portas:
├── 8000 - Gateway API
├── 9000 - Métricas
├── 27017 - MongoDB (local)
├── 5672/15672 - RabbitMQ (local)
└── 6379 - Redis (local)
```

**Comandos:**
```bash
cd camunda-worker-api-gateway

# Desenvolvimento local
make local-up              # Auto-detecta modo (serviços locais)
make local-up-external     # Força uso de serviços externos

# Produção
make deploy               # Deploy com Azure services
make health-check         # Verificar saúde dos serviços
```

### 👷 Projeto 3: `camunda-workers-platform`
**Plataforma de Workers com Auto-Discovery**

```
Responsabilidades:
├── Sistema de auto-discovery
├── Templates de workers
├── Base classes compartilhadas
└── Workers específicos (hello-world, publicacao)

Portas:
├── 8001 - Hello World Worker metrics
└── 8002 - Publicacao Worker metrics
```

**Comandos:**
```bash
cd camunda-workers-platform

# Gerenciamento
make list-workers         # Lista workers disponíveis
make new-worker           # Cria novo worker
make build-workers        # Build de todos os workers

# Deploy
make local-up             # Workers locais
make deploy              # Workers em produção
make remote-scale W=hello-world N=5  # Escalar worker
```

## 🎛️ Modos de Operação

### 🏠 Modo Local (Desenvolvimento)
Todos os bancos de dados rodam em containers Docker locais.

```bash
# Configuração (.env.local)
EXTERNAL_DATABASE_MODE=false        # Projeto 1
EXTERNAL_SERVICES_MODE=false        # Projeto 2

# URLs internas
DATABASE_URL=jdbc:postgresql://db:5432/camunda
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/worker_gateway
REDIS_URI=redis://redis:6379
```

### ☁️ Modo Externo (Produção)
Todos os bancos conectam via URI a serviços gerenciados (Azure).

```bash
# Configuração (.env.production)
EXTERNAL_DATABASE_MODE=true         # Projeto 1
EXTERNAL_SERVICES_MODE=true         # Projeto 2

# URLs Azure
DATABASE_URL=jdbc:postgresql://camunda-db.postgres.database.azure.com:5432/camunda?sslmode=require
MONGODB_URI=mongodb+srv://user:pass@cluster.cosmos.azure.com/worker_gateway
REDIS_URI=rediss://cache.redis.cache.windows.net:6380?ssl_cert_reqs=required
```

## 🚀 Cenários de Deploy

### Cenário 1: Desenvolvimento Local Completo
```bash
# Terminal 1: Infraestrutura
cd camunda-platform-standalone && make local-up

# Terminal 2: Gateway (opcional)
cd camunda-worker-api-gateway && make local-up

# Terminal 3: Workers
cd camunda-workers-platform && make local-up
```

### Cenário 2: Híbrido (Local + Azure)
```bash
# Camunda local, Gateway no Azure
cd camunda-platform-standalone && make local-up
cd camunda-worker-api-gateway && make local-up-external
cd camunda-workers-platform && make local-up
```

### Cenário 3: Produção Completa (Azure)
```bash
# Tudo no Azure
cd camunda-platform-standalone && make deploy
cd camunda-worker-api-gateway && make deploy  
cd camunda-workers-platform && make deploy
```

## 🔧 Configuração Rápida

### 1. Setup Inicial
```bash
# Clone dos 3 projetos (já criados)
cd camunda-server-dc
ls -la
# camunda-platform-standalone/
# camunda-worker-api-gateway/
# camunda-workers-platform/
```

### 2. Configuração Local
```bash
# Cada projeto tem .env.local pré-configurado
# Não precisa alteração para desenvolvimento local
```

### 3. Configuração Azure (quando necessário)
```bash
# Copiar exemplos e configurar
cp camunda-platform-standalone/.env.azure-example .env.production
cp camunda-worker-api-gateway/.env.azure-example .env.production

# Editar com connection strings reais do Azure
nano camunda-platform-standalone/.env.production
nano camunda-worker-api-gateway/.env.production
```

## 📋 URLs de Acesso

### Desenvolvimento Local
| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Camunda | http://localhost:8080 | demo/demo |
| Grafana | http://localhost:3001 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Gateway API | http://localhost:8000 | - |
| RabbitMQ | http://localhost:15672 | admin/admin123 |
| Worker Metrics | http://localhost:8001/metrics | - |

### Produção (201.23.67.197)
| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Camunda | http://201.23.67.197:8080 | demo/demo |
| Grafana | http://201.23.67.197:3001 | admin/admin |
| Prometheus | http://201.23.67.197:9090 | - |
| Gateway API | http://201.23.67.197:8000 | - |
| Worker Metrics | http://201.23.67.197:8001/metrics | - |

## 🗄️ Bancos de Dados

### Bancos por Projeto
| Projeto | Banco Local | Azure Equivalente | Uso |
|---------|-------------|-------------------|-----|
| **Projeto 1** | PostgreSQL 16.3 | Azure Database for PostgreSQL | Camunda BPM data |
| **Projeto 2** | MongoDB 7.0 | Azure Cosmos DB (MongoDB API) | Task storage |
| **Projeto 2** | Redis 7.2 | Azure Cache for Redis | Cache/sessions |
| **Projeto 2** | RabbitMQ 3.12 | Azure Service Bus | Message queuing |
| **Projeto 3** | - | - | Sem bancos próprios |

### Estimativa de Custos Azure
| Serviço | Configuração | Custo/mês (BRL) |
|---------|-------------|-----------------|
| PostgreSQL | General Purpose, 2 vCores, 100GB | ~R$ 400 |
| Cosmos DB | 400 RU/s, 10GB | ~R$ 150 |
| Redis Cache | Standard C1, 1GB | ~R$ 80 |
| Service Bus | Standard tier | ~R$ 10 |
| **Total** | | **~R$ 640** |

## 👥 Sistema de Workers

### Workers Disponíveis
- **hello-world**: Worker de exemplo simples
- **publicacao**: Processamento de publicações

### Criando Novo Worker
```bash
cd camunda-workers-platform
make new-worker
# Assistente interativo criará:
# - workers/meu-worker/worker.json
# - workers/meu-worker/main.py
# - Dockerfile automático
```

### Escalando Workers
```bash
# Local
make local-scale W=hello-world N=3

# Remoto (Docker Swarm)
make remote-scale W=publicacao N=5
```

## 🔍 Monitoramento

### Métricas Disponíveis
- **Camunda**: Process instances, jobs, incidents
- **Gateway**: Task processing rates, queue sizes
- **Workers**: Task completion rates, errors
- **Infrastructure**: CPU, memory, network

### Dashboards Grafana
- **Camunda BPM Overview**: Métricas principais
- **Workers Performance**: Performance dos workers
- **Infrastructure**: Saúde da infraestrutura

## 🚨 Troubleshooting

### Problemas Comuns

**Containers não sobem:**
```bash
# Verificar modo de operação
grep EXTERNAL_ */.*env.local

# Usar comando correto
make local-up          # modo automático
make local-up-external # força externo
```

**Conectividade entre projetos:**
```bash
# Verificar URLs nos .env
grep -r CAMUNDA_URL */
grep -r GATEWAY_URL */

# Testar conectividade
make test-worker-connection  # workers
make health-check           # gateway
```

**Performance issues:**
```bash
# Verificar health checks
make local-status
make remote-status

# Ajustar recursos
make scale N=3              # platform
make scale-gateway N=2      # gateway
```

### Comandos de Debug
```bash
# Logs detalhados
make local-logs             # cada projeto
make worker-logs W=hello-world

# Status completo
make local-status
make remote-status

# Testes específicos
make local-test            # gateway
make worker-metrics        # workers
```

## 📚 Documentação Adicional

- [DATABASE-MIGRATION-GUIDE.md](DATABASE-MIGRATION-GUIDE.md) - Guia completo de migração para Azure
- [README-SEPARATED-PROJECTS.md](README-SEPARATED-PROJECTS.md) - Detalhes da separação dos projetos
- `*/README.md` - Documentação específica de cada projeto

## 🎯 Vantagens da Arquitetura

### ✅ Independência Total
- Deploy independente de cada projeto
- Ciclos de release separados
- Tecnologias específicas por projeto

### ✅ Escalabilidade Flexível
- Escalar apenas componentes necessários
- Load balancing por serviço
- Resource allocation otimizado

### ✅ Manutenção Simplificada
- Equipes diferentes por projeto
- Debugging isolado
- Logs e métricas específicos

### ✅ Preparação para Cloud
- Migração gradual para Azure
- Modo híbrido (local + cloud)
- Zero downtime migration

### ✅ Custo Otimizado
- Pagar apenas pelo que usar
- Escalabilidade automática
- Recursos dimensionados por necessidade

## 🎛️ Makefile Orquestrador

**Novidade!** Agora você pode gerenciar todos os 3 projetos de um lugar centralizado usando o `Makefile` na raiz do projeto.

### 🚀 Comandos Principais
```bash
# Na raiz do projeto
make start          # Inicia ecosystem completo (Platform + Workers)
make start-full     # Inicia ecosystem + Gateway
make stop           # Para todo o ecosystem
make status         # Status de todos os projetos
make health         # Health check de todos os serviços
make urls           # Lista todas as URLs de acesso
```

### 🎯 Cenários Pré-definidos
```bash
make scenario-local      # Desenvolvimento local completo
make scenario-hybrid     # Híbrido (local + cloud)
make scenario-production # Produção completa
```

### 👷 Gerenciamento de Workers
```bash
make workers-list        # Lista workers disponíveis
make workers-new         # Cria novo worker
make workers-build       # Build de todos os workers
```

### 📊 Monitoramento
```bash
make status             # Status geral
make health             # Health checks
make logs-all           # Todos os logs
```

## 🎉 Getting Started

### Opção 1: Makefile Orquestrador (Recomendado)
```bash
# Na raiz do projeto
make start              # Sistema completo em 1 comando
make urls               # Ver todas as URLs
# Acesse: http://localhost:8080 (Camunda)
```

### Opção 2: Manual por Projeto
```bash
# Start manual - projeto por projeto
cd camunda-platform-standalone && make local-up
cd camunda-workers-platform && make local-up
# Acesse: http://localhost:8080 (Camunda)
```


  🎯 Core Functionality

  - Ecosystem Management: make start, make stop, make restart
  - Individual Project Control: Platform, Gateway, and Workers management
  - Health Monitoring: Automated health checks across all services
  - Status Reporting: Consolidated status views for local and remote environments

  📊 Key Features Working

  - Auto-detection of external vs local mode configurations
  - Colored output for easy identification of different projects
  - Intelligent sequencing with proper wait times between service starts
  - Complete documentation suite with guides for every scenario

  🛠️ Available Commands

  The orchestrator provides 30+ commands covering:
  - Development: make start, make dev-setup, make dev-reset
  - Production: make deploy-all, make prod-status, make scale-*
  - Monitoring: make status, make health, make urls
  - Workers: make workers-list, make workers-new, make workers-build


**Sistema pronto para usar em menos de 5 minutos!** 🚀