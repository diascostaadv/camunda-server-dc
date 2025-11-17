# 🚀 Guia de Início Rápido - Windows

Este guia vai te ajudar a rodar o projeto Camunda localmente no Windows.

## ✅ Pré-requisitos

- ✅ Docker Desktop instalado e rodando
- ✅ Make instalado (ou use os scripts PowerShell)
- ✅ PowerShell 5.1+ ou PowerShell 7+

## 🎯 Opção 1: Usando Script PowerShell (Mais Fácil)

### Passo 1: Verificar Docker

```powershell
docker --version
docker ps
```

Se o Docker não estiver rodando, inicie o **Docker Desktop**.

### Passo 2: Iniciar Serviços

Na raiz do projeto, execute:

```powershell
.\start-local.ps1
```

Isso vai:
- ✅ Verificar se Docker está rodando
- ✅ Iniciar PostgreSQL, Camunda, Prometheus e Grafana
- ✅ Aguardar serviços ficarem prontos
- ✅ Mostrar URLs de acesso

### Passo 3: Acessar

Após ~30 segundos, acesse:
- **Camunda**: http://localhost:8080 (usuário: `demo`, senha: `demo`)
- **Grafana**: http://localhost:3001 (usuário: `admin`, senha: `admin`)
- **Prometheus**: http://localhost:9090

### Parar Serviços

```powershell
.\stop-local.ps1
```

---

## 🎯 Opção 2: Usando Docker Compose Diretamente

### Passo 1: Navegar para o projeto

```powershell
cd camunda-platform-standalone
```

### Passo 2: Verificar arquivo .env.local

```powershell
Test-Path .env.local
```

Se retornar `True`, está OK. Se retornar `False`, você precisa criar o arquivo (mas ele já deve existir).

### Passo 3: Iniciar serviços

```powershell
docker compose --env-file .env.local --profile local-db up -d
```

### Passo 4: Verificar status

```powershell
docker compose --env-file .env.local ps
```

### Passo 5: Ver logs (opcional)

```powershell
docker compose --env-file .env.local logs -f
```

### Parar serviços

```powershell
docker compose --env-file .env.local down
```

---

## 🎯 Opção 3: Usando Make (WSL ou Git Bash)

### Passo 1: Converter line endings (se necessário)

No WSL ou Git Bash:

```bash
cd camunda-platform-standalone
find scripts -name "*.sh" -exec sed -i 's/\r$//' {} \;
```

### Passo 2: Iniciar

```bash
make local-up
```

---

## 🔍 Verificação e Troubleshooting

### Verificar se Docker está rodando

```powershell
docker ps
```

Se der erro, inicie o Docker Desktop.

### Verificar portas em uso

```powershell
# Verificar se as portas estão livres
netstat -ano | findstr ":8080"
netstat -ano | findstr ":5432"
netstat -ano | findstr ":9090"
netstat -ano | findstr ":3001"
```

Se alguma porta estiver em uso, você pode:
1. Parar o serviço que está usando a porta
2. Ou alterar a porta no `.env.local`

### Ver logs de erro

```powershell
cd camunda-platform-standalone
docker compose --env-file .env.local logs
```

### Ver logs de um serviço específico

```powershell
docker compose --env-file .env.local logs camunda
docker compose --env-file .env.local logs db
```

### Reiniciar um serviço específico

```powershell
docker compose --env-file .env.local restart camunda
```

### Limpar tudo e começar do zero

```powershell
cd camunda-platform-standalone
docker compose --env-file .env.local down -v
docker compose --env-file .env.local --profile local-db up -d
```

O `-v` remove os volumes (dados do banco serão perdidos).

---

## 🐛 Problemas Comuns

### Erro: "Port already in use"

**Solução**: Pare o serviço que está usando a porta ou altere a porta no `.env.local`

### Erro: "Cannot connect to Docker daemon"

**Solução**: Inicie o Docker Desktop

### Erro: "No such file or directory: .env.local"

**Solução**: Verifique se você está no diretório correto (`camunda-platform-standalone`)

### Erro: Scripts .sh com line endings errados

**Solução**: Já foi corrigido! Mas se aparecer novamente:
```powershell
Get-ChildItem -Path camunda-platform-standalone\scripts -Filter *.sh | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $content = $content -replace "`r`n", "`n" -replace "`r", "`n"
    [System.IO.File]::WriteAllText($_.FullName, $content, [System.Text.UTF8Encoding]::new($false))
}
```

### Erro: "Container name already in use"

**Solução**: Pare os containers existentes:
```powershell
docker compose --env-file .env.local down
```

---

## 📊 Comandos Úteis

### Ver status dos containers

```powershell
docker compose --env-file .env.local ps
```

### Ver uso de recursos

```powershell
docker stats
```

### Acessar banco de dados

```powershell
docker compose --env-file .env.local exec db psql -U camunda -d camunda
```

### Acessar shell do container Camunda

```powershell
docker compose --env-file .env.local exec camunda sh
```

---

## ✅ Checklist de Verificação

Após iniciar, verifique:

- [ ] Docker Desktop está rodando
- [ ] Containers estão rodando: `docker compose ps`
- [ ] Camunda acessível: http://localhost:8080
- [ ] Grafana acessível: http://localhost:3001
- [ ] Prometheus acessível: http://localhost:9090
- [ ] Logs não mostram erros críticos

---

## 🎉 Próximos Passos

Depois que tudo estiver rodando:

1. **Explorar Camunda**: http://localhost:8080
   - Login: `demo` / `demo`
   - Explore Cockpit, Tasklist, Admin

2. **Ver métricas no Grafana**: http://localhost:3001
   - Login: `admin` / `admin`
   - Dashboards pré-configurados disponíveis

3. **Iniciar Workers**: Veja `camunda-workers-platform/README.md`

4. **Iniciar Gateway**: Veja `camunda-worker-api-gateway/README.md`

---

## 💡 Dica

Se você tiver problemas, sempre comece verificando:
1. Docker está rodando?
2. Portas estão livres?
3. Arquivo `.env.local` existe?
4. Logs mostram algum erro específico?

