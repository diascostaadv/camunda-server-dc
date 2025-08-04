# Scripts de Teste - Movimentação Judicial Camunda VM

Este diretório contém scripts para testar o fluxo completo de processamento de movimentações judiciais no Camunda VM online (201.23.67.197:8080).

## 📁 Arquivos

### Processo BPMN
- **`processar_movimentacao.bpmn`** - Definição do processo BPMN para processamento de movimentações judiciais

### Scripts Python
- **`test_movimentacao_vm.py`** - Script principal para executar testes end-to-end
- **`deploy_processo.py`** - Utilitário para gerenciar deployments de processos BPMN
- **`monitor_execucao.py`** - Monitor de execução em tempo real

## 🚀 Uso Rápido

### 1. Executar Teste Completo
```bash
# Com dados reais do SOAP
python test_movimentacao_vm.py

# Com dados sintéticos
python test_movimentacao_vm.py --synthetic
```

### 2. Deploy do Processo
```bash
# Deploy básico
python deploy_processo.py deploy processar_movimentacao.bpmn

# Deploy com nome customizado
python deploy_processo.py deploy processar_movimentacao.bpmn --name "Movimentacao_v1.0"
```

### 3. Monitorar Execução
```bash
# Status atual
python monitor_execucao.py status --process processar_movimentacao_judicial

# Monitoramento contínuo (10 minutos)
python monitor_execucao.py monitor processar_movimentacao_judicial --duration 10
```

## 📋 Detalhamento dos Scripts

### test_movimentacao_vm.py

**Funcionalidade:** Executa testes end-to-end do fluxo de movimentação judicial.

**Características:**
- Integra com API SOAP para obter dados reais
- Fallback para dados sintéticos se SOAP falhar
- Deploy automático do processo BPMN
- Monitoramento de execução com timeout
- Relatório detalhado de resultados

**Uso:**
```bash
# Teste completo com dados reais
python test_movimentacao_vm.py

# Teste com dados sintéticos apenas
python test_movimentacao_vm.py --synthetic
```

**Saídas:**
- Console: Log detalhado da execução
- `test_report_YYYYMMDD_HHMMSS.json`: Relatório completo dos resultados

### deploy_processo.py

**Funcionalidade:** Gerenciamento completo de deployments no Camunda VM.

**Comandos disponíveis:**
```bash
# Testar conexão
python deploy_processo.py test

# Listar deployments existentes  
python deploy_processo.py list

# Listar definições de processo
python deploy_processo.py processes

# Deploy de processo
python deploy_processo.py deploy arquivo.bpmn [--name NOME]

# Remover deployment
python deploy_processo.py delete DEPLOYMENT_ID

# Listar recursos de deployment
python deploy_processo.py resources DEPLOYMENT_ID

# Exportar resumo
python deploy_processo.py export [--output arquivo.json]
```

**Opções de Deploy:**
- `--name`: Nome customizado para o deployment
- `--no-duplicate-filter`: Desabilita filtro de duplicatas
- `--no-changed-only`: Deploy todos os recursos mesmo sem alterações

### monitor_execucao.py

**Funcionalidade:** Monitoramento em tempo real de execuções no Camunda VM.

**Comandos disponíveis:**
```bash
# Status atual do sistema
python monitor_execucao.py status [--process CHAVE_PROCESSO]

# Monitoramento contínuo
python monitor_execucao.py monitor CHAVE_PROCESSO [--duration MINUTOS] [--interval SEGUNDOS]

# Observar tarefas externas
python monitor_execucao.py watch-tasks [--topic TOPICO] [--duration MINUTOS]

# Testar conexão
python monitor_execucao.py test
```

**Saídas:**
- Console: Logs em tempo real
- `monitor_PROCESSO_YYYYMMDD_HHMMSS.json`: Dados detalhados do monitoramento

## 🔧 Configuração

### Dependências
Os scripts dependem dos módulos do projeto:
- `intimation_api` (para dados SOAP)
- `requests` (para API REST do Camunda)

### URL do Camunda
Todos os scripts usam por padrão `http://201.23.67.197:8080`. Para alterar:
```bash
python script.py --url http://outro-servidor:8080 comando
```

