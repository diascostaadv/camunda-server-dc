# Worker Unificado de Publicações

Este worker unificado combina as funcionalidades dos workers `nova_publicacao` e `buscar_publicacoes` em um único container Docker, oferecendo uma solução mais eficiente e plug-and-play para o processamento de publicações judiciais.

## 🎯 Funcionalidades

### Tópicos Suportados

1. **`nova_publicacao`** - Processamento individual de movimentações judiciais

   - Validação de campos obrigatórios
   - Persistência e higienização de dados
   - Integração com MongoDB
   - Detecção de duplicatas via hash

2. **`BuscarPublicacoes`** - Busca automatizada de publicações
   - Busca via SOAP API
   - Disparo de processos individuais no Camunda
   - Processamento em lote
   - Monitoramento de status

## 🏗️ Arquitetura

### Padrão Orquestrador

- **Worker**: Validação básica e orquestração
- **Gateway**: Toda lógica de negócio centralizada
- **Camunda**: Gerenciamento de workflow

### Fluxo de Processamento

```
Camunda → Worker Unificado → Gateway → SOAP API / MongoDB
     ↑                                      ↓
     └─── Resultado ←──────────────────────┘
```

## 🚀 Como Usar

### 1. Build e Deploy com Docker

```bash
# Construir a imagem
docker build -t publicacao-unified-worker .

# Executar com docker-compose
docker-compose up -d

# Verificar logs
docker-compose logs -f publicacao-unified-worker
```

### 2. Configuração via Variáveis de Ambiente

```bash
# Gateway
GATEWAY_ENABLED=true
GATEWAY_URL=http://camunda-worker-api-gateway:8001

# Camunda
CAMUNDA_URL=http://camunda:8080/engine-rest
CAMUNDA_USERNAME=demo
CAMUNDA_PASSWORD=DiasCosta@!!2025

# Worker
MAX_TASKS=2
LOCK_DURATION=60000
```

### 3. Monitoramento

- **Metrics**: `http://localhost:8002/metrics` (Prometheus)
- **Health Check**: `http://localhost:8002/health`
- **Logs**: Via `docker-compose logs`

## 📋 Exemplos de Uso

### Nova Publicação Individual

```json
{
  "numero_processo": "1234567-89.2023.8.13.0001",
  "data_publicacao": "15/12/2023",
  "texto_publicacao": "Citação do réu...",
  "fonte": "dw",
  "tribunal": "tjmg",
  "instancia": "1"
}
```

### Busca Automatizada

```json
{
  "cod_grupo": 5,
  "limite_publicacoes": 50,
  "timeout_soap": 90,
  "apenas_nao_exportadas": true
}
```

### Busca por Período

```json
{
  "cod_grupo": 0,
  "data_inicial": "2023-12-01",
  "data_final": "2023-12-15",
  "limite_publicacoes": 100,
  "timeout_soap": 120
}
```

## 🔧 Desenvolvimento

### Estrutura do Projeto

```
publicacao_unified/
├── main.py              # Worker unificado
├── Dockerfile           # Imagem Docker
├── docker-compose.yml   # Orquestração local
├── requirements.txt     # Dependências Python
├── worker.json         # Configuração do worker
└── README.md           # Documentação
```

### Testando Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
export GATEWAY_ENABLED=true
export CAMUNDA_URL=http://localhost:8080/engine-rest

# Executar worker
python main.py
```

## 📊 Métricas e Monitoring

O worker expõe métricas Prometheus em `/metrics`:

- `camunda_tasks_total{topic, status}` - Total de tarefas processadas
- `camunda_task_duration_seconds{topic}` - Duração do processamento
- `camunda_active_tasks{topic}` - Tarefas ativas
- `gateway_tasks_total{topic, status}` - Comunicação com Gateway

## 🔄 Vantagens da Unificação

### ✅ Benefícios

1. **Simplicidade de Deploy**: Um único container para ambos os fluxos
2. **Redução de Recursos**: Menor overhead de infraestrutura
3. **Gestão Centralizada**: Configuração e monitoring unificados
4. **Escalabilidade**: Um worker pode processar múltiplos tipos de tarefa
5. **Manutenção**: Código centralizado e reutilização de componentes

### 🔧 Flexibilidade

- **Multi-Topic**: Suporte nativo a múltiplos tópicos
- **Configurável**: Habilitação/desabilitação via variáveis
- **Compatível**: Mantém compatibilidade com workers separados
- **Gateway-Ready**: Integração transparente com Worker API Gateway

## 🚨 Troubleshooting

### Problemas Comuns

1. **Gateway Indisponível**

   ```
   ERROR: Gateway communication error
   → Verificar GATEWAY_URL e conectividade
   ```

2. **Camunda Connection Failed**

   ```
   ERROR: Failed to connect to Camunda
   → Verificar CAMUNDA_URL e credenciais
   ```

3. **Task Validation Error**
   ```
   ERROR: Required field missing
   → Verificar payload da tarefa no Camunda
   ```

### Logs Importantes

```bash
# Ver logs do worker
docker-compose logs publicacao-unified-worker

# Filtrar por tópico
docker-compose logs | grep "nova_publicacao"
docker-compose logs | grep "BuscarPublicacoes"
```

## 📈 Performance

### Configurações Recomendadas

- **Produção**: `MAX_TASKS=2`, `LOCK_DURATION=60000`
- **Desenvolvimento**: `MAX_TASKS=1`, `LOG_LEVEL=DEBUG`
- **Alta Carga**: Múltiplas réplicas do worker

### Limites de Recursos

- **Memória**: 512Mi (limite), 256Mi (reserva)
- **CPU**: 0.5 cores (limite), 0.25 cores (reserva)

---

**Desenvolvido por**: Dias Costa  
**Versão**: 1.0.0  
**Data**: Dezembro 2023
