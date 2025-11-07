# 🆘 URGENTE: Limpar Espaço em Disco na VM

**Erro**: `No space left on device (28)`
**VM**: 201.23.69.65
**Status**: ⚠️ CRÍTICO - Precisa limpar ANTES de qualquer deploy

---

## 🔍 PASSO 1: Diagnosticar Espaço em Disco

```bash
# SSH na VM
ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65

# Verificar uso geral
df -h

# Verificar uso por diretório
du -sh /home/ubuntu/* | sort -rh | head -20
du -sh /var/* | sort -rh | head -20
```

**Procure por**:
- `/var/lib/docker` - Imagens e containers Docker
- `/home/ubuntu/camunda-server-dc` - Código do projeto
- `/var/log` - Logs de sistema

---

## 🧹 PASSO 2: Limpar Docker (Mais Efetivo)

### Opção A: Limpeza Agressiva (RECOMENDADO)

```bash
# Parar todos os containers
docker stop $(docker ps -aq)

# Remover containers parados
docker container prune -f

# Remover imagens não usadas
docker image prune -a -f

# Remover volumes não usados
docker volume prune -f

# Remover redes não usadas
docker network prune -f

# Limpar build cache
docker builder prune -af

# Verificar espaço recuperado
df -h
```

**Espaço recuperado esperado**: 5-20 GB

### Opção B: Limpeza Seletiva (Mais Segura)

```bash
# Ver imagens Docker (verificar tamanho)
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | sort -k3 -hr

# Remover imagens antigas/não usadas
docker rmi $(docker images -f "dangling=true" -q)

# Ver volumes Docker
docker volume ls

# Remover volumes não usados
docker volume prune -f
```

---

## 🗑️ PASSO 3: Limpar Logs

```bash
# Ver tamanho dos logs Docker
sudo du -sh /var/lib/docker/containers/*/*.log | sort -rh | head -10

# Limpar logs Docker maiores que 100MB
sudo find /var/lib/docker/containers/ -name "*.log" -size +100M -delete

# Limpar logs de sistema antigos
sudo journalctl --vacuum-time=7d
sudo journalctl --vacuum-size=500M

# Limpar logs apt
sudo apt-get clean
sudo apt-get autoclean
```

---

## 📦 PASSO 4: Limpar Arquivos Temporários

```bash
# Limpar cache apt
sudo apt-get clean
sudo rm -rf /var/cache/apt/archives/*

# Limpar arquivos temporários
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# Limpar old kernels (CUIDADO!)
sudo apt-get autoremove --purge -y
```

---

## 🔍 PASSO 5: Verificar Espaço Recuperado

```bash
# Verificar espaço disponível
df -h

# Deve mostrar:
# /dev/sda1       30G    15G    14G   52% /
# Ou similar com pelo menos 5-10GB livres
```

---

## 🚀 PASSO 6: Comandos Completos (Copy & Paste)

```bash
# SSH na VM
ssh -i ~/.ssh/id_rsa ubuntu@201.23.69.65

# Limpeza completa
echo "🔍 Espaço atual:"
df -h

echo "🧹 Limpando Docker..."
docker stop $(docker ps -aq)
docker container prune -f
docker image prune -a -f
docker volume prune -f
docker network prune -f
docker builder prune -af

echo "🗑️ Limpando logs..."
sudo find /var/lib/docker/containers/ -name "*.log" -size +50M -delete
sudo journalctl --vacuum-time=7d
sudo journalctl --vacuum-size=500M

echo "📦 Limpando cache..."
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get autoremove --purge -y

echo "✅ Espaço após limpeza:"
df -h
```

---

## ⚠️ ALTERNATIVA: Aumentar Disco da VM

Se a limpeza não resolver (disco muito pequeno):

### Azure CLI
```bash
# Ver disco atual
az vm show -g <resource-group> -n <vm-name> --query "storageProfile.osDisk.diskSizeGb"

# Aumentar disco para 50GB (por exemplo)
az vm deallocate -g <resource-group> -n <vm-name>
az disk update -g <resource-group> -n <disk-name> --size-gb 50
az vm start -g <resource-group> -n <vm-name>

# Na VM, expandir partição
ssh ubuntu@201.23.69.65
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
df -h
```

---

## 📊 Análise de Uso Típico

Após limpeza, uso esperado:
```
Sistema Operacional:     2-3 GB
Docker Images:           3-5 GB
Docker Volumes:          1-2 GB
Logs:                    500MB - 1GB
Código Projeto:          500MB
Buffer Livre:            5-10 GB (mínimo recomendado)
TOTAL:                   15-25 GB
```

**Disco Recomendado**: 30-50 GB

---

## ✅ Após Limpar

Execute novamente o deploy:

```bash
# Na sua máquina local
cd /Users/pedromarques/dev/dias_costa/camunda/camunda-server-dc/camunda-worker-api-gateway
make copy-files

# Se funcionar, prosseguir com deploy
```

---

## 🆘 Se Continuar com Problema

1. **Verificar tamanho do disco**:
   ```bash
   ssh ubuntu@201.23.69.65 "df -h && du -sh /var/lib/docker"
   ```

2. **Aumentar disco da VM** (via Azure Portal ou CLI)

3. **Considerar usar Azure Container Registry** (evita build na VM)

---

**⚠️ EXECUTE A LIMPEZA ANTES DE QUALQUER DEPLOY!**
