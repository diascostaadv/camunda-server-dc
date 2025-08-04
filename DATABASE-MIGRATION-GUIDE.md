# Guia de Migração para Bancos de Dados via URI

Este documento explica como usar os novos modos de operação nos 3 projetos, preparando para migração para Azure Managed Services.

## Visão Geral

Todos os projetos agora suportam **2 modos de operação**:

- **Modo Local**: Usa containers Docker locais para bancos de dados
- **Modo Externo**: Usa apenas URIs para conectar a serviços externos (Azure)

## Projeto 1: Camunda Platform Standalone

### Configuração dos Modos

**Modo Local (.env.local):**
```bash
EXTERNAL_DATABASE_MODE=false
DATABASE_URL=jdbc:postgresql://db:5432/camunda
```

**Modo Externo (.env.production):**
```bash
EXTERNAL_DATABASE_MODE=true
DATABASE_URL=jdbc:postgresql://your-azure-db.postgres.database.azure.com:5432/camunda?sslmode=require
```

### Comandos Disponíveis

```bash
# Modo automático (detecta configuração)
make local-up

# Forçar modo externo
make local-up-external

# Deploy sempre usa modo externo
make deploy
```

### Azure Database for PostgreSQL

**Connection String Example:**
```bash
DATABASE_URL=jdbc:postgresql://camunda-db.postgres.database.azure.com:5432/camunda?sslmode=require&user=adminuser@camunda-db&password=YourSecurePassword123
```

## Projeto 2: Worker API Gateway

### Configuração dos Modos

**Modo Local (.env.local):**
```bash
EXTERNAL_SERVICES_MODE=false
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/worker_gateway?authSource=admin
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/worker_gateway
REDIS_URI=redis://redis:6379
```

**Modo Externo (.env.production):**
```bash
EXTERNAL_SERVICES_MODE=true
MONGODB_URI=mongodb+srv://user:pass@cluster.cosmos.azure.com/worker_gateway
RABBITMQ_URL=amqps://user:pass@servicebus.servicebus.windows.net/
REDIS_URI=rediss://cache.redis.cache.windows.net:6380?ssl_cert_reqs=required
```

### Comandos Disponíveis

```bash
# Modo automático (detecta configuração)
make local-up

# Forçar modo externo
make local-up-external

# Deploy sempre usa modo externo
make deploy
```

### Azure Managed Services

**Azure Cosmos DB (MongoDB API):**
```bash
MONGODB_URI=mongodb+srv://your-cosmos:primary-key@your-cosmos.mongo.cosmos.azure.com:10255/worker_gateway?ssl=true&replicaSet=globaldb&retrywrites=false
```

**Azure Cache for Redis:**
```bash
REDIS_URI=rediss://your-redis.redis.cache.windows.net:6380?password=access-key&ssl_cert_reqs=required
```

**Azure Service Bus (alternativa ao RabbitMQ):**
```bash
RABBITMQ_URL=Endpoint=sb://your-servicebus.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=your-key
```

## Projeto 3: Workers Platform

### Configuração

O projeto de workers já estava configurado corretamente usando URIs externas:

```bash
# .env.local
CAMUNDA_URL=http://localhost:8080/engine-rest
GATEWAY_URL=http://localhost:8000

# .env.production  
CAMUNDA_URL=http://201.23.67.197:8080/engine-rest
GATEWAY_URL=http://201.23.67.197:8000
```

**Sem mudanças necessárias** ✅

## Cenários de Uso

### Cenário 1: Desenvolvimento Local Completo
```bash
# Projeto 1: Camunda com PostgreSQL local
cd camunda-platform-standalone
make local-up  # usa containers locais

# Projeto 2: Gateway com MongoDB/Redis/RabbitMQ locais  
cd camunda-worker-api-gateway
make local-up  # usa containers locais

# Projeto 3: Workers conectam aos serviços locais
cd camunda-workers-platform
make local-up
```

### Cenário 2: Híbrido (Camunda local + Azure Gateway)
```bash
# Projeto 1: Camunda local
cd camunda-platform-standalone
make local-up

# Projeto 2: Gateway com Azure services
cd camunda-worker-api-gateway
# Configure EXTERNAL_SERVICES_MODE=true no .env.local
make local-up-external

# Projeto 3: Workers conectam ao Camunda local
cd camunda-workers-platform  
make local-up
```

### Cenário 3: Produção Completa (Tudo no Azure)
```bash
# Projeto 1: Camunda com Azure PostgreSQL
cd camunda-platform-standalone
make deploy  # usa DATABASE_URL externa

# Projeto 2: Gateway com Azure services
cd camunda-worker-api-gateway
make deploy  # usa MONGODB_URI, REDIS_URI, etc. externos

# Projeto 3: Workers conectam aos serviços Azure
cd camunda-workers-platform
make deploy
```

## Processo de Migração

### Fase 1: Preparação
1. Provisionar serviços no Azure
2. Obter connection strings
3. Atualizar arquivos .env com URIs Azure

### Fase 2: Teste Híbrido
1. Migrar Projeto 2 (Gateway) primeiro
2. Testar conectividade
3. Validar funcionamento

### Fase 3: Migração Completa
1. Migrar Projeto 1 (Camunda Platform)
2. Backup e migração de dados
3. Deploy final e testes

## Troubleshooting

### Problemas Comuns

**Erro de conexão Azure:**
- Verificar firewall rules
- Validar connection strings
- Verificar SSL/TLS settings

**Profiles não funcionando:**
- Verificar se EXTERNAL_*_MODE está correto
- Usar comandos específicos (`local-up-external`)

**Performance issues:**
- Ajustar timeouts no .env
- Verificar região dos serviços Azure

### Comandos de Debug

```bash
# Verificar configuração atual
make local-status

# Testar conectividade
make health-check  # (Gateway)
make test-worker-connection  # (Workers)

# Logs detalhados
make local-logs
```

## Custos Estimados Azure

- **PostgreSQL (General Purpose, 2 vCores)**: ~R$ 400/mês
- **Cosmos DB (400 RU/s)**: ~R$ 150/mês
- **Redis Cache (Standard C1)**: ~R$ 80/mês
- **Service Bus (Standard)**: ~R$ 10/mês

**Total**: ~R$ 640/mês para ambiente de produção