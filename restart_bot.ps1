# Script para reiniciar el bot
Write-Host "Deteniendo procesos de Python..."
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "Esperando 3 segundos..."
Start-Sleep -Seconds 3

Write-Host "Iniciando bot..."
cd "C:\work\work\Context Bot V2\bot-ventas-whatsapp"
Start-Process python -ArgumentList "run.py", "-v" -WindowStyle Hidden

Write-Host "Bot iniciado en segundo plano"
Start-Sleep -Seconds 5

Write-Host "Verificando procesos..."
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime

