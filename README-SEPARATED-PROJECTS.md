# Separação em 3 Projetos Independentes

Este documento descreve a nova arquitetura com 3 projetos totalmente independentes, cada um com responsabilidades específicas.

## Visão Geral da Separação

### Antes (Monólito)
```
camunda-swarm/
├── docker-compose.yml (tudo junto)
├── workers/
├── worker-api-gateway/
├── config/
└── Makefile (complexo)
```

### Depois (3 Projetos Independentes)
```
camunda-platform-standalone/     # Projeto 1: Infraestrutura
camunda-worker-api-gateway/      # Projeto 2: Gateway
camunda-workers-platform/        # Projeto 3: Workers
```

## Projeto 1: Camunda Platform Standalone

**Localização:** `camunda-platform-standalone/`

### Responsabilidades
- Camunda BPM Platform
- PostgreSQL (banco de dados)
- Prometheus (métricas)
- Grafana (dashboards)

### Comandos Principais
```bash
# Local
make local-up
make local-down
make local-logs
make local-status

# Remoto
make deploy
make remote-down
make remote-logs
make remote-status
```

### URLs
- **Local:** http://localhost:8080 (Camunda), http://localhost:3001 (Grafana)
- **Produção:** http://201.23.67.197:8080 (Camunda), http://201.23.67.197:3001 (Grafana)

## Projeto 2: Worker API Gateway

**Localização:** `camunda-worker-api-gateway/`

### Responsabilidades
- FastAPI Gateway para processamento assíncrono
- MongoDB (armazenamento de tarefas)
- RabbitMQ (filas de mensagens)
- Redis (cache)

### Comandos Principais
```bash
# Local
make local-up
make local-down
make local-test
make health-check

# Remoto
make deploy
make remote-down
make remote-test
make scale-gateway N=3
```

### URLs
- **Local:** http://localhost:8000 (API), http://localhost:15672 (RabbitMQ)
- **Produção:** http://201.23.67.197:8000 (API), http://201.23.67.197:15672 (RabbitMQ)

## Projeto 3: Workers Platform

**Localização:** `camunda-workers-platform/`

### Responsabilidades
- Sistema de auto-discovery de workers
- Templates para criação de novos workers
- Workers hello-world e publicacao
- Integração com Gateway (opcional)

### Comandos Principais
```bash
# Gerenciamento
make list-workers
make new-worker
make build-workers
make generate-compose

# Local
make local-up
make local-down
make local-scale W=hello-world N=3

# Remoto
make deploy
make remote-scale W=publicacao N=5
```

### URLs
- **Local:** http://localhost:8001/metrics (hello-world), http://localhost:8002/metrics (publicacao)
- **Produção:** http://201.23.67.197:8001/metrics, http://201.23.67.197:8002/metrics

## Cenários de Deploy

### Cenário 1: Tudo Local (Desenvolvimento)
```bash
# Terminal 1: Camunda Platform
cd camunda-platform-standalone
make local-up

# Terminal 2: Gateway (opcional)
cd camunda-worker-api-gateway
make local-up

# Terminal 3: Workers
cd camunda-workers-platform
CAMUNDA_URL=http://localhost:8080/engine-rest make local-up
```

### Cenário 2: Distribuído (Produção)
```bash
# Servidor A (201.23.67.197): Camunda Platform
cd camunda-platform-standalone
make deploy

# Servidor B: Gateway
cd camunda-worker-api-gateway
make deploy

# Servidor C: Workers
cd camunda-workers-platform
CAMUNDA_URL=http://201.23.67.197:8080/engine-rest make deploy
```

### Cenário 3: Híbrido (Dev + Prod)
```bash
# Remoto: Camunda Platform
cd camunda-platform-standalone && make deploy

# Local: Workers para desenvolvimento
cd camunda-workers-platform
CAMUNDA_URL=http://201.23.67.197:8080/engine-rest make local-up
```

## Configuração de Conectividade

### Workers → Camunda Platform
```bash
# .env.local
CAMUNDA_URL=http://localhost:8080/engine-rest

# .env.production
CAMUNDA_URL=http://201.23.67.197:8080/engine-rest
```

### Workers → Gateway (opcional)
```bash
# .env.local
GATEWAY_ENABLED=true
GATEWAY_URL=http://localhost:8000

# .env.production
GATEWAY_ENABLED=true
GATEWAY_URL=http://201.23.67.197:8000
```

## Vantagens da Separação

### 1. Independência Total
- Cada projeto pode ser desenvolvido e deployado independentemente
- Ciclos de release independentes
- Tecnologias específicas por projeto

### 2. Escalabilidade Específica
- Escalar só o que precisa (workers vs infraestrutura)
- Load balancing por componente
- Resource allocation otimizado

### 3. Manutenção Simplificada
- Equipes diferentes podem trabalhar em cada projeto
- Debugging isolado
- Logs e métricas específicos

### 4. Flexibilidade de Deploy
- Multi-cloud (cada projeto em provedor diferente)
- Ambientes híbridos (local dev + remote prod)
- Disaster recovery por componente

### 5. Reusabilidade
- Camunda Platform pode ser usado para outros workers
- Gateway pode processar tarefas de outras fontes
- Workers podem conectar a outros Camundas

## Guia de Migração

### 1. Clone dos Projetos
```bash
git clone <repo-url> camunda-platform-standalone
git clone <repo-url> camunda-worker-api-gateway
git clone <repo-url> camunda-workers-platform
```

### 2. Configuração de URLs
Ajustar os arquivos `.env.local` e `.env.production` em cada projeto com as URLs corretas.

### 3. Deploy Ordenado
1. **Primeiro:** Camunda Platform (infraestrutura base)
2. **Segundo:** Gateway (se necessário)
3. **Terceiro:** Workers (conectam aos anteriores)

### 4. Testes de Conectividade
```bash
# Testar cada projeto independentemente
make local-status  # ou remote-status
make local-test    # quando disponível
```

## Próximos Passos

1. **Documentar APIs** - Swagger/OpenAPI para o Gateway
2. **CI/CD Pipelines** - Pipeline independente por projeto
3. **Monitoring** - Métricas cross-project
4. **Security** - Authentication entre projetos
5. **Backup/Restore** - Estratégia por componente