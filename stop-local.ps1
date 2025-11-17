# Script PowerShell para parar o Camunda Platform localmente
# Uso: .\stop-local.ps1

Write-Host "⏹️ Parando Camunda Platform..." -ForegroundColor Yellow

$platformDir = Join-Path $PSScriptRoot "camunda-platform-standalone"
if (Test-Path $platformDir) {
    Set-Location $platformDir
    docker compose -f docker-compose.simple.yml --env-file .env.local down
    Write-Host "✅ Serviços parados!" -ForegroundColor Green
    Set-Location $PSScriptRoot
} else {
    Write-Host "❌ Diretório não encontrado: $platformDir" -ForegroundColor Red
}

