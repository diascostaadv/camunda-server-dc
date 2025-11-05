# CPJ API Worker

Worker unificado para integração com API CPJ-3C.

## Características

- **22 tópicos Camunda** para 21 endpoints da API
- **Autenticação JWT** gerenciada automaticamente com cache
- **Validações** de CPF/CNPJ, número CNJ, datas
- **Orquestrador** - delega lógica de negócio ao Gateway

## Tópicos Suportados

### Autenticação (2)
- `cpj_login` - Obter token JWT
- `cpj_refresh_token` - Renovar token

### Publicações (2)
- `cpj_buscar_publicacoes_nao_vinculadas`
- `cpj_atualizar_publicacao`

### Pessoas (3)
- `cpj_consultar_pessoa`
- `cpj_cadastrar_pessoa`
- `cpj_atualizar_pessoa`

### Processos (3)
- `cpj_consultar_processos`
- `cpj_cadastrar_processo`
- `cpj_atualizar_processo`

### Pedidos (3)
- `cpj_consultar_pedidos`
- `cpj_cadastrar_pedido`
- `cpj_atualizar_pedido`

### Envolvidos (3)
- `cpj_consultar_envolvidos`
- `cpj_cadastrar_envolvido`
- `cpj_atualizar_envolvido`

### Tramitação (3)
- `cpj_cadastrar_andamento`
- `cpj_cadastrar_tarefa`
- `cpj_atualizar_tarefa`

### Documentos (3)
- `cpj_consultar_documentos`
- `cpj_baixar_documento`
- `cpj_cadastrar_documento`

## Configuração

Variáveis de ambiente obrigatórias:

```bash
CPJ_API_BASE_URL=https://ip:porta/api/v2
CPJ_API_USER=usuario_api
CPJ_API_PASSWORD=senha_api
GATEWAY_ENABLED=true
GATEWAY_URL=http://gateway:8000
```

## Uso

```bash
# Local
python main.py

# Docker
docker build -t cpj-api-worker .
docker run cpj-api-worker
```

## Estrutura

```
cpj_api_worker/
├── handlers/          # Handlers por módulo
├── validators/        # Validações (CPF, CNJ, etc)
├── main.py           # Entry point
├── worker.json       # Configuração
└── Dockerfile
```