### Credenciais SOAP
As credenciais estão hardcoded no `test_movimentacao_vm.py`:
- Usuário: `100049`
- Senha: `DcDpW@24`

## 📊 Processo BPMN

O processo `processar_movimentacao_judicial` implementa:

1. **Start Event** - Recebe dados da movimentação
2. **Service Task** - Processa publicação (tópico: `nova_publicacao`)
3. **Gateway** - Verifica resultado do processamento
4. **Log Tasks** - Registra sucesso ou erro (tópico: `log_processamento`)  
5. **End Events** - Finaliza com sucesso ou erro

### Variáveis de Entrada
```json
{
  "numero_processo": "string",
  "data_publicacao": "dd/mm/yyyy", 
  "texto_publicacao": "string",
  "fonte": "dw|manual|escavador",
  "tribunal": "string",
  "instancia": "string"
}
```

### Variáveis de Controle
- `status_processamento`: Controla fluxo do gateway
  - `"step_1_complete"` → Sucesso
  - Outros valores → Erro

## 🎯 Workflow de Teste

### Cenário Típico
1. **Deploy**: `python deploy_processo.py deploy processar_movimentacao.bpmn`
2. **Monitor**: `python monitor_execucao.py status --process processar_movimentacao_judicial`
3. **Teste**: `python test_movimentacao_vm.py`
4. **Acompanhar**: `python monitor_execucao.py monitor processar_movimentacao_judicial`

### Debugging
Para debugging de problemas:
```bash
# Ver status detalhado
python monitor_execucao.py status

# Monitorar tarefas externas
python monitor_execucao.py watch-tasks --topic nova_publicacao

# Ver logs do deployment
python deploy_processo.py list
python deploy_processo.py resources DEPLOYMENT_ID
```

## 📈 Interpretar Resultados

### Códigos de Status dos Testes
- `completed`: Teste executado com sucesso
- `failed`: Falha ao iniciar instância
- `timeout`: Processo não finalizou no tempo limite
- `exception`: Erro durante execução

### Métricas de Sucesso
- **Taxa de Sucesso**: > 90% dos testes completados
- **Tempo Médio**: < 30 segundos por teste
- **Instâncias Ativas**: 0 após finalização dos testes

### Problemas Comuns
1. **Timeout**: Workers não estão rodando ou Gateway inacessível
2. **Failed**: Processo BPMN mal deployado ou variáveis incorretas
3. **Exception**: Problemas de rede ou configuração

## 🔍 Logs e Relatórios

### Arquivos Gerados
- `test_report_*.json`: Relatório completo dos testes
- `monitor_*.json`: Dados de monitoramento
- `deployment_summary_*.json`: Resumo de deployments

### Estrutura do Relatório de Teste
```json
{
  "timestamp": "ISO datetime",
  "camunda_url": "string",
  "summary": {
    "total": 0,
    "completed": 0,
    "success_rate": 0.0,
    "avg_duration": 0.0
  },
  "detailed_results": [...]
}
```

## 🚨 Troubleshooting

### Erro de Conexão
```bash
# Verificar conectividade
python monitor_execucao.py test

# Verificar se VM está online
ping 201.23.67.197
```

### Processo Não Inicia
```bash
# Verificar deployments
python deploy_processo.py list
python deploy_processo.py processes

# Re-deployar se necessário
python deploy_processo.py deploy processar_movimentacao.bpmn --name "debug_deploy"
```

### Workers Não Respondem
1. Verificar se workers estão rodando
2. Verificar configuração `GATEWAY_ENABLED=true`
3. Verificar se Gateway está acessível
4. Verificar logs dos workers e gateway

### Dados SOAP Indisponíveis
```bash
# Usar dados sintéticos
python test_movimentacao_vm.py --synthetic
```

## 📝 Notas Importantes

- Scripts projetados para VM online (`201.23.67.197:8080`)
- Integração com data provider via `example_soap_to_json.py`
- Workers devem estar configurados para usar Gateway
- Processo BPMN segue padrão de orquestração (workers são orquestradores)
- Timeout padrão de 60 segundos por teste