# 🚀 Quick Fix: Camunda Container Deploy

## ⚡ Problema: Containers não sobem na VM remota

### 🔍 **Diagnóstico Rápido (30 segundos)**
```bash
# Verificar estado da VM
ssh ubuntu@201.23.67.197 "docker info --format '{{ .Swarm.LocalNodeState }}' && docker ps"

# Se retornar "inactive" ou erro de network → Problema de rede
# Se retornar "No services found" → Problema de profiles
```

### ✅ **Soluções Rápidas**

#### **1. Erro de Rede (mais comum)**
```bash
# Solução A: Inicializar Swarm
make init

# Solução B: Usar modo local (bridge network)
ENVIRONMENT=local make deploy
ENVIRONMENT=production make deploy

# Solução C: Forçar bridge
ssh ubuntu@201.23.67.197 "echo 'NETWORK_DRIVER=bridge' >> ~/camunda-swarm/.env.production"
```

#### **2. Modo Mais Seguro (sempre funciona)**
```bash
# Deploy básico sem workers
WORKERS_MODE=embedded ENVIRONMENT=local make deploy

# Verificar se funcionou
curl http://201.23.67.197:8080/camunda/app/welcome/
```

#### **3. Reset Completo (se nada funcionar)**
```bash
make down
ssh ubuntu@201.23.67.197 "docker system prune -af && docker swarm leave --force || true"
make init && make deploy
```

### 🛠️ **Comandos de Validação**
```bash
# Verificar containers rodando
ssh ubuntu@201.23.67.197 "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Testar serviços
curl http://201.23.67.197:8080/camunda/app/welcome/  # Camunda
curl http://201.23.67.197:9090/-/healthy            # Prometheus  
curl http://201.23.67.197:3001/api/health          # Grafana
```

### 📋 **Checklist de Problemas Comuns**

- [ ] **SSH funcionando**: `ssh ubuntu@201.23.67.197 "echo OK"`
- [ ] **Docker instalado**: `ssh ubuntu@201.23.67.197 "docker --version"`
- [ ] **Arquivos copiados**: `make copy`
- [ ] **Swarm ativo ou bridge network**: Ver diagnóstico acima

### ⚠️ **Problemas de Segurança Encontrados**
- Credenciais MongoDB/RabbitMQ expostas no código
- **AÇÃO IMEDIATA**: Rotacionar credenciais do MongoDB Atlas e RabbitMQ CloudAMQP

---

## 📚 Documentação Completa
Para análise detalhada de todos os problemas: [`CONTAINER_DEPLOYMENT_TROUBLESHOOTING.md`](camunda-swarm/CONTAINER_DEPLOYMENT_TROUBLESHOOTING.md)

---
**Tempo estimado de resolução**: 2-10 minutos