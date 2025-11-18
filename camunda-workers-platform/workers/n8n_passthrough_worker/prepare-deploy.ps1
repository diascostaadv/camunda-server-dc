# Deploy apenas da pasta n8n_passthrough_worker para Railway
# Cria um ZIP temporário apenas com os arquivos necessários

Write-Host "Preparando deploy do n8n_passthrough_worker..." -ForegroundColor Cyan

# Criar pasta temporária
$tempDir = Join-Path $env:TEMP "n8n-worker-deploy"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copiar apenas arquivos necessários
$files = @(
    "main.py",
    "requirements.txt",
    ".env.example"
)

foreach ($file in $files) {
    Copy-Item $file $tempDir -Force
    Write-Host "Copiado: $file" -ForegroundColor Green
}

Write-Host "`nArquivos preparados em: $tempDir" -ForegroundColor Yellow
Write-Host "`nAGORA:" -ForegroundColor Cyan
Write-Host "1. Acesse Railway Dashboard: https://railway.app/dashboard" -ForegroundColor Gray
Write-Host "2. Servico: n8n-passthrough-worker" -ForegroundColor Gray  
Write-Host "3. Settings > Source > Upload Files" -ForegroundColor Gray
Write-Host "4. Selecione TODOS os arquivos de: $tempDir" -ForegroundColor Gray
Write-Host "5. Custom Start Command: python main.py" -ForegroundColor Gray
Write-Host "`nPressione qualquer tecla para abrir a pasta..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

explorer $tempDir
