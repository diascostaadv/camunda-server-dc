# 🚀 Deploy DW LAW Worker - Guia Completo

**Data**: 2025-11-07
**Versão**: 1.0.0
**VM Produção**: 201.23.69.65 (ubuntu)
**Status**: ✅ Pronto para Deploy

---

## 📋 Pré-requisitos

- [x] Worker DW LAW desenvolvido e testado localmente
- [x] Credenciais DW LAW configuradas no Gateway
- [x] docker-compose.yml atualizado
- [x] env.gateway atualizado
- [x] SSH configurado para VM (~/.ssh/id_rsa ou ~/.ssh/azure_vm)
- [ ] Gateway rodando na VM (http://201.23.69.65:8080)
- [ ] Camunda acessível (http://201.23.67.197:8080)

---

## 🎯 Método de Deploy

Este projeto usa **Docker Compose** para produção (NÃO Docker Swarm).
Deploy via **sync de arquivos + build remoto** (sem Docker Registry).

---

## 📝 Passo a Passo do Deploy

### **PASSO 1: Sincronizar Código para VM**

#### Opção A: Via Makefile (Recomendado)

```bash
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Copiar arquivos para VM
make copy-files
```

**O que faz**:
- Copia `workers/` para VM
- Copia `docker-compose.yml` para VM
- Copia `env.gateway` para VM
- Copia arquivos comuns (`common/`)

#### Opção B: Via SCP Manual

```bash
# Conectar à VM de casa
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform

# Copiar worker DW LAW
scp -i ~/.ssh/id_rsa -r workers/dw_law_worker ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/workers/

# Copiar docker-compose.yml
scp -i ~/.ssh/id_rsa docker-compose.yml ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/

# Copiar env.gateway
scp -i ~/.ssh/id_rsa env.gateway ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/

# Copiar common (base classes)
scp -i ~/.ssh/id_rsa -r workers/common ubuntu@201.23.69.65:~/camunda-server-dc/camunda-workers-platform/workers/
```

---

### **PASSO 2: Conectar na VM**

```bash
# SSH na VM
ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65

# Navegar para diretório
cd ~/camunda-server-dc/camunda-workers-platform
```

---

### **PASSO 3: Build do Worker**

```bash
# Build apenas o worker DW LAW
docker compose build worker-dw-law

# OU para rebuild completo (sem cache)
docker compose build --no-cache worker-dw-law
```

**Tempo estimado**: 3-5 minutos

**Logs esperados**:
```
Building worker-dw-law
Step 1/10 : FROM python:3.11-slim
Step 2/10 : WORKDIR /app
...
Successfully built abc123def456
Successfully tagged camunda-workers-platform-worker-dw-law:latest
```

---

### **PASSO 4: Iniciar Worker**

```bash
# Iniciar apenas o worker DW LAW
docker compose up -d worker-dw-law

# OU reiniciar todos os workers (se preferir)
docker compose up -d
```

**Logs esperados**:
```
[+] Running 1/1
 ✔ Container worker-dw-law  Started  0.5s
```

---

### **PASSO 5: Verificar Status**

#### Verificar Container Rodando

```bash
docker ps | grep dw-law
```

**Saída esperada**:
```
worker-dw-law   Up 30 seconds   0.0.0.0:8010->8010/tcp
```

#### Verificar Logs

```bash
docker logs -f worker-dw-law --tail=100
```

**Logs esperados**:
```
DWLawWorker inicializado - Base URL: http://camunda:8080/engine-rest
✅ Worker configurado em modo orquestrador (Gateway)
🔍 DWLawWorker iniciado - aguardando tarefas nos tópicos:
  • INSERIR_PROCESSOS_DW_LAW - Inserir processos
  • EXCLUIR_PROCESSOS_DW_LAW - Excluir processos
  • CONSULTAR_PROCESSO_DW_LAW - Consultar processo
📊 Prometheus metrics server started on port 8010
🚀 Worker ready and waiting for external tasks...
```

#### Verificar Health Check

```bash
# Health endpoint
curl http://localhost:8010/health
```

**Resposta esperada**:
```json
{
  "status": "healthy",
  "worker": "dw-law-worker",
  "timestamp": "2025-11-07T..."
}
```

#### Verificar Métricas

```bash
curl http://localhost:8010/metrics | grep external_task
```

**Métricas esperadas**:
```
# HELP external_task_completed_total Total de tarefas completadas
# TYPE external_task_completed_total counter
external_task_completed_total{worker="dw-law-worker"} 0

# HELP external_task_failed_total Total de tarefas falhadas
# TYPE external_task_failed_total counter
external_task_failed_total{worker="dw-law-worker"} 0
```

---

### **PASSO 6: Verificar Registro no Camunda**

1. **Acessar Camunda Cockpit**:
   - URL: http://201.23.67.197:8080/camunda/app/cockpit
   - Login: demo / DiasCostaA!!2025

2. **Verificar External Tasks**:
   - Menu: Cockpit → External Tasks
   - Deve aparecer 3 tópicos:
     - ✅ INSERIR_PROCESSOS_DW_LAW
     - ✅ EXCLUIR_PROCESSOS_DW_LAW
     - ✅ CONSULTAR_PROCESSO_DW_LAW

3. **Verificar Worker ID**:
   - Worker ID: `dw-law-worker`
   - Lock Duration: 120000ms (2 minutos)
   - Max Tasks: 3

---

### **PASSO 7: Configurar Firewall (Se Necessário)**

Se a porta 8010 não estiver aberta:

```bash
# Adicionar regra UFW
sudo ufw allow 8010/tcp
sudo ufw reload

# Verificar
sudo ufw status | grep 8010
```

**Saída esperada**:
```
8010/tcp                   ALLOW       Anywhere
```

---

## 🧪 Testes de Validação

### Teste 1: Health Check Externo

```bash
# Da sua máquina local
curl http://201.23.69.65:8010/health
```

### Teste 2: Métricas Prometheus

```bash
# Da sua máquina local
curl http://201.23.69.65:8010/metrics
```

### Teste 3: Inserir Processo via Gateway

```bash
curl -X POST http://201.23.69.65:8000/dw-law/inserir-processos \
  -H 'Content-Type: application/json' \
  -d '{
    "chave_projeto": "diascostacitacaoconsultaunica",
    "processos": [
      {
        "numero_processo": "0012205-60.2015.5.15.0077",
        "other_info_client1": "TESTE_DEPLOY_PRODUCAO"
      }
    ]
  }'
```

### Teste 4: Criar Processo BPMN de Teste

1. Criar processo no Camunda Modeler
2. Adicionar Service Task com tópico `INSERIR_PROCESSOS_DW_LAW`
3. Fazer deploy do processo
4. Iniciar instância
5. Verificar logs do worker

---

## 📊 Monitoramento

### Logs em Tempo Real

```bash
# SSH na VM
ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65

# Logs do worker
docker logs -f worker-dw-law --tail=100

# Filtrar por tipo de log
docker logs worker-dw-law 2>&1 | grep "ERROR"
docker logs worker-dw-law 2>&1 | grep "WARNING"
docker logs worker-dw-law 2>&1 | grep "✅"
```

### Prometheus + Grafana

1. **Prometheus**:
   - URL: http://201.23.69.65:9090
   - Query: `external_task_completed_total{worker="dw-law-worker"}`

2. **Grafana**:
   - URL: http://201.23.69.65:3001
   - Login: admin/admin
   - Dashboard: Workers Performance

---

## 🔄 Operações Comuns

### Escalar Worker (Aumentar Réplicas)

```bash
# Editar env.gateway
nano env.gateway
# Alterar: WORKER_DW_LAW_REPLICAS=2

# Aplicar mudança
docker compose up -d --scale worker-dw-law=2

# Verificar
docker ps | grep dw-law
```

### Atualizar Worker (Após Mudanças no Código)

```bash
# 1. Na máquina local: Sync arquivos
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-workers-platform
make copy-files

# 2. Na VM: Rebuild e restart
ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65
cd ~/camunda-server-dc/camunda-workers-platform
docker compose build --no-cache worker-dw-law
docker compose up -d worker-dw-law

# 3. Verificar logs
docker logs -f worker-dw-law --tail=50
```

### Reiniciar Worker

```bash
docker compose restart worker-dw-law
```

### Parar Worker

```bash
docker compose stop worker-dw-law
```

### Remover Worker

```bash
# Parar e remover container
docker compose down worker-dw-law

# Remover imagem
docker rmi camunda-workers-platform-worker-dw-law:latest
```

### Ver Status de Todos os Workers

```bash
docker compose ps
```

---

## 🆘 Troubleshooting

### Worker não inicia

```bash
# Verificar logs de erro
docker logs worker-dw-law 2>&1 | grep -i error

# Verificar se todas as variáveis de ambiente estão definidas
docker exec worker-dw-law env | grep -E "(CAMUNDA|GATEWAY|DW_LAW)"

# Verificar se Gateway está acessível
docker exec worker-dw-law curl -f http://201.23.69.65:8080/health
```

### Worker não conecta ao Camunda

```bash
# Testar conectividade
docker exec worker-dw-law curl http://201.23.67.197:8080/engine-rest/version

# Verificar variáveis
docker exec worker-dw-law env | grep CAMUNDA
```

### Worker não se registra nos tópicos

```bash
# Verificar logs de inicialização
docker logs worker-dw-law --tail=200 | grep -i "topic\|subscribe"

# Verificar se max_tasks não está zerado
docker exec worker-dw-law env | grep MAX_TASKS
```

### Porta 8010 não acessível

```bash
# Verificar se porta está exposta
docker port worker-dw-law

# Verificar firewall
sudo ufw status | grep 8010

# Testar localmente na VM
curl http://localhost:8010/health
```

---

## 🔙 Rollback

Se precisar reverter o deploy:

```bash
# 1. Parar worker
docker compose stop worker-dw-law

# 2. Remover container e imagem
docker compose rm -f worker-dw-law
docker rmi camunda-workers-platform-worker-dw-law:latest

# 3. Restaurar docker-compose.yml anterior
git checkout HEAD -- docker-compose.yml env.gateway

# 4. Reiniciar outros serviços
docker compose up -d
```

---

## ✅ Checklist de Deploy

- [ ] **Pré-Deploy**
  - [ ] Código sincronizado para VM
  - [ ] docker-compose.yml atualizado
  - [ ] env.gateway atualizado
  - [ ] SSH funcionando

- [ ] **Build**
  - [ ] Build concluído sem erros
  - [ ] Imagem criada

- [ ] **Deploy**
  - [ ] Container iniciado
  - [ ] Container rodando (docker ps)
  - [ ] Logs sem erros críticos

- [ ] **Verificação**
  - [ ] Health check OK
  - [ ] Métricas expostas
  - [ ] Tópicos registrados no Camunda
  - [ ] Porta 8010 acessível

- [ ] **Testes**
  - [ ] Teste via Gateway OK
  - [ ] Teste via Camunda OK
  - [ ] Callbacks funcionando

- [ ] **Monitoramento**
  - [ ] Prometheus coletando métricas
  - [ ] Grafana exibindo dashboard
  - [ ] Logs estruturados

---

## 📝 Informações Técnicas

### Configuração do Worker

```yaml
Worker ID: dw-law-worker
Porta: 8010
Max Tasks: 3
Lock Duration: 120000ms (2 min)
Gateway: http://201.23.69.65:8080
Camunda: http://201.23.67.197:8080/engine-rest
```

### Tópicos Camunda

```
1. INSERIR_PROCESSOS_DW_LAW
   - Insere lista de processos no DW LAW
   - Timeout: 90s

2. EXCLUIR_PROCESSOS_DW_LAW
   - Exclui processos do monitoramento
   - Timeout: 90s

3. CONSULTAR_PROCESSO_DW_LAW
   - Consulta dados completos por chave
   - Timeout: 120s
```

### Variáveis de Ambiente

```bash
# Worker
WORKER_ID=dw-law-worker
MAX_TASKS=3
LOCK_DURATION=120000
GATEWAY_ENABLED=true
METRICS_PORT=8010

# DW LAW API (via Gateway)
DW_LAW_BASE_URL=https://web-eprotocol-integration-cons-qa.azurewebsites.net
DW_LAW_USUARIO=integ_dias_cons@dwlaw.com.br
DW_LAW_SENHA=DC@Dwlaw2025
DW_LAW_CHAVE_PROJETO=diascostacitacaoconsultaunica
```

---

## 📞 Suporte

**Logs**: `docker logs worker-dw-law`
**Métricas**: http://201.23.69.65:8010/metrics
**Health**: http://201.23.69.65:8010/health
**Documentação**: `workers/dw_law_worker/README.md`

---

**✅ Worker DW LAW pronto para produção!**

**Data de Deploy**: ___________
**Responsável**: ___________
**Status**: [ ] Sucesso [ ] Rollback
