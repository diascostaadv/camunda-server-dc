# Requisitos e Premissas de Deploy - Camunda Platform

Este documento define as premissas e requisitos para deploy do Camunda Platform, baseado nos problemas encontrados e suas soluções.

## 🚨 **Problemas Conhecidos e Soluções**

### 1. **Compatibilidade de Versão Docker Compose**

**❌ Problema:** Versão 3.9 não suportada pelo Docker Compose 1.26.2

```
Version in "./docker-compose.yml" is unsupported
```

**✅ Solução:** Sempre usar `version: "3.3"` nos arquivos docker-compose.yml

**📋 Checklist:**

- [ ] Verificar versão do Docker Compose: `docker-compose --version`
- [ ] Usar `version: "3.3"` em todos os docker-compose.yml
- [ ] Testar localmente antes do deploy remoto

### 2. **Configuração de Banco de Dados no Docker Swarm**

**❌ Problema:** URL de banco incorreta no Docker Swarm

```
Driver org.postgresql.Driver claims to not accept jdbcUrl, jdbc:h2:./camunda-h2-default/process-engine
```

**✅ Solução:** Usar nome completo do serviço no Docker Swarm

**📋 Configuração Correta:**

```yaml
# Para Docker Compose local
DB_URL: jdbc:postgresql://db:5432/camunda

# Para Docker Swarm
DB_URL: jdbc:postgresql://camunda-platform-v2_db:5432/camunda
```

**📋 Checklist:**

- [ ] Verificar se está usando Docker Compose ou Docker Swarm
- [ ] Ajustar URL do banco conforme o modo de deploy
- [ ] Testar conectividade do banco antes do deploy

### 3. **Propriedades Incompatíveis do Docker Compose**

**❌ Problema:** Propriedades não suportadas

```
Additional property start_period is not allowed
```

**✅ Solução:** Remover propriedades incompatíveis

**📋 Propriedades a Evitar:**

- `start_period` em healthcheck
- `profiles` em serviços
- `depends_on` com `condition` (usar apenas lista simples)

**📋 Checklist:**

- [ ] Remover `start_period` de healthchecks
- [ ] Usar `depends_on: [service]` em vez de `depends_on: service: condition:`
- [ ] Testar sintaxe com `docker-compose config`

### 4. **Conflitos de Rede e Stack**

**❌ Problema:** Rede já existente

```
failed to create network camunda-platform_backend: Error response from daemon: network with name camunda-platform_backend already exists
```

**✅ Solução:** Usar nomes únicos para stacks

**📋 Estratégia:**

- Usar timestamp ou versão no nome do stack
- Limpar recursos antigos antes do deploy
- Verificar redes existentes

**📋 Checklist:**

- [ ] Verificar redes existentes: `docker network ls`
- [ ] Remover stack antigo: `docker stack rm <stack-name>`
- [ ] Usar nome único para novo stack

## 🔧 **Requisitos de Sistema**

### **Docker e Docker Compose**

- Docker Compose versão 1.26.2 ou superior
- Docker versão 20.10 ou superior
- Docker Swarm habilitado para deploy em produção

### **Recursos Mínimos**

- RAM: 4GB mínimo, 8GB recomendado
- CPU: 2 cores mínimo, 4 cores recomendado
- Disco: 20GB livre para imagens e volumes

### **Rede**

- Porta 8080 disponível para Camunda
- Porta 5432 disponível para PostgreSQL
- Porta 9090 disponível para Prometheus
- Porta 3001 disponível para Grafana

## 📋 **Checklist de Deploy**

### **Antes do Deploy**

- [ ] Verificar versão do Docker Compose
- [ ] Validar sintaxe: `docker-compose config`
- [ ] Verificar variáveis de ambiente
- [ ] Limpar recursos antigos
- [ ] Verificar conectividade de rede

### **Durante o Deploy**

- [ ] Monitorar logs em tempo real
- [ ] Verificar status dos containers
- [ ] Testar conectividade dos serviços
- [ ] Validar health checks

### **Após o Deploy**

- [ ] Testar acesso ao Camunda
- [ ] Verificar logs de erro
- [ ] Validar conectividade do banco
- [ ] Testar funcionalidades básicas

## 🚀 **Comandos de Troubleshooting**

### **Verificar Status**

```bash
# Docker Compose
docker-compose ps
docker-compose logs

# Docker Swarm
docker stack ps <stack-name>
docker service logs <service-name>
```

### **Limpeza de Recursos**

```bash
# Remover stack
docker stack rm <stack-name>

# Remover rede
docker network rm <network-name>

# Limpeza geral
docker system prune -a
```

### **Teste de Conectividade**

```bash
# Testar Camunda
curl -f http://localhost:8080/camunda/app/welcome/default/

# Testar banco
docker exec -it <container-db> pg_isready -U camunda
```

## 📚 **Arquivos de Configuração**

### **docker-compose.yml (Local)**

- Versão: 3.3
- Sem profiles
- Healthcheck sem start_period
- depends_on simples

### **docker-compose.swarm.yml (Produção)**

- Versão: 3.3
- URL de banco com nome completo do serviço
- Deploy com replicas
- Configurações de rede

### **Variáveis de Ambiente**

```bash
# Banco de dados
DATABASE_URL=jdbc:postgresql://<service-name>:5432/camunda
POSTGRES_USER=camunda
POSTGRES_PASSWORD=<secure-password>

# Camunda
CAMUNDA_PORT=8080
CAMUNDA_USERNAME=admin
CAMUNDA_PASSWORD=<secure-password>
```

## ⚠️ **Problemas Conhecidos**

### **Parsing HTTP Errors**

```
Error parsing HTTP request header
Invalid character found in method name
```

**Causa:** Tentativas de conexão HTTPS/SSL na porta HTTP
**Solução:** Ignorar - são scanners de rede ou proxies mal configurados

### **Timeout de Conexão**

**Causa:** Banco de dados não acessível ou configuração incorreta
**Solução:** Verificar URL do banco e conectividade

### **Memória Insuficiente**

**Causa:** Recursos insuficientes no servidor
**Solução:** Aumentar RAM ou otimizar configurações Java

## 📝 **Notas de Manutenção**

- Sempre testar localmente antes do deploy remoto
- Manter logs de deploy para troubleshooting
- Documentar mudanças de configuração
- Fazer backup antes de mudanças importantes
- Monitorar recursos do servidor

---

**Última atualização:** 23/10/2025
**Versão:** 1.0
**Autor:** Sistema de Deploy Camunda
