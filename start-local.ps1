# Script PowerShell para iniciar o Camunda Platform localmente
# Uso: .\start-local.ps1

Write-Host "🚀 Iniciando Camunda Platform localmente..." -ForegroundColor Cyan

# Verificar se Docker está rodando
Write-Host "`n🔍 Verificando Docker..." -ForegroundColor Cyan
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker não está acessível"
    }
    Write-Host "✅ Docker está rodando" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker não está rodando ou não está acessível." -ForegroundColor Red
    Write-Host "   Por favor, inicie o Docker Desktop e aguarde ele inicializar completamente." -ForegroundColor Yellow
    exit 1
}

# Navegar para o diretório do projeto
$platformDir = Join-Path $PSScriptRoot "camunda-platform-standalone"
if (-not (Test-Path $platformDir)) {
    Write-Host "❌ Diretório não encontrado: $platformDir" -ForegroundColor Red
    exit 1
}

Set-Location $platformDir

# Verificar se .env.local existe
if (-not (Test-Path ".env.local")) {
    Write-Host "❌ Arquivo .env.local não encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host "`n📊 Iniciando serviços..." -ForegroundColor Yellow

# Iniciar os serviços usando docker compose
# Usa docker-compose.simple.yml diretamente
docker compose -f docker-compose.simple.yml --env-file .env.local --profile local-db up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Serviços iniciados com sucesso!" -ForegroundColor Green
    Write-Host "`n⏳ Aguardando serviços ficarem prontos (30 segundos)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    Write-Host "`n🌐 URLs de acesso:" -ForegroundColor Cyan
    Write-Host "  Camunda:    http://localhost:8080 (demo/demo)" -ForegroundColor White
    Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor White
    Write-Host "  Grafana:    http://localhost:3001 (admin/admin)" -ForegroundColor White
    
    Write-Host "`n📊 Status dos containers:" -ForegroundColor Cyan
    docker compose -f docker-compose.simple.yml --env-file .env.local ps
    
    Write-Host "`n💡 Para ver logs: docker compose -f docker-compose.simple.yml --env-file .env.local logs -f" -ForegroundColor Gray
    Write-Host "💡 Para parar: docker compose -f docker-compose.simple.yml --env-file .env.local down" -ForegroundColor Gray
} else {
    Write-Host "`n❌ Erro ao iniciar serviços. Verifique os logs acima." -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot

