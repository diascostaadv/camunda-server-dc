# 🔐 Cache de Tokens com Redis

**Implementação**: Token Cache Service
**Objetivo**: Evitar autenticações desnecessárias nas APIs externas
**Método**: Redis com expiração automática

---

## 🎯 Problema Resolvido

### ANTES (Sem Cache)
```
Request 1 → Autenticar CPJ → Obter token → Usar token → Descartar
Request 2 → Autenticar CPJ → Obter token → Usar token → Descartar
Request 3 → Autenticar CPJ → Obter token → Usar token → Descartar
...

Resultado: Autenticação a CADA request (lento, desnecessário)
Logs: 🔐 Autenticando no CPJ... (em cada chamada)
```

### DEPOIS (Com Cache Redis)
```
Request 1 → Cache vazio → Autenticar CPJ → Salvar token no Redis → Usar
Request 2 → Cache HIT → Usar token do Redis (não autentica)
Request 3 → Cache HIT → Usar token do Redis (não autentica)
...
Request N (após 30 min) → Cache expirado → Autenticar → Salvar → Usar

Resultado: Autenticação apenas quando necessário
Logs: ♻️ Token CPJ recuperado do cache Redis
```

---

## 🏗️ Arquitetura do Cache

### Fluxo de Autenticação com Cache

```
┌─────────────────────────────────────────────────────────────┐
│  CPJService / DWLawService                                  │
│                                                              │
│  _ensure_authenticated()                                     │
│    │                                                         │
│    ├─ 1. Verificar cache em memória                        │
│    │   └─ Se válido → Usar token ✅                        │
│    │                                                         │
│    ├─ 2. Verificar cache Redis                             │
│    │   └─ Se válido → Recuperar → Salvar em memória ✅    │
│    │                                                         │
│    └─ 3. Fazer login na API                                │
│        └─ Salvar em memória + Redis ✅                     │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Redis                                                       │
│                                                              │
│  token:cpj:api         → {token, expires_at, ...}           │
│  token:dw_law:usuario  → {token, expires_at, ...}           │
│                                                              │
│  TTL Automático: Token expira automaticamente após 30 min   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Arquivos Criados/Modificados

### Novo Arquivo
1. **`app/services/token_cache_service.py`** ✅
   - Classe `TokenCacheService`
   - Métodos: `get_token()`, `set_token()`, `delete_token()`
   - Singleton: `get_token_cache()`
   - Health check do Redis

### Arquivos Modificados
2. **`app/services/cpj_service.py`** ✅
   - Import `get_token_cache()`
   - `_ensure_authenticated()` verifica Redis antes de autenticar
   - `_login()` salva token no Redis após autenticação

3. **`app/services/dw_law_service.py`** ✅
   - Import `get_token_cache()`
   - `_ensure_authenticated()` verifica Redis antes de autenticar
   - `_autenticar()` salva token no Redis após autenticação

---

## 🔑 Estrutura das Chaves Redis

### Padrão de Chaves
```
token:{api_name}:{usuario}
```

### Exemplos
```
token:cpj:api                            → Token do CPJ (login: api)
token:dw_law:integ_dias_cons@dwlaw.com.br → Token do DW LAW
```

### Dados Armazenados
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-11-07T17:51:25.041196",
  "created_at": "2025-11-07T17:21:25.041196",
  "api_name": "cpj",
  "usuario": "api",
  "base_url": "https://app.leviatan.com.br/..."
}
```

### TTL (Time To Live)
```
CPJ:     30 minutos - 1 minuto = 29 minutos
DW LAW:  120 minutos - 1 minuto = 119 minutos

(1 minuto de margem de segurança para evitar uso de token prestes a expirar)
```

---

## 💾 Métodos Disponíveis

### TokenCacheService

```python
# Obter instância (singleton)
cache = get_token_cache()

# Recuperar token
token_data = cache.get_token("cpj", "api")
if token_data:
    token = token_data["token"]

# Salvar token
cache.set_token(
    api_name="cpj",
    token="eyJhbGc...",
    expires_at=datetime.now() + timedelta(minutes=30),
    usuario="api",
    extra_data={"base_url": "https://..."}
)

# Remover token
cache.delete_token("cpj", "api")

# Informações do token (sem o valor)
info = cache.get_token_info("cpj", "api")

# Limpar todos os tokens de uma API
cache.clear_all_tokens("cpj")

# Limpar TODOS os tokens
cache.clear_all_tokens()

# Health check do Redis
health = cache.health_check()
```

---

## 📊 Logs Esperados

### Primeiro Request (Cache Vazio)
```
CPJService inicializado - Base URL: https://app.leviatan.com.br/...
🔧 Cache Redis: ✅ Habilitado
🔐 Autenticando no CPJ...
✅ Autenticação CPJ bem-sucedida - Token válido até 2025-11-07 17:51:25
💾 Token armazenado no cache: token:cpj:api (TTL: 1740s / ~29min)
```

