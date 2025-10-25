# Testes CPJ - Worker API Gateway

Este diretório contém testes isolados para a funcionalidade de busca de dados no CPJ (Sistema de Controle de Processos Judiciais).

## 📁 Estrutura de Testes

```
tests/
├── __init__.py                  # Inicialização do pacote de testes
├── conftest.py                  # Fixtures compartilhadas (pytest)
├── test_cpj_service.py          # Testes unitários do CPJService
├── test_cpj_endpoint.py         # Testes de integração do endpoint REST
└── README.md                    # Esta documentação
```

## 🎯 Cobertura de Testes

### `test_cpj_service.py` - Testes Unitários (41 testes)

Testa o serviço `CPJService` ([app/services/cpj_service.py](../services/cpj_service.py)) isoladamente usando mocks:

#### Autenticação
- ✅ Login bem-sucedido armazena token
- ✅ Login calcula expiração corretamente
- ✅ Login trata erros HTTP (401, 500)
- ✅ Login trata timeout
- ✅ Login trata erros de conexão
- ✅ Login trata erros genéricos

#### Gerenciamento de Token
- ✅ Autenticação automática quando não tem token
- ✅ Renovação automática quando token expira
- ✅ Reutilização de token válido (não autentica novamente)
- ✅ `is_authenticated()` valida token corretamente
- ✅ `get_token_info()` retorna informações do token

#### Busca de Processos
- ✅ Busca retorna múltiplos processos
- ✅ Busca retorna único processo
- ✅ Busca retorna lista vazia quando não encontra
- ✅ Busca usa token em cache
- ✅ Busca trata timeout
- ✅ Busca trata erros HTTP
- ✅ Busca trata erros de conexão
- ✅ Busca trata erros genéricos

#### Fluxos Completos
- ✅ Primeira requisição autentica + busca
- ✅ Segunda requisição reutiliza token
- ✅ Renovação automática em requisições subsequentes

### `test_cpj_endpoint.py` - Testes de Integração (26 testes)

Testa o endpoint REST `/publicacoes/verificar-processo-cnj` ([app/routers/publicacoes.py](../routers/publicacoes.py:831-894)):

#### Requisições Válidas
- ✅ Request com `numero_cnj` retorna processos
- ✅ Request com `numero_processo` (campo alternativo)
- ✅ Request com formato worker (`variables.numero_cnj`)
- ✅ Processo real `0000036-58.2019.8.16.0033`
- ✅ Resposta com único processo
- ✅ Resposta sem processos encontrados

#### Validação de Estrutura
- ✅ Estrutura completa da resposta
- ✅ Timestamp em formato ISO
- ✅ Preservação do formato do numero_cnj
- ✅ Logging de detalhes do request

#### Casos Extremos (Edge Cases)
- ✅ Numero CNJ com espaços extras
- ✅ Valor especial "não informado"
- ✅ Request com campos extras (ignora)
- ✅ Precedência de campos múltiplos
- ✅ Precedência variables vs campo direto

#### Tratamento de Erros
- ✅ Request sem numero_cnj retorna 400
- ✅ Request vazio retorna 400
- ✅ Numero CNJ null retorna 400
- ✅ Numero CNJ vazio retorna 400
- ✅ Timeout do CPJService retorna 500
- ✅ Erro de autenticação retorna 500
- ✅ Erro de conexão retorna 500
- ✅ Exceções genéricas retornam 500

## 🚀 Como Executar os Testes

> **⚠️ IMPORTANTE para macOS/Homebrew**: Este projeto usa ambiente virtual isolado para evitar erros de "externally-managed-environment".

### 1. Configurar Ambiente (Primeira Vez)

```bash
# Navegue até o diretório de testes
cd camunda-worker-api-gateway/app/tests

# Execute o script de setup (cria virtualenv e instala dependências)
./setup_test_env.sh
```

O script irá:
- ✅ Criar ambiente virtual em `.venv/`
- ✅ Instalar pytest e todas as dependências
- ✅ Validar a instalação
- ✅ Exibir instruções de uso

**Você só precisa fazer isso UMA VEZ!** O ambiente virtual será reutilizado automaticamente.

### 2. Executar Testes (Sempre)

```bash
# O script ativa automaticamente o virtualenv!

# Executar TODOS os testes CPJ
./run_cpj_tests.sh all

# Testes unitários apenas
./run_cpj_tests.sh unit

# Testes de integração apenas
./run_cpj_tests.sh integration

# Execução rápida (sem verbose)
./run_cpj_tests.sh quick
```

### 3. Executar com Cobertura

```bash
# Relatório de cobertura completo
./run_cpj_tests.sh coverage

# Abre relatório HTML gerado
open tests/htmlcov/index.html  # macOS
xdg-open tests/htmlcov/index.html  # Linux
```

