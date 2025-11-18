# 🚀 Como Rodar o API Gateway Localmente

Guia rápido para executar o Worker API Gateway em ambiente de desenvolvimento local.

---

## 📋 Pré-requisitos

- Docker Desktop instalado e rodando
- Docker Compose v2+
- Make (geralmente já vem no macOS/Linux)

---

## 🎯 Método Rápido (Recomendado)

### Iniciar o Gateway com Serviços Locais

```bash
cd camunda-worker-api-gateway
make local-up
```

Isso irá:
- ✅ Criar a rede Docker `camunda-gateway-network`
- ✅ Subir MongoDB local (porta 27017)
- ✅ Subir RabbitMQ local (porta 5672, management na 15672)
- ✅ Subir Redis local (porta 6379)
- ✅ Subir API Gateway (porta 8000)
- ✅ Usar configuração do `.env.local`

### URLs Disponíveis

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **API Gateway** | http://localhost:8000 | - |
| **API Docs (Swagger)** | http://localhost:8000/docs | - |
| **Health Check** | http://localhost:8000/health | - |
| **Metrics (Prometheus)** | http://localhost:9000/metrics | - |
| **MongoDB** | mongodb://localhost:27017 | admin / admin123 |
| **RabbitMQ Management** | http://localhost:15672 | admin / admin123 |
| **Redis** | redis://localhost:6379 | - |

---

## 🔧 Comandos Disponíveis

### Gerenciamento Básico

```bash
# Iniciar Gateway (com serviços locais)
make local-up

# Iniciar Gateway (usando serviços externos Azure)
make local-up-external

# Parar Gateway
make local-down

# Reiniciar Gateway
make local-restart

# Ver logs em tempo real
make local-logs

# Verificar status dos containers
make local-status
```

### Testes e Monitoramento

```bash
# Testar se API está respondendo
make local-test

# Health check completo (Gateway + MongoDB + RabbitMQ + Redis)
make health-check
```

---

## 🧪 Testando a API

### Opção 1: Arquivo `.http` (Recomendado)

1. Abra o arquivo `api-tests.http` no VS Code
2. Instale a extensão **REST Client**
3. Clique em "Send Request" acima de qualquer requisição

### Opção 2: Swagger UI

Acesse: http://localhost:8000/docs

### Opção 3: cURL

```bash
# Health check
curl http://localhost:8000/health

# Testar busca de publicações
curl -X POST http://localhost:8000/buscar-publicacoes/test-soap \
  -H "Content-Type: application/json" \
  -d '{
    "cod_grupo": 5,
    "data_inicial": "2025-11-17",
    "data_final": "2025-11-17"
  }'

# Estatísticas
curl http://localhost:8000/publicacoes/estatisticas
```

---

## ⚙️ Configuração

### Arquivo `.env.local`

O Gateway usa o arquivo `.env.local` por padrão em modo local. Principais configurações:

```bash
# Modo de serviços
EXTERNAL_SERVICES_MODE=false  # false = usa containers locais

# Porta do Gateway
GATEWAY_PORT=8000

# Limite de publicações
DEFAULT_LIMITE_PUBLICACOES=0  # 0 = SEM LIMITE

# Log level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Modificar Configurações

1. Edite `.env.local`
2. Reinicie o Gateway:
   ```bash
   make local-restart
   ```

---

## 🐛 Troubleshooting

### Gateway não inicia

```bash
# Verificar logs
make local-logs

# Verificar se portas estão em uso
lsof -i :8000
lsof -i :27017

# Limpar e reiniciar
make local-down
docker system prune -f
make local-up
```

### MongoDB não conecta

```bash
# Verificar se container está rodando
docker ps | grep mongodb

# Testar conexão MongoDB
docker exec -it $(docker ps -qf "name=mongodb") mongosh -u admin -p admin123

# Ver logs do MongoDB
docker logs $(docker ps -qf "name=mongodb")
```

### RabbitMQ não conecta

```bash
# Verificar se container está rodando
docker ps | grep rabbitmq

# Acessar management UI
open http://localhost:15672