### Segundo Request (Cache Hit)
```
♻️ Token CPJ recuperado do cache Redis - Válido até 2025-11-07 17:51:25
🔍 Buscando processo 0012205-60.2015.5.15.0077 no CPJ...
```

### Request Após Expiração (30 min depois)
```
🔍 Token não encontrado no cache: token:cpj:api
🔐 Autenticando no CPJ...
✅ Autenticação CPJ bem-sucedida - Token válido até 2025-11-07 18:21:25
💾 Token armazenado no cache: token:cpj:api (TTL: 1740s / ~29min)
```

---

## 🧪 Como Testar o Cache

### Teste 1: Verificar Tokens em Cache

```bash
# Conectar ao Redis (local)
docker exec -it camunda-worker-api-gateway-redis-1 redis-cli

# Listar tokens
KEYS token:*

# Ver token CPJ
GET token:cpj:api

# Ver token DW LAW
GET token:dw_law:integ_dias_cons@dwlaw.com.br

# Ver TTL restante
TTL token:cpj:api
```

### Teste 2: Fazer Múltiplos Requests

```bash
# Request 1 (autentica)
curl -X POST http://201.23.69.65:8080/cpj/processos/buscar-por-numero \
  -H 'Content-Type: application/json' \
  -d '{"numero_cnj":"0012205-60.2015.5.15.0077"}' | jq .

# Request 2 (usa cache - não autentica)
curl -X POST http://201.23.69.65:8080/cpj/processos/buscar-por-numero \
  -H 'Content-Type: application/json' \
  -d '{"numero_cnj":"1000655-90.2016.5.02.0008"}' | jq .

# Request 3 (usa cache - não autentica)
curl -X POST http://201.23.69.65:8080/cpj/processos/buscar-por-numero \
  -H 'Content-Type: application/json' \
  -d '{"numero_cnj":"0329056-75.2017.8.13.0000"}' | jq .
```

**Logs esperados**:
```
Request 1: 🔐 Autenticando no CPJ... → 💾 Token armazenado
Request 2: ♻️ Token CPJ recuperado do cache
Request 3: ♻️ Token CPJ recuperado do cache
```

### Teste 3: Verificar Expiração Automática

```bash
# Inserir token manualmente com TTL de 30 segundos
docker exec -it camunda-worker-api-gateway-redis-1 redis-cli
SETEX token:test:user 30 '{"token":"test123"}'

# Aguardar 30 segundos
sleep 30

# Verificar que expirou
GET token:test:user
# (nil)
```

---

## 🔄 Benefícios do Cache

### Performance
- ✅ **Reduz latência**: Não precisa autenticar a cada request
- ✅ **Reduz carga**: Menos calls para APIs externas
- ✅ **Mais rápido**: Cache Redis é muito rápido (< 1ms)

### Confiabilidade
- ✅ **Fallback**: Se Redis falhar, autentica normalmente
- ✅ **Auto-recuperação**: Tokens expiram automaticamente
- ✅ **Margem de segurança**: TTL com 1 minuto a menos

### Exemplo de Ganho
```
Sem Cache:
- Request 1: 150ms (100ms auth + 50ms busca)
- Request 2: 150ms (100ms auth + 50ms busca)
- Request 3: 150ms (100ms auth + 50ms busca)
Total: 450ms

Com Cache:
- Request 1: 150ms (100ms auth + 50ms busca + cache)
- Request 2: 50ms (0ms auth + 50ms busca)
- Request 3: 50ms (0ms auth + 50ms busca)
Total: 250ms (44% mais rápido)
```

---

## ⚙️ Configuração

### Redis URI (já configurado)
```bash
# Local
REDIS_URI=redis://redis:6379

# Produção
REDIS_URI=redis://redis:6379
# OU Azure Redis Cache:
# REDIS_URI=redis://azure-redis:6380?ssl=true&password=xxx
```

### Timeouts
```python
# token_cache_service.py linhas 30-33
socket_connect_timeout=5   # 5s para conectar
socket_timeout=5           # 5s para operações
retry_on_timeout=True      # Retry automático
health_check_interval=30   # Health check a cada 30s
```

---

## 🆘 Troubleshooting

### Cache não funciona (Redis offline)
```
Logs:
❌ Erro ao conectar no Redis: ...
⚠️ Cache de tokens DESABILITADO - autenticação será feita a cada request

Solução:
- Sistema continua funcionando (autentica a cada request)
- Verificar se Redis está rodando: docker ps | grep redis
- Iniciar Redis: docker compose up -d redis
```

### Token expirado antes do TTL
```
Logs:
⏰ Token expirado no cache: token:cpj:api

Causa:
- API mudou tempo de expiração
- Relógio do servidor diferente

Solução:
- Token é renovado automaticamente
- Ajustar CPJ_TOKEN_EXPIRY_MINUTES no .env
```

### Muitas autenticações (cache não está funcionando)
```
Verificar:
1. Redis está rodando?
   docker ps | grep redis

2. Gateway conecta no Redis?
   docker logs camunda-worker-api-gateway-gateway-1 | grep Redis

3. Ver tokens em cache:
   docker exec -it camunda-worker-api-gateway-redis-1 redis-cli KEYS token:*
```

---

## 📊 Monitoramento

### Verificar Tokens em Cache
```bash
# Conectar ao Redis
docker exec -it camunda-worker-api-gateway-redis-1 redis-cli

# Listar todos os tokens
KEYS token:*

# Ver detalhes de um token
GET token:cpj:api

# Ver TTL restante (segundos)
TTL token:cpj:api

# Contar tokens em cache
DBSIZE
```

### Logs para Monitorar
```bash
# Ver logs de cache
docker logs camunda-worker-api-gateway-gateway-1 | grep -E "(cache|Cache|Redis|Token)"

# Filtrar apenas recuperação de cache
docker logs camunda-worker-api-gateway-gateway-1 | grep "♻️"

# Filtrar apenas armazenamento
docker logs camunda-worker-api-gateway-gateway-1 | grep "💾"
```

---

## 🔧 Operações de Manutenção

### Limpar Cache Manualmente
```bash
# Via Redis CLI
docker exec -it camunda-worker-api-gateway-redis-1 redis-cli

# Limpar tokens específicos
DEL token:cpj:api
DEL token:dw_law:integ_dias_cons@dwlaw.com.br

# Limpar todos os tokens
KEYS token:* | xargs redis-cli DEL

# OU usar padrão
EVAL "return redis.call('del', unpack(redis.call('keys', 'token:*')))" 0
```

### Verificar Health do Cache
```bash
# Via API (quando implementado endpoint)
curl http://201.23.69.65:8080/cache/health | jq .
```

---

## 📝 Estrutura do Código

### TokenCacheService

```python
class TokenCacheService:
    def __init__(self):
        self._initialize_redis()  # Conecta ao Redis

    def get_token(api_name, usuario):
        """Busca token no Redis"""
        # 1. Gera chave: token:{api}:{usuario}
        # 2. Busca no Redis
        # 3. Valida expiração
        # 4. Retorna token ou None

    def set_token(api_name, token, expires_at, usuario):
        """Salva token no Redis com TTL"""
        # 1. Prepara dados (token + metadata)
        # 2. Calcula TTL (expires_at - now - 60s)
        # 3. Salva com SETEX (expira automaticamente)
        # 4. Log de confirmação

    def delete_token(api_name, usuario):
        """Remove token do cache"""

    def health_check():
        """Verifica Redis online"""
```

### Integração nos Services

```python
class CPJService:
    def __init__(self):
        self.token_cache = get_token_cache()  # Singleton

    async def _ensure_authenticated(self):
        # 1. Memória?
        if self._token and not expired:
            return

        # 2. Redis?
        cached = self.token_cache.get_token("cpj", self.login)
        if cached:
            self._token = cached["token"]
            return

        # 3. Login
        await self._login()

    async def _login(self):
        # ... autenticar ...
        self._token = response.json()["token"]

        # Salvar no Redis
        self.token_cache.set_token("cpj", self._token, expires_at, ...)
```

---

## 🎯 Resultado Esperado

### Performance
- **Primeiro request**: 150-200ms (autentica + busca)
- **Requests seguintes**: 50-100ms (apenas busca)
- **Redução**: ~50-70% no tempo de resposta

### Logs
```
2025-11-07 17:25:00,000 - CPJService inicializado
2025-11-07 17:25:00,001 - 🔧 Cache Redis: ✅ Habilitado
2025-11-07 17:25:00,100 - 🔐 Autenticando no CPJ...
2025-11-07 17:25:00,250 - ✅ Autenticação CPJ bem-sucedida
2025-11-07 17:25:00,251 - 💾 Token armazenado no cache (TTL: 1740s / ~29min)
2025-11-07 17:25:05,000 - ♻️ Token CPJ recuperado do cache Redis
2025-11-07 17:25:10,000 - ♻️ Token CPJ recuperado do cache Redis
2025-11-07 17:25:15,000 - ♻️ Token CPJ recuperado do cache Redis
```

---

## ✅ Checklist de Implementação

- [x] TokenCacheService criado
- [x] Integração com CPJService
- [x] Integração com DWLawService
- [x] Redis no requirements.txt
- [x] Tratamento de erro (fallback)
- [x] TTL com margem de segurança
- [x] Logs detalhados
- [x] Documentação
- [ ] Deploy em produção
- [ ] Testes de carga

---

## 🚀 Deploy

Para ativar o cache em produção:

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway

# Deploy com cache implementado
make deploy

# Verificar logs
ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65 "docker logs -f camunda-worker-api-gateway-gateway-1 | grep -E '(Cache|cache|Redis|Token)'"
```

---

**✅ Cache de tokens implementado com Redis! Pronto para deploy.**

**Benefícios**:
- ⚡ 50-70% mais rápido
- 📉 Menos load nas APIs externas
- 💾 Tokens persistentes entre restarts do Gateway
- 🔄 Expiração automática