### 4. Modo Debug

```bash
# Modo debug com output completo
./run_cpj_tests.sh debug

# Teste específico
./run_cpj_tests.sh specific TestCPJServiceLogin::test_login_success
```

### 5. Uso Avançado (pytest direto)

Se preferir usar pytest diretamente (virtualenv deve estar ativo):

```bash
# Ativa virtualenv manualmente
source .venv/bin/activate

# Executar testes
cd ..  # Volta para app/
pytest tests/test_cpj_service.py -v
pytest tests/test_cpj_endpoint.py -v
pytest tests/test_cpj* -v

# Desativa quando terminar
deactivate
```

### 6. Recriar Ambiente

Se houver problemas com o ambiente virtual:

```bash
# Limpa e recria o ambiente
./setup_test_env.sh --clean
```

## 📊 Fixtures Disponíveis (conftest.py)

### Configuração
- `cpj_config` - Configurações mock do CPJ
- `mock_settings` - Mock de Settings completo

### Respostas HTTP
- `mock_cpj_auth_success` - Autenticação bem-sucedida
- `mock_cpj_auth_error` - Erro de autenticação (401)
- `mock_cpj_processo_encontrado` - 2 processos encontrados
- `mock_cpj_processo_single` - 1 processo encontrado
- `mock_cpj_processo_nao_encontrado` - Nenhum processo (lista vazia)

### Payloads de Request
- `cpj_request_valid` - Request válido com numero_cnj
- `cpj_request_with_variables` - Request formato worker
- `cpj_request_alternative_field` - Request com numero_processo
- `cpj_request_invalid_missing_numero` - Request inválido

### Erros
- `mock_timeout_error` - Erro de timeout
- `mock_connection_error` - Erro de conexão
- `mock_http_error` - Erro HTTP genérico

### Helpers
- `create_response` - Factory para criar mock de Response HTTP

## 🧪 Exemplo de Uso das Fixtures

```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_meu_teste(mock_cpj_processo_encontrado, create_response):
    """Exemplo de teste usando fixtures"""
    from services.cpj_service import CPJService

    service = CPJService()
    mock_response = create_response(200, mock_cpj_processo_encontrado)

    with patch("requests.post", return_value=mock_response):
        resultado = await service.buscar_processo_por_numero("0000036-58.2019.8.16.0033")

    assert len(resultado) == 2
    assert resultado[0]["tribunal"] == "TJPR"
```

## 📝 Processo Real Testado

Os testes utilizam o processo real fornecido nos logs:

- **Número CNJ**: `0000036-58.2019.8.16.0033`
- **Tribunal**: TJPR (Tribunal de Justiça do Paraná)
- **Resultado esperado**: 2 processos encontrados

Este processo é mockado nos fixtures para simular respostas reais da API CPJ.

## 🔍 Logs de Teste

Durante a execução, os testes validam que os logs são gerados corretamente:

```
✅ Autenticação CPJ bem-sucedida - Token válido até 2024-10-24 22:55:53
✅ Busca CPJ concluída - 2 processos encontrados
🔍 Verificando processo 0000036-58.2019.8.16.0033 no CPJ...
```

## 📚 Referências

- **CPJService**: [app/services/cpj_service.py](../services/cpj_service.py)
- **Endpoint REST**: [app/routers/publicacoes.py](../routers/publicacoes.py:831-894)
- **Configurações**: [app/core/config.py](../core/config.py:72-77)

## 🎓 Boas Práticas Implementadas

1. **Isolamento**: Testes unitários não fazem chamadas HTTP reais (100% mockado)
2. **Cobertura**: 67 testes cobrindo todos os cenários principais
3. **Fixtures**: Dados de teste reutilizáveis e realistas
4. **Async/Await**: Suporte completo a testes assíncronos
5. **Edge Cases**: Validação de casos extremos e erros
6. **Logging**: Verificação de logs gerados durante execução
7. **Documentação**: Testes auto-documentados com docstrings descritivas

## ⚠️ Notas Importantes

- **Não faz chamadas reais à API CPJ**: Todos os testes usam mocks
- **Independentes**: Cada teste pode rodar isoladamente
- **Rápidos**: Bateria completa executa em segundos (sem I/O de rede)
- **Determinísticos**: Resultados consistentes (fixtures fixas)

## 🐛 Troubleshooting

### Erro: "No module named pytest"
```bash
pip install pytest pytest-asyncio
```

### Erro: "No module named requests-mock"
```bash
pip install requests-mock
```

### Erro de import do app
```bash
# Execute a partir do diretório correto
cd camunda-worker-api-gateway/app
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/test_cpj* -v
```

### Ver fixtures disponíveis
```bash
pytest --fixtures tests/conftest.py
```
