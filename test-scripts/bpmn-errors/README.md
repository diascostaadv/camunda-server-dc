# Scripts de Teste - BPMN Errors

Scripts automatizados para testar os **BPMN Errors** implementados no `publicacao_unified` worker.

## 🚀 Quick Start

### 1. Subir o ambiente
```bash
cd ../..
make start
```

### 2. Executar todos os testes
```bash
cd test-scripts/bpmn-errors
chmod +x *.sh
./run_all_tests.sh
```

### 3. Monitorar logs em tempo real
```bash
./monitor_logs.sh
```

---

## 📁 Estrutura de Scripts

| Script | Descrição | Erro Testado |
|--------|-----------|--------------|
| `01_test_erro_validacao_nova_publicacao.sh` | Submete publicação sem campos obrigatórios | `ERRO_VALIDACAO_NOVA_PUBLICACAO` |
| `02_test_erro_validacao_busca.sh` | Busca com parâmetros inválidos | `ERRO_VALIDACAO_BUSCA` |
| `03_test_erro_validacao_classificacao.sh` | Classificação sem publicacao_id nem texto | `ERRO_VALIDACAO_CLASSIFICACAO` |
| `monitor_logs.sh` | Monitora logs do worker em tempo real | - |
| `run_all_tests.sh` | Executa todos os testes em sequência | - |

---

## 🧪 Executar Testes Individuais

### Teste 1: Validação Nova Publicação
```bash
./01_test_erro_validacao_nova_publicacao.sh
```

**O que testa:**
- Submete nova publicação sem `texto_publicacao`, `tribunal` e `instancia`
- Deve lançar `ERRO_VALIDACAO_NOVA_PUBLICACAO`
- Boundary event no BPMN deve capturar o erro

### Teste 2: Validação Busca
```bash
./02_test_erro_validacao_busca.sh
```

**O que testa:**
- Inicia busca com `limite_publicacoes=100` (máximo: 50)
- Inicia busca com `timeout_soap=500` (máximo: 300)
- Deve lançar `ERRO_VALIDACAO_BUSCA`

### Teste 3: Validação Classificação
```bash
./03_test_erro_validacao_classificacao.sh
```

**O que testa:**
- Tenta classificar sem fornecer `publicacao_id` ou `texto_publicacao`
- Deve lançar `ERRO_VALIDACAO_CLASSIFICACAO`

---

## 📊 Monitoramento

### Logs em Tempo Real
```bash
./monitor_logs.sh
```

Este script monitora os logs do worker com highlight de cores:
- 🔴 **Vermelho**: BPMN Errors
- 🟡 **Amarelo**: Erros de validação
- 🟢 **Verde**: Operações bem-sucedidas

### Buscar Erros Específicos
```bash
# Buscar todos os BPMN errors
docker logs publicacao-unified-worker | grep "BPMN Error"

# Buscar erro específico
docker logs publicacao-unified-worker | grep "ERRO_VALIDACAO_NOVA_PUBLICACAO"

# Últimos 50 logs
docker logs --tail 50 publicacao-unified-worker

# Logs de hoje
docker logs publicacao-unified-worker --since $(date -u +%Y-%m-%dT00:00:00Z)
```

---

## ✅ Verificação no Camunda Cockpit

Após executar os testes, verificar no Cockpit:

1. Acesse: http://localhost:8080/camunda/app/cockpit
2. Login: `demo` / `demo`
3. **Processes** → Selecione o processo testado
4. **Process Instances** → Clique na instância criada
5. Verificar:
   - ✅ **Incidents**: Deve estar vazio (sem incidents técnicos)
   - ✅ **Activity History**: Boundary error event deve estar ativado
   - ✅ **Variables**: Deve conter `errorMessage` com a mensagem do erro

---

## 🔧 Variáveis de Ambiente

```bash
# URL do Camunda (padrão: http://localhost:8080)
export CAMUNDA_URL=http://localhost:8080

# Nome do container do worker (padrão: publicacao-unified-worker)
export WORKER_CONTAINER=publicacao-unified-worker
```

---

## 🐛 Troubleshooting

### Erro: "Camunda não está acessível"
```bash
# Verificar se containers estão rodando
docker ps | grep camunda

# Reiniciar ambiente
cd ../..
make stop
make start
```

### Erro: "Worker não está rodando"
```bash
# Verificar status do worker
docker ps | grep publicacao-unified

# Ver logs de erro
docker logs publicacao-unified-worker

# Reconstruir worker
cd ../../camunda-workers-platform
make build-workers
docker-compose restart publicacao-unified-worker
```

### Boundary Event não captura o erro
```bash
# Verificar se o processo BPMN tem boundary events configurados
# Ver documentação em: ../../TESTE_BPMN_ERRORS.md

# Verificar código de erro no BPMN
# Deve ser EXATAMENTE igual ao código no worker (case-sensitive)
```

---

## 📚 Documentação Completa

Para documentação detalhada sobre:
- Como configurar boundary events no BPMN
- Todos os códigos de erro disponíveis
- Exemplos de processos BPMN de teste

Ver: [`../../TESTE_BPMN_ERRORS.md`](../../TESTE_BPMN_ERRORS.md)
