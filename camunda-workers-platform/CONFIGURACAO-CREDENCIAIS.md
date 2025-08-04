# 🔐 Configuração de Credenciais do Camunda para Workers

Os workers já estão **totalmente configurados** para receber credenciais do Camunda através de variáveis de ambiente.

## 📋 Variáveis de Ambiente Configuradas

### 🔧 Configuração Principal
```bash
# Conexão com Camunda
CAMUNDA_URL=http://host.docker.internal:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=demo

# Configurações do Worker
MAX_TASKS=1
LOCK_DURATION=60000
ASYNC_RESPONSE_TIMEOUT=30000
RETRIES=3
RETRY_TIMEOUT=5000
```

## 📁 Arquivos de Configuração

### 🏠 Ambiente Local (.env.local)
```bash
CAMUNDA_URL=http://host.docker.internal:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=demo
```

### ☁️ Ambiente Produção (.env.production)
```bash
CAMUNDA_URL=http://201.23.67.197:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=demo
```

## 🔄 Como os Workers Usam as Credenciais

### 1. Carregamento Automático
```python
# workers/common/config.py
CAMUNDA_URL: str = os.getenv('CAMUNDA_URL', 'http://localhost:8080/engine-rest')
CAMUNDA_USERNAME: Optional[str] = os.getenv('CAMUNDA_USERNAME', 'demo')
CAMUNDA_PASSWORD: Optional[str] = os.getenv('CAMUNDA_PASSWORD', 'demo')
```

### 2. Inicialização do Worker
```python
# workers/publicacao/main.py
def __init__(self):
    super().__init__(
        worker_id="publicacao-worker",
        base_url=WorkerConfig.CAMUNDA_URL,        # ← Usando a variável de ambiente
        auth=WorkerConfig.get_auth()              # ← (username, password) ou None
    )
```

### 3. Autenticação Automática
```python
# workers/common/config.py
@classmethod
def get_auth(cls) -> Optional[tuple]:
    """Get authentication tuple if configured"""
    if cls.CAMUNDA_USERNAME and cls.CAMUNDA_PASSWORD:
        return (cls.CAMUNDA_USERNAME, cls.CAMUNDA_PASSWORD)
    return None
```

## 🛠️ Personalizando Credenciais

### Opção 1: Editar Arquivo .env
```bash
# Edite diretamente o arquivo
nano .env.local

# Ou copie para personalizar
cp .env.local .env.local.custom
```

### Opção 2: Variáveis de Ambiente Docker
```yaml
# docker-compose.yml
environment:
  - CAMUNDA_URL=http://meu-camunda:8080/engine-rest
  - CAMUNDA_USERNAME=meu-usuario
  - CAMUNDA_PASSWORD=minha-senha
```

### Opção 3: Comando Direto
```bash
# Definir temporariamente
export CAMUNDA_URL="http://outro-servidor:8080/engine-rest"
export CAMUNDA_USERNAME="admin"
export CAMUNDA_PASSWORD="senha123"

# Iniciar worker
docker compose up worker-publicacao
```

## 🎯 Exemplos de Configuração

### Para Servidor Local
```bash
CAMUNDA_URL=http://localhost:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=demo
```

### Para Servidor Remoto
```bash
CAMUNDA_URL=http://meu-servidor.com:8080/engine-rest
CAMUNDA_USERNAME=admin
CAMUNDA_PASSWORD=senha-segura
```

### Para Camunda Cloud
```bash
CAMUNDA_URL=https://meu-cluster.zeebe.camunda.io/engine-rest
CAMUNDA_USERNAME=usuario-cloud
CAMUNDA_PASSWORD=token-acesso
```

## 🔍 Verificando Configuração

### Verificar Variáveis Carregadas
```bash
# No container do worker
docker exec -it camunda-workers-platform-worker-publicacao-1 env | grep CAMUNDA
```

### Testar Conectividade
```bash
# Teste manual de conexão
curl -u demo:demo http://localhost:8080/engine-rest/version
```

### Logs do Worker
```bash
# Ver logs de conexão
docker logs camunda-workers-platform-worker-publicacao-1
```

## 🚨 Troubleshooting

### Problema: Erro de Autenticação
```bash
# Verificar credenciais no .env
grep CAMUNDA_ .env.local

# Testar credenciais manualmente
curl -u USUARIO:SENHA http://URL/engine-rest/version
```

### Problema: URL Inacessível
```bash
# Para containers Docker, use host.docker.internal
CAMUNDA_URL=http://host.docker.internal:8080/engine-rest

# Para Docker Swarm, use nome do serviço
CAMUNDA_URL=http://camunda:8080/engine-rest
```

### Problema: Workers Não Conectam
```bash
# Verificar se Camunda está rodando
make platform-status

# Verificar logs dos workers
make workers-logs
```

## ✅ Sistema Já Configurado

**Seu sistema já está funcionando corretamente!** 🎉

- ✅ Credenciais carregadas de variáveis de ambiente
- ✅ Configuração automática por ambiente (local/produção)
- ✅ Autenticação HTTP Basic implementada
- ✅ Fallbacks para valores padrão
- ✅ Validação de configuração obrigatória

**Para alterar credenciais**: Edite os arquivos `.env.local` ou `.env.production` e reinicie os workers com `make workers-down && make workers-up`