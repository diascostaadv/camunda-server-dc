# Deploy n8n Passthrough Worker to Railway

Write-Host "Deploy n8n Passthrough Worker to Railway" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root
$projectRoot = "c:\www\camunda-server-dc\camunda-workers-platform"
Set-Location $projectRoot
Write-Host "Working directory: $projectRoot" -ForegroundColor Cyan
Write-Host ""

# Prompt for service name
$serviceName = Read-Host "Service name (default: n8n-passthrough-worker)"
if ([string]::IsNullOrWhiteSpace($serviceName)) {
    $serviceName = "n8n-passthrough-worker"
}

Write-Host "Deploying service: $serviceName" -ForegroundColor Green
Write-Host ""

# Deploy
railway up --service $serviceName

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Check logs: railway logs --service $serviceName"
    Write-Host "2. Configure variables in Railway Dashboard"
} else {
    Write-Host ""
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}
