# Implementação Completa: Integração CPJ-3C API

**Data**: 5 de Novembro de 2025
**Versão**: 1.0.0
**Status**: ✅ Implementado e Pronto para Uso

---

## 📋 Sumário Executivo

Implementação completa da integração com API CPJ-3C, seguindo arquitetura de orquestração com:
- **23 métodos** no serviço CPJ (`cpj_service.py`)
- **22 tópicos** Camunda organizados por categoria
- **22 handlers** no worker dedicado (`cpj_api_worker`)
- **20 endpoints** REST no Gateway organizados em 7 routers
- **Validadores** reutilizáveis (CPF/CNPJ, CNJ, datas)

---

## 🏗️ Arquitetura Implementada

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMUNDA BPMN PROCESSES                   │
│  (Service Tasks using 22 CPJ topics)                        │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ External Tasks
                ▼
┌─────────────────────────────────────────────────────────────┐
│               CPJ API WORKER (Orchestrator)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  22 Handlers organized by category:                  │  │
│  │  • Auth (2)     • Publicações (2)  • Pessoas (3)    │  │
│  │  • Processos (3) • Pedidos (3)     • Envolvidos (3) │  │
│  │  • Tramitação (3) • Documentos (3)                  │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ HTTP Requests
                ▼
┌─────────────────────────────────────────────────────────────┐
│           WORKER API GATEWAY (Business Logic)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  7 FastAPI Routers with 20 endpoints:                │  │
│  │  /cpj/publicacoes/* → 2 endpoints                    │  │
│  │  /cpj/pessoas/*     → 3 endpoints                    │  │
│  │  /cpj/processos/*   → 3 endpoints                    │  │
│  │  /cpj/pedidos/*     → 3 endpoints                    │  │
│  │  /cpj/envolvidos/*  → 3 endpoints                    │  │
│  │  /cpj/tramitacao/*  → 3 endpoints                    │  │
│  │  /cpj/documentos/*  → 3 endpoints                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CPJ Service (cpj_service.py):                       │  │
│  │  • Autenticação JWT com cache                        │  │
│  │  • 23 métodos async para API CPJ-3C                  │  │
│  │  • Token auto-renewing                               │  │
│  │  • Error handling robusto                            │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ HTTPS/JWT
                ▼
┌─────────────────────────────────────────────────────────────┐
│                   CPJ-3C API (External)                      │
│  https://ip:porta/api/v2/*                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Componentes Implementados

### 1. CPJ Service (`camunda-worker-api-gateway/app/services/cpj_service.py`)

**Responsabilidade**: Gerenciar autenticação e chamadas à API CPJ-3C

**Métodos Implementados** (23):

#### Autenticação
- `_login()` - Autentica e obtém token JWT
- `_ensure_authenticated()` - Garante token válido

#### Publicações (2)
- `buscar_publicacoes_nao_vinculadas()` - Seção 4.2
- `atualizar_publicacao()` - Seção 4.3

#### Pessoas (3)
- `consultar_pessoa()` - Seção 4.4
- `cadastrar_pessoa()` - Seção 4.5
- `atualizar_pessoa()` - Seção 4.6

#### Processos (4)
- `buscar_processo_por_numero()` - Busca simples (já existia)
- `consultar_processos()` - Seção 4.7 (busca avançada)
- `cadastrar_processo()` - Seção 4.8
- `atualizar_processo()` - Seção 4.9

#### Pedidos (3)
- `consultar_pedidos()` - Seção 4.10
- `cadastrar_pedido()` - Seção 4.11
- `atualizar_pedido()` - Seção 4.12

#### Envolvidos (3)
- `consultar_envolvidos()` - Seção 4.13
- `cadastrar_envolvido()` - Seção 4.14
- `atualizar_envolvido()` - Seção 4.15

#### Tramitação (3)
- `cadastrar_andamento()` - Seção 4.16
- `cadastrar_tarefa()` - Seção 4.17
- `atualizar_tarefa()` - Seção 4.18

#### Documentos (3)
- `consultar_documentos()` - Seção 4.19
- `baixar_documento()` - Seção 4.20
- `cadastrar_documento()` - Seção 4.21

**Características**:
- ✅ Cache de token JWT com renovação automática
- ✅ Logging detalhado com emojis
- ✅ Error handling robusto (timeout, rede, HTTP errors)
- ✅ Retorna listas/dicts vazios em vez de lançar exceções
- ✅ Timeouts configurados (30s normal, 60s documentos)

---

### 2. CPJ API Worker (`camunda-workers-platform/workers/cpj_api_worker/`)

**Responsabilidade**: Orquestrador - delega para Gateway

**Estrutura**:
```
cpj_api_worker/
├── main.py                          # Worker principal
├── worker.json                      # Metadados
├── Dockerfile                       # Container config
├── requirements.txt                 # Dependências Python
├── handlers/                        # 8 arquivos de handlers
│   ├── __init__.py
│   ├── auth_handlers.py            # Login, refresh token
│   ├── publicacoes_handlers.py     # 2 handlers
│   ├── pessoas_handlers.py         # 3 handlers
│   ├── processos_handlers.py       # 3 handlers
│   ├── pedidos_handlers.py         # 3 handlers
│   ├── envolvidos_handlers.py      # 3 handlers
│   ├── tramitacao_handlers.py      # 3 handlers
│   └── documentos_handlers.py      # 3 handlers
└── validators/                      # Validadores reutilizáveis
    ├── __init__.py
    ├── cpf_cnpj_validator.py       # Validação CPF/CNPJ
    ├── cnj_validator.py            # Validação número CNJ
    └── date_validator.py           # Validação datas
```

**Handlers Implementados** (22):

| Categoria | Tópicos | Handlers |
|-----------|---------|----------|
| Autenticação | `cpj_login`, `cpj_refresh_token` | 2 |
| Publicações | `cpj_buscar_publicacoes_nao_vinculadas`, `cpj_atualizar_publicacao` | 2 |
| Pessoas | `cpj_consultar_pessoa`, `cpj_cadastrar_pessoa`, `cpj_atualizar_pessoa` | 3 |
| Processos | `cpj_consultar_processos`, `cpj_cadastrar_processo`, `cpj_atualizar_processo` | 3 |
| Pedidos | `cpj_consultar_pedidos`, `cpj_cadastrar_pedido`, `cpj_atualizar_pedido` | 3 |
| Envolvidos | `cpj_consultar_envolvidos`, `cpj_cadastrar_envolvido`, `cpj_atualizar_envolvido` | 3 |
| Tramitação | `cpj_cadastrar_andamento`, `cpj_cadastrar_tarefa`, `cpj_atualizar_tarefa` | 3 |
| Documentos | `cpj_consultar_documentos`, `cpj_baixar_documento`, `cpj_cadastrar_documento` | 3 |
| **TOTAL** | **22 tópicos** | **22 handlers** |

**Características**:
- ✅ Padrão de orquestração (sem lógica de negócio)
- ✅ Validação básica de entrada
- ✅ Delegação via `process_via_gateway()`
- ✅ Error handling com retries configuráveis
- ✅ Logging contextual detalhado

---

### 3. Gateway Routers (`camunda-worker-api-gateway/app/routers/cpj/`)

**Responsabilidade**: Expor endpoints REST que chamam `cpj_service.py`

**Routers Implementados** (7):

#### Router de Publicações
**Arquivo**: `publicacoes_router.py`
**Prefix**: `/cpj/publicacoes`
**Endpoints** (2):
- `POST /cpj/publicacoes/nao-vinculadas` - Buscar publicações não vinculadas
- `POST /cpj/publicacoes/atualizar/{id_tramitacao}` - Atualizar publicação

#### Router de Pessoas
**Arquivo**: `pessoas_router.py`
**Prefix**: `/cpj/pessoas`
**Endpoints** (3):
- `POST /cpj/pessoas/consultar` - Consultar pessoas
- `POST /cpj/pessoas/cadastrar` - Cadastrar pessoa
- `POST /cpj/pessoas/atualizar/{codigo}` - Atualizar pessoa

#### Router de Processos
**Arquivo**: `processos_router.py`
**Prefix**: `/cpj/processos`
**Endpoints** (3):
- `POST /cpj/processos/consultar` - Consultar processos
- `POST /cpj/processos/cadastrar` - Cadastrar processo
- `POST /cpj/processos/atualizar/{pj}` - Atualizar processo

#### Router de Pedidos
**Arquivo**: `pedidos_router.py`
**Prefix**: `/cpj/pedidos`
**Endpoints** (3):
- `POST /cpj/pedidos/consultar` - Consultar pedidos
- `POST /cpj/pedidos/cadastrar/{pj}` - Cadastrar pedido
- `POST /cpj/pedidos/atualizar/{pj}/{sequencia}` - Atualizar pedido

#### Router de Envolvidos
**Arquivo**: `envolvidos_router.py`
**Prefix**: `/cpj/envolvidos`
**Endpoints** (3):
- `POST /cpj/envolvidos/consultar` - Consultar envolvidos
- `POST /cpj/envolvidos/cadastrar/{pj}` - Cadastrar envolvido
- `POST /cpj/envolvidos/atualizar/{pj}/{sequencia}` - Atualizar envolvido

#### Router de Tramitação
**Arquivo**: `tramitacao_router.py`
**Prefix**: `/cpj/tramitacao`
**Endpoints** (3):
- `POST /cpj/tramitacao/andamento/cadastrar/{pj}` - Cadastrar andamento
- `POST /cpj/tramitacao/tarefa/cadastrar/{pj}` - Cadastrar tarefa
- `POST /cpj/tramitacao/tarefa/atualizar/{id_tramitacao}` - Atualizar tarefa

#### Router de Documentos
**Arquivo**: `documentos_router.py`
**Prefix**: `/cpj/documentos`
**Endpoints** (3):
- `POST /cpj/documentos/consultar/{origem}/{id_origem}` - Consultar documentos
- `GET /cpj/documentos/baixar/{id_ged}` - Baixar documento
- `POST /cpj/documentos/cadastrar/{origem}/{id_origem}` - Cadastrar documento

**Total**: 7 routers com 20 endpoints REST

**Características**:
- ✅ Pydantic models para validação de request/response
- ✅ HTTPException para erros padronizados
- ✅ Logging consistente com emojis
- ✅ Documentação OpenAPI automática (Swagger)
- ✅ Tags organizadas por categoria

---

### 4. Configuração de Tópicos (`common/config.py`)

Tópicos adicionados à classe `Topics`:

```python
# Autenticação
CPJ_LOGIN = "cpj_login"
CPJ_REFRESH_TOKEN = "cpj_refresh_token"

# Publicações
CPJ_BUSCAR_PUBLICACOES_NAO_VINCULADAS = "cpj_buscar_publicacoes_nao_vinculadas"
CPJ_ATUALIZAR_PUBLICACAO = "cpj_atualizar_publicacao"

# Pessoas
CPJ_CONSULTAR_PESSOA = "cpj_consultar_pessoa"
CPJ_CADASTRAR_PESSOA = "cpj_cadastrar_pessoa"
CPJ_ATUALIZAR_PESSOA = "cpj_atualizar_pessoa"

# Processos
CPJ_CONSULTAR_PROCESSOS = "cpj_consultar_processos"
CPJ_CADASTRAR_PROCESSO = "cpj_cadastrar_processo"
CPJ_ATUALIZAR_PROCESSO = "cpj_atualizar_processo"

# Pedidos
CPJ_CONSULTAR_PEDIDOS = "cpj_consultar_pedidos"
CPJ_CADASTRAR_PEDIDO = "cpj_cadastrar_pedido"
CPJ_ATUALIZAR_PEDIDO = "cpj_atualizar_pedido"

# Envolvidos
CPJ_CONSULTAR_ENVOLVIDOS = "cpj_consultar_envolvidos"
CPJ_CADASTRAR_ENVOLVIDO = "cpj_cadastrar_envolvido"
CPJ_ATUALIZAR_ENVOLVIDO = "cpj_atualizar_envolvido"

# Tramitação
CPJ_CADASTRAR_ANDAMENTO = "cpj_cadastrar_andamento"
CPJ_CADASTRAR_TAREFA = "cpj_cadastrar_tarefa"
CPJ_ATUALIZAR_TAREFA = "cpj_atualizar_tarefa"

# Documentos
CPJ_CONSULTAR_DOCUMENTOS = "cpj_consultar_documentos"
CPJ_BAIXAR_DOCUMENTO = "cpj_baixar_documento"
CPJ_CADASTRAR_DOCUMENTO = "cpj_cadastrar_documento"
```

---

## 🚀 Como Usar

### 1. Configurar Variáveis de Ambiente

**Gateway** (`.env.production` ou `.env.local`):
```bash
# API CPJ-3C
CPJ_BASE_URL=https://cpj-server:porta/api/v2
CPJ_LOGIN=seu_usuario_api
CPJ_PASSWORD=sua_senha_api
CPJ_TOKEN_EXPIRY_MINUTES=60
```

**Worker CPJ** (`.env.production` ou `.env.local`):
```bash
# Gateway
GATEWAY_ENABLED=true
GATEWAY_URL=http://gateway:8000

# CPJ (para modo direto - não recomendado)
CPJ_API_BASE_URL=https://cpj-server:porta/api/v2
CPJ_API_USER=seu_usuario_api
CPJ_API_PASSWORD=sua_senha_api
```

### 2. Deploy com Docker Compose

**Gateway**:
```bash
cd camunda-worker-api-gateway
make local-up  # ou make deploy para produção
```

**Worker CPJ**:
```bash
cd camunda-workers-platform
make build-workers
make local-up  # ou make deploy para produção
```

### 3. Usar em Processos BPMN

#### Exemplo: Consultar Pessoa

**Service Task no BPMN**:
```xml
<bpmn:serviceTask id="ConsultarPessoaCPJ" name="Consultar Pessoa CPJ">
  <bpmn:extensionElements>
    <zeebe:taskDefinition type="cpj_consultar_pessoa" />
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

**Variáveis de Input**:
```json
{
  "filter": {
    "_and": [
      {"cpf_cnpj": {"_eq": "123.456.789-00"}}
    ]
  },
  "sort": "nome"
}
```

**Variáveis de Output**:
```json
{
  "success": true,
  "total": 1,
  "pessoas": [
    {
      "codigo": 123,
      "nome": "João da Silva",
      "cpf_cnpj": "123.456.789-00",
      "email": "joao@example.com",
      ...
    }
  ]
}
```

#### Exemplo: Cadastrar Processo

**Service Task no BPMN**:
```xml
<bpmn:serviceTask id="CadastrarProcessoCPJ" name="Cadastrar Processo CPJ">
  <bpmn:extensionElements>
    <zeebe:taskDefinition type="cpj_cadastrar_processo" />
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

**Variáveis de Input**:
```json
{
  "entrada": "2025-11-05T10:00:00",
  "materia": 5,
  "acao": "RTORD",
  "numero_processo": "1234567-89.2025.8.09.0000",
  "juizo": "1ª Vara Cível",
  "oj_numero": 1,
  "oj_sigla": "VC",
  "grau_risco": 50,
  "acao_ativa_passiva": 2,
  "valor_causa": 10000.00,
  "envolvidos": [
    {"qualificacao": 1, "pessoa": 123, "responsavel": 1}
  ]
}
```

**Variáveis de Output**:
```json
{
  "success": true,
  "pj": 456,
  "message": "Processo cadastrado com sucesso"
}
```

---

## 📊 Endpoints REST Disponíveis

Acesse a documentação interativa (Swagger UI):
```
http://localhost:8000/docs
```

Ou documentação alternativa (ReDoc):
```
http://localhost:8000/redoc
```

### Resumo dos Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| **Publicações** |
| POST | `/cpj/publicacoes/nao-vinculadas` | Buscar publicações não vinculadas |
| POST | `/cpj/publicacoes/atualizar/{id}` | Atualizar publicação |
| **Pessoas** |
| POST | `/cpj/pessoas/consultar` | Consultar pessoas |
| POST | `/cpj/pessoas/cadastrar` | Cadastrar pessoa |
| POST | `/cpj/pessoas/atualizar/{codigo}` | Atualizar pessoa |
| **Processos** |
| POST | `/cpj/processos/consultar` | Consultar processos |
| POST | `/cpj/processos/cadastrar` | Cadastrar processo |
| POST | `/cpj/processos/atualizar/{pj}` | Atualizar processo |
| **Pedidos** |
| POST | `/cpj/pedidos/consultar` | Consultar pedidos |
| POST | `/cpj/pedidos/cadastrar/{pj}` | Cadastrar pedido |
| POST | `/cpj/pedidos/atualizar/{pj}/{seq}` | Atualizar pedido |
| **Envolvidos** |
| POST | `/cpj/envolvidos/consultar` | Consultar envolvidos |
| POST | `/cpj/envolvidos/cadastrar/{pj}` | Cadastrar envolvido |
| POST | `/cpj/envolvidos/atualizar/{pj}/{seq}` | Atualizar envolvido |
| **Tramitação** |
| POST | `/cpj/tramitacao/andamento/cadastrar/{pj}` | Cadastrar andamento |
| POST | `/cpj/tramitacao/tarefa/cadastrar/{pj}` | Cadastrar tarefa |
| POST | `/cpj/tramitacao/tarefa/atualizar/{id}` | Atualizar tarefa |
| **Documentos** |
| POST | `/cpj/documentos/consultar/{origem}/{id}` | Consultar documentos |
| GET | `/cpj/documentos/baixar/{id_ged}` | Baixar documento |
| POST | `/cpj/documentos/cadastrar/{origem}/{id}` | Cadastrar documento |

---

## ✅ Checklist de Implementação

- [x] **CPJ Service** (`cpj_service.py`)
  - [x] 23 métodos async implementados
  - [x] Autenticação JWT com cache
  - [x] Error handling robusto
  - [x] Timeouts configurados

- [x] **CPJ API Worker** (`cpj_api_worker/`)
  - [x] Estrutura de diretórios criada
  - [x] 22 handlers implementados
  - [x] Validadores reutilizáveis
  - [x] worker.json e Dockerfile

- [x] **Gateway Routers** (`routers/cpj/`)
  - [x] 7 routers criados
  - [x] 20 endpoints REST
  - [x] Pydantic models
  - [x] Documentação OpenAPI

- [x] **Configuração**
  - [x] 22 tópicos em `common/config.py`
  - [x] Routers incluídos no `main.py`
  - [x] Variáveis de ambiente documentadas

- [x] **Documentação**
  - [x] README completo
  - [x] Exemplos de uso BPMN
  - [x] Tabela de endpoints

---

## 🎯 Próximos Passos

1. **Testes de Integração**: Criar testes end-to-end para cada endpoint
2. **Monitoramento**: Adicionar métricas Prometheus específicas de CPJ
3. **Circuit Breaker**: Implementar circuit breaker para resiliência
4. **Cache**: Adicionar cache Redis para consultas frequentes
5. **Webhooks**: Implementar notificações de eventos CPJ

---

## 📞 Suporte

Para dúvidas ou problemas:
- Verificar logs do worker: `docker logs cpj-api-worker`
- Verificar logs do gateway: `docker logs worker-api-gateway`
- Consultar documentação API CPJ-3C
- Revisar este documento

---

**Fim da Documentação** 🎉