# Ver logs do RabbitMQ
docker logs $(docker ps -qf "name=rabbitmq")
```

### Porta 8000 já está em uso

Opção 1: Parar o serviço que está usando a porta
```bash
lsof -ti :8000 | xargs kill -9
```

Opção 2: Alterar porta no `.env.local`
```bash
GATEWAY_PORT=8001
```

---

## 📊 Monitoramento

### Ver Métricas Prometheus

```bash
curl http://localhost:9000/metrics
```

### Ver Logs em Tempo Real

```bash
make local-logs
```

### Health Check Completo

```bash
make health-check
```

Exemplo de saída:
```
🏥 Running comprehensive health check...

📡 Testing Gateway API...
{
    "status": "healthy",
    "mongodb": "connected",
    "timestamp": "2025-11-17T21:30:00.123456"
}

📊 Testing Metrics...
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="11",...} 1.0

💾 Testing MongoDB...
{ ok: 1 }

🐰 Testing RabbitMQ...
{
    "rabbitmq_version": "3.12.12",
    "cluster_name": "rabbit@...",
    ...
}

✅ Health check complete
```

---

## 🔄 Workflow de Desenvolvimento

### 1. Iniciar ambiente

```bash
make local-up
```

### 2. Fazer alterações no código

Edite arquivos em `app/`

### 3. Reiniciar para aplicar mudanças

```bash
make local-restart
```

### 4. Testar via `.http` file

Use `api-tests.http` para testar endpoints

### 5. Ver logs

```bash
make local-logs
```

---

## 🌐 Modos de Execução

### Modo 1: Serviços Locais (Desenvolvimento)

```bash
make local-up
```

- MongoDB, RabbitMQ, Redis rodando em containers
- Ideal para desenvolvimento sem dependências externas
- Dados isolados no ambiente local

### Modo 2: Serviços Externos (Testes com Azure)

```bash
make local-up-external
```

- Conecta aos serviços Azure (MongoDB Atlas, Redis Cloud, etc)
- Usa mesmas credenciais de produção
- Útil para testar integrações reais

---

## 📝 Notas Importantes

- ⚠️ **Dados Locais**: Ao usar `make local-up`, os dados do MongoDB/RabbitMQ ficam em volumes Docker locais
- ⚠️ **Limpeza**: Para limpar volumes: `docker compose --env-file .env.local down -v`
- ⚠️ **Limite Removido**: `DEFAULT_LIMITE_PUBLICACOES=0` significa SEM LIMITE de publicações
- ⚠️ **Integrações Externas**: WebJur, CPJ, DW LAW e N8N usam URLs de produção mesmo em modo local

---

## 🚀 Deploy para Produção

Após testar localmente, faça deploy para produção:

```bash
make deploy
```

Isso irá:
1. Copiar arquivos para servidor Azure via rsync
2. Fazer build da imagem Docker
3. Subir serviço em produção com `.env.production`

---

## 📚 Recursos Adicionais

- **API Documentation**: http://localhost:8000/docs (quando rodando)
- **ReDoc**: http://localhost:8000/redoc (quando rodando)
- **Arquivo de Testes**: `api-tests.http`
- **CLAUDE.md**: Documentação arquitetural do projeto

---

## ❓ Dúvidas Comuns

**Q: Como alterar o limite de publicações?**
A: Edite `DEFAULT_LIMITE_PUBLICACOES` no `.env.local` e execute `make local-restart`

**Q: Como acessar o MongoDB localmente?**
A: Use MongoDB Compass com: `mongodb://admin:admin123@localhost:27017`

**Q: Como ver mensagens do RabbitMQ?**
A: Acesse http://localhost:15672 com admin/admin123

**Q: Como ativar modo DEBUG?**
A: No `.env.local`, altere `DEBUG=true` e `LOG_LEVEL=DEBUG`, depois `make local-restart`

**Q: Como limpar completamente o ambiente?**
A: Execute:
```bash
make local-down
docker volume rm $(docker volume ls -q | grep camunda-worker-api-gateway)
docker network rm camunda-gateway-network
make local-up
```
