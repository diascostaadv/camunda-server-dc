# Camunda Workers Platform

Plataforma completa e independente para gerenciamento de workers Camunda com sistema de auto-discovery, templates e escalabilidade.

## Arquitetura

- **Sistema de Auto-Discovery** (Detecção automática de workers)
- **Templates de Workers** (Criação rápida de novos workers)
- **Base Worker Class** (Classe base compartilhada)
- **Gateway Integration** (Integração opcional com API Gateway)
- **Prometheus Metrics** (Métricas por worker)

## Workers Disponíveis

- **hello-world** - Worker de exemplo simples
- **publicacao** - Worker para processamento de publicações

## Uso Local

```bash
# Listar workers
make list-workers

# Build de todos os workers
make build-workers

# Inicializar plataforma
make local-up

# Parar plataforma
make local-down

# Ver logs
make local-logs

# Status
make local-status
```

## Deploy Remoto

```bash
# Deploy completo
make deploy

# Parar remotamente
make remote-down

# Logs remotos
make remote-logs

# Status remoto
make remote-status
```

## Gerenciamento de Workers

### Criar Novo Worker
```bash
# Assistente interativo
make new-worker

# Regenerar docker-compose
make generate-compose
```

### Build de Workers
```bash
# Build todos os workers
make build-workers

# Build worker específico
make build-worker W=hello-world
```

### Escalabilidade
```bash
# Local
make local-scale W=hello-world N=3

# Remoto (Swarm)
make remote-scale W=publicacao N=5
```

## URLs de Acesso

### Local
- Hello World Metrics: http://localhost:8001/metrics
- Publicacao Metrics: http://localhost:8002/metrics

### Produção
- Hello World Metrics: http://201.23.67.197:8001/metrics
- Publicacao Metrics: http://201.23.67.197:8002/metrics

## Configuração

### Conexão Externa
Os workers se conectam a instâncias Camunda externas via:
- `CAMUNDA_URL` - URL da API REST do Camunda
- `GATEWAY_URL` - URL do Worker API Gateway (opcional)

### Arquivos de Ambiente
- `.env.local` - Desenvolvimento local
- `.env.production` - Produção remota

### Gateway Integration
```bash
# Habilitar gateway
GATEWAY_ENABLED=true
GATEWAY_URL=http://gateway-host:8000
```

## Desenvolvimento

### Setup
```bash
# Ambiente de desenvolvimento
make dev-setup

# Executar worker em dev
make dev-run-worker W=hello-world

# Validar configurações
make validate-workers
```

### Estrutura de Worker
```
workers/
├── meu-worker/
│   ├── worker.json      # Configuração
│   ├── main.py         # Código principal
│   └── requirements.txt # Dependências (opcional)
```

### Template worker.json
```json
{
  "name": "meu-worker",
  "description": "Descrição do worker",
  "topic": "meu_topico",
  "port": 8003,
  "dependencies": [],
  "environment": {
    "CUSTOM_VAR": "valor"
  }
}
```

## Utilitários

```bash
# Logs de worker específico
make worker-logs W=hello-world

# Shell no worker
make worker-shell W=publicacao

# Métricas dos workers
make worker-metrics

# Testar conexão com Camunda
make test-worker-connection
```

## Monitoramento

- Métricas Prometheus por worker
- Health checks automáticos
- Logs estruturados
- Auto-discovery de workers ativos

## Sistema de Auto-Discovery

O sistema automaticamente:
1. Descobre workers pela presença de `worker.json`
2. Gera docker-compose dinâmicamente
3. Configura networking e ports
4. Aplica configurações específicas por worker