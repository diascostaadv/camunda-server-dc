# 🚀 Camunda Workers - Scalable System

Este diretório contém o sistema escalável de workers para Camunda BPM. O sistema automaticamente descobre workers baseado na estrutura de diretórios e gera configurações do Docker Compose dinamicamente.

## 📁 Estrutura

```
workers/
├── _config/                 # Scripts de configuração e discovery
│   ├── worker_discovery.py  # Sistema de auto-discovery
│   ├── generate-compose.py  # Gerador de docker-compose.swarm.yml
│   └── new-worker.py        # Gerador de novos workers
├── _templates/              # Templates para novos workers
│   ├── worker.json          # Template de configuração
│   ├── main.py              # Template de código Python
│   └── Dockerfile           # Template de Dockerfile (opcional)
├── common/                  # Módulos compartilhados
├── hello-world/             # Worker de exemplo
│   ├── worker.json          # Configuração do worker
│   └── main.py              # Código principal
├── publicacao/              # Worker de publicação
│   ├── worker.json
│   ├── main.py
│   └── *.py                 # Arquivos auxiliares
└── Dockerfile               # Dockerfile base para todos os workers
```

## 🎯 Como Funciona

### 1. Auto-Discovery
O sistema scannea automaticamente por arquivos `worker.json` nos subdiretórios e descobre workers configurados.

### 2. Configuração por JSON
Cada worker tem um arquivo `worker.json` que define:
- Nome, porta, tópicos
- Dependências, réplicas
- Variáveis de ambiente específicas

### 3. Geração Dinâmica
O `docker-compose.swarm.yml` é gerado automaticamente baseado nos workers descobertos.

## 🛠️ Comandos Disponíveis

### Descoberta e Listagem
```bash
# Descobrir todos os workers
make discover-workers

# Listar workers disponíveis
make list-workers
```

### Criação de Novos Workers
```bash
# Criar novo worker (modo interativo)
make new-worker

# Criar worker via linha de comando
cd workers/_config && python3 new-worker.py email-sender --port 8003 --topic send_email
```

### Build e Deploy
```bash
# Construir todos os workers
make build-all-workers

# Gerar docker-compose.swarm.yml dinamicamente
make generate-compose

# Deploy completo (gera compose + build + deploy)
make deploy-workers

# Deploy tradicional (inclui geração automática)
ENVIRONMENT=production make deploy
```

### Gerenciamento Individual
```bash
# Construir worker específico
make build-worker-publicacao

# Ver logs de worker específico
make logs-worker-publicacao
make logs-worker-hello-world

# Status dos workers
make worker-status
```

## 📝 Criando um Novo Worker

### Opção 1: Interativo
```bash
make new-worker
```

### Opção 2: Manual
1. Criar diretório: `workers/meu-worker/`
2. Criar `worker.json`:
```json
{
  "name": "meu-worker",
  "description": "Meu Worker personalizado",
  "entry_point": "main.py",
  "port": 8005,
  "topics": ["meu_topico"],
  "depends_on": ["camunda"],
  "environment": {
    "CUSTOM_VAR": "valor"
  },
  "max_tasks": 1,
  "replicas": 1
}
```

3. Criar `main.py` (usar template como base)
4. Executar `make deploy-workers`

## 🔧 Configuração worker.json

### Campos Obrigatórios
- `name`: Nome único do worker
- `entry_point`: Arquivo principal (ex: main.py)
- `port`: Porta única para métricas

### Campos Opcionais
- `description`: Descrição do worker
- `topics`: Array de tópicos que o worker processa
- `depends_on`: Serviços que o worker depende
- `environment`: Variáveis de ambiente específicas
- `max_tasks`, `lock_duration`, etc.: Configurações do Camunda
- `replicas`: Número de réplicas no Swarm

### Exemplo Completo
```json
{
  "name": "email-sender",
  "description": "Email Sender Worker",
  "entry_point": "main.py",
  "port": 8003,
  "topics": ["send_email", "send_notification"],
  "depends_on": ["camunda", "redis"],
  "environment": {
    "SMTP_HOST": "${SMTP_HOST:-localhost}",
    "SMTP_PORT": "${SMTP_PORT:-587}"
  },
  "max_tasks": 2,
  "lock_duration": 60000,
  "replicas": 2,
  "version": "1.0.0"
}
```

## 🐳 Docker e Build

### Dockerfile Personalizado
Se um worker precisar de dependências específicas, crie um `Dockerfile` no diretório do worker.

### Dockerfile Base
O `workers/Dockerfile` base é usado para workers que não têm Dockerfile personalizado. Ele suporta:
- Múltiplos workers via `ARG WORKER_DIR`
- Módulos common compartilhados
- Copy automático do código do worker

### Build Process
1. Sistema detecta se existe `Dockerfile` personalizado
2. Se sim: usa Dockerfile do worker
3. Se não: usa Dockerfile base com `--build-arg WORKER_DIR=nome`

## 📊 Monitoramento

Cada worker expõe métricas na porta configurada:
```
http://localhost:${WORKER_PORT}/metrics
```

URLs são automaticamente adicionadas ao `make monitoring-status`.

## 🔄 Deploy Process

### Fluxo Automático (make deploy)
1. Copia arquivos para servidor remoto
2. Descobre workers via `worker_discovery.py`
3. Gera `docker-compose.swarm.yml` dinamicamente
4. Constrói imagens de todos os workers
5. Faz deploy no Docker Swarm

### Fluxo Manual
```bash
make generate-compose    # Gera compose
make build-all-workers   # Constrói workers
make deploy-workers      # Deploy no Swarm
```

## 🆘 Troubleshooting

### Worker não aparece no discovery
- Verificar se `worker.json` existe e está válido
- Verificar se não está em diretório `_config` ou `_templates`
- Executar `make discover-workers` para debug

### Erro no build
- Verificar se `main.py` existe
- Verificar se Dockerfile está correto
- Verificar dependências no `requirements.txt`

### Worker não sobe no Swarm
- Verificar logs: `make logs-worker-NOME`
- Verificar se imagem foi construída
- Verificar se porta não está em conflito

## 💡 Dicas

1. **Portas**: Use portas sequenciais a partir de 8001
2. **Nomes**: Use kebab-case (meu-worker)
3. **Tópicos**: Use snake_case (meu_topico)
4. **Testes**: Teste localmente antes do deploy
5. **Dependencies**: Mantenha `requirements.txt` limpo

## 🎉 Benefícios

- ✅ **Zero configuração manual** do docker-compose
- ✅ **Adição de worker em 2 minutos**
- ✅ **Consistência garantida** entre workers
- ✅ **Auto-discovery** de novos workers
- ✅ **Templates prontos** para uso
- ✅ **Build e deploy automáticos**
- ✅ **Monitoramento integrado**
- ✅ **Facilidade de manutenção**