# Worker de Publicações/Intimações

Este módulo integra com o WebService de Intimações da DWRPA, convertendo respostas SOAP para JSON com retry automático e tratamento robusto de timeouts.

## Funcionalidades

- ✅ **Conversão SOAP para JSON** completa e automática
- ✅ **Retry automático** com backoff exponencial 
- ✅ **Tratamento de timeout** configurável
- ✅ **Parse XML com namespaces** correto
- ✅ **Logging estruturado** para monitoramento
- ✅ **Integração com Camunda** Worker
- ✅ **Dados reais validados** com 2889+ publicações

## Uso Básico

```python
from publicacao_worker import IntimationAPIClient, Publicacao

# Cliente básico
client = IntimationAPIClient(
    usuario="100049",
    senha="DcDpW@24"
)

# Buscar publicações não exportadas
publicacoes = client.get_publicacoes_nao_exportadas()

# Converter para JSON
json_data = client.publicacoes_to_json(publicacoes)

# Salvar arquivo
with open('intimacoes.json', 'w', encoding='utf-8') as f:
    f.write(json_data)
```

## Configuração Avançada

```python
# Cliente com configurações customizadas
client = IntimationAPIClient(
    usuario="seu_usuario",
    senha="sua_senha",
    timeout=120,        # Timeout em segundos
    max_retries=5,      # Tentativas de retry
    base_url="url_customizada"  # URL alternativa
)

# Busca com timeout específico para período grande
publicacoes = client.get_publicacoes_periodo_safe(
    data_inicial="2025-01-01",
    data_final="2025-12-31",
    timeout_override=180  # 3 minutos para períodos grandes
)
```

## Integração com Camunda

O worker suporta três operações via variáveis de processo:

### 1. Importação Completa
```json
{
    "operation": "import_all",
    "cod_grupo": 0
}
```

### 2. Importação por Período
```json
{
    "operation": "import_period", 
    "data_inicial": "2025-01-01",
    "data_final": "2025-01-31",
    "cod_grupo": 0
}
```

### 3. Estatísticas
```json
{
    "operation": "get_statistics",
    "data": "2025-01-15",
    "cod_grupo": 0
}
```

## Variáveis de Ambiente

Para produção, configure as variáveis:

```bash
export INTIMATION_USER="seu_usuario_producao"
export INTIMATION_PASSWORD="sua_senha_producao"
```

## Estrutura de Dados

### Publicacao
```python
@dataclass
class Publicacao:
    cod_publicacao: int         # Código único da intimação
    numero_processo: str        # Número do processo
    uf_publicacao: str         # Estado (MG, SP, RJ, etc.)
    descricao_diario: str      # Tribunal (TJMG, TJSP, etc.)
    vara_descricao: str        # Vara específica
    data_publicacao: str       # Data da publicação
    processo_publicacao: str   # Conteúdo completo da intimação
    nome_vinculo: str          # Nome do advogado
    oab_numero: int           # Número da OAB
    oab_estado: str           # Estado da OAB
    anexo: str                # Link para PDF
    # ... demais campos
```

### Conversão JSON
```python
# Objeto individual
publicacao.to_json()          # String JSON formatada
publicacao.to_dict()          # Dicionário Python

# Lista de publicações  
client.publicacoes_to_json(lista)   # JSON da lista completa
client.publicacoes_to_dict(lista)   # Lista de dicionários
```

## Tratamento de Erros

O cliente possui tratamento robusto de erros:

```python
try:
    publicacoes = client.get_publicacoes_nao_exportadas()
except requests.exceptions.Timeout:
    print("Timeout após todas as tentativas")
except requests.exceptions.ConnectionError:
    print("Erro de conectividade")
except Exception as e:
    print(f"Erro inesperado: {e}")
```

## Logging

Configure logging para monitorar operações:

```python
import logging

# Logging básico
logging.basicConfig(level=logging.INFO)

# Logging avançado
logger = logging.getLogger('intimation_client')
logger.setLevel(logging.DEBUG)

# Verá mensagens como:
# INFO: Tentativa 2/4 para getPublicacoes. Aguardando 2s...
# INFO: Parsed 156 publicações do XML
# INFO: Encontradas 156 publicações no período 2025-01-01 - 2025-01-31
```

## Períodos com Dados Confirmados

Para testes, use períodos que sabemos ter dados:

```python
# Maio 2025 tem 2889+ publicações confirmadas
publicacoes = client.get_publicacoes_periodo_safe(
    "2025-05-01", "2025-05-31"
)

# Dia específico para testes rápidos (12 publicações)
publicacoes = client.get_publicacoes_periodo_safe(
    "2025-05-01", "2025-05-01"  
)
```

## Rotina de Importação Automática

```python
# Importa todas as publicações não exportadas
# Processa em lotes de 700, marca como exportadas automaticamente
todas_publicacoes = client.importar_publicacoes_rotina(
    cod_grupo=0,
    max_iteracoes=100
)

print(f"Importadas {len(todas_publicacoes)} publicações")
```

## Performance e Limites

- **Máximo por requisição**: 700 publicações
- **Timeout padrão**: 60 segundos
- **Retry automático**: 3 tentativas com backoff exponencial
- **Formato de data**: yyyy-mm-dd
- **Encoding**: UTF-8 com caracteres especiais preservados

## Exemplos Completos

### Exemplo 1: Busca Simples
```python
from publicacao_worker import IntimationAPIClient

client = IntimationAPIClient("100049", "DcDpW@24")

# Testa conexão
if client.test_connection():
    # Busca publicações
    publicacoes = client.get_publicacoes_nao_exportadas()
    
    # Converte para JSON
    json_data = client.publicacoes_to_json(publicacoes)
    
    # Salva arquivo
    with open('intimacoes.json', 'w', encoding='utf-8') as f:
        f.write(json_data)
        
    print(f"✅ {len(publicacoes)} publicações salvas")
```

### Exemplo 2: Período Específico
```python
# Busca período com timeout customizado
publicacoes = client.get_publicacoes_periodo_safe(
    data_inicial="2025-05-01",
    data_final="2025-05-31", 
    cod_grupo=0,
    timeout_override=180  # 3 minutos
)

# Processa cada publicação
for pub in publicacoes:
    print(f"Processo: {pub.numero_processo}")
    print(f"Tribunal: {pub.descricao_diario}")
    print(f"Data: {pub.data_publicacao}")
    print("---")
```

### Exemplo 3: Integração Completa
```python
import logging
from publicacao_worker import IntimationAPIClient

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Cliente robusto
client = IntimationAPIClient(
    usuario="100049",
    senha="DcDpW@24", 
    timeout=90,
    max_retries=3
)

try:
    # Rotina completa de importação
    publicacoes = client.importar_publicacoes_rotina()
    
    # Estatísticas
    print(f"📊 Total importado: {len(publicacoes)}")
    
    # Análise por tribunal
    tribunais = {}
    for pub in publicacoes:
        tribunal = pub.descricao_diario
        tribunais[tribunal] = tribunais.get(tribunal, 0) + 1
    
    print("📈 Por tribunal:")
    for tribunal, count in sorted(tribunais.items()):
        print(f"  {tribunal}: {count}")
        
    # Salva resultado
    json_data = client.publicacoes_to_json(publicacoes)
    with open('importacao_completa.json', 'w', encoding='utf-8') as f:
        f.write(json_data)
        
    print("💾 Dados salvos em importacao_completa.json")
    
except Exception as e:
    print(f"❌ Erro: {e}")
```

## Troubleshooting

### Timeout Persistente
- Aumente o `timeout` para 120-180s
- Use `timeout_override` para períodos grandes
- Reduza o intervalo de datas

### Erro de Parse XML
- Verifique se o XML de resposta está válido
- Ative logging DEBUG para ver detalhes
- Confirme credenciais corretas

### Nenhum Dado Retornado
- Use período confirmado: maio 2025
- Verifique `cod_grupo` correto
- Teste com `get_publicacoes_nao_exportadas()`

## Arquivos do Módulo

- `intimation_client.py` - Cliente principal
- `worker.py` - Worker do Camunda
- `config_example.py` - Exemplo de configuração
- `README.md` - Esta documentação
- `*.http` - Arquivos de teste HTTP

## Requisitos

```txt
requests>=2.31.0
xml (built-in)
json (built-in)
logging (built-in)
```

## Créditos

Desenvolvido para integração com o WebService de Intimações da DWRPA.
Suporte completo a SOAP→JSON com tratamento robusto de erros e retry automático.