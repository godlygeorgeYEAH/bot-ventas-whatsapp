# Script para reiniciar el bot automáticamente
Write-Host "🔄 Deteniendo bot..." -ForegroundColor Yellow

# Buscar y matar proceso de Python del bot
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*Context Bot V2*"
} | Stop-Process -Force

Start-Sleep -Seconds 2

Write-Host "✅ Bot detenido" -ForegroundColor Green
Write-Host "🚀 Iniciando bot..." -ForegroundColor Yellow

# Iniciar bot en nueva ventana
$scriptPath = "C:\work\work\Context Bot V2\bot-ventas-whatsapp"
$pythonPath = "C:\work\work\Context Bot V2\libs\Scripts\python.exe"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$scriptPath'; & '$pythonPath' run.py"
)

Start-Sleep -Seconds 3
Write-Host "✅ Bot iniciado en nueva ventana" -ForegroundColor Green
Write-Host "📱 Esperando a que el bot esté listo..." -ForegroundColor Yellow

# Esperar a que el servidor responda
$maxAttempts = 10
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    Start-Sleep -Seconds 2
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            Write-Host "✅ Bot listo en http://localhost:8000" -ForegroundColor Green
        }
    } catch {
        Write-Host "⏳ Intento $attempt/$maxAttempts..." -ForegroundColor Gray
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "🎉 Bot reiniciado exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ahora recarga la webapp en tu navegador:" -ForegroundColor Cyan
    Write-Host "http://localhost:5174/cart/TU-TOKEN-AQUI" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "⚠️  El bot no respondió a tiempo" -ForegroundColor Red
    Write-Host "Verifica la ventana nueva que se abrió para ver errores" -ForegroundColor Yellow
}

