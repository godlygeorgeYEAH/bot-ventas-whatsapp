# Script para habilitar acceso de red al dashboard
# Ejecutar como Administrador: Click derecho -> "Ejecutar con PowerShell"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Configurando Firewall para Dashboard Móvil" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Regla para Vite Dev Server (Puerto 5173)
Write-Host "Creando regla para Vite (puerto 5173)..." -ForegroundColor Yellow
try {
    netsh advfirewall firewall add rule name="Vite Dev Server" dir=in action=allow protocol=TCP localport=5173
    Write-Host "✓ Regla para Vite creada exitosamente" -ForegroundColor Green
} catch {
    Write-Host "✗ Error al crear regla para Vite" -ForegroundColor Red
}

Write-Host ""

# Regla para FastAPI (Puerto 8000)
Write-Host "Creando regla para FastAPI (puerto 8000)..." -ForegroundColor Yellow
try {
    netsh advfirewall firewall add rule name="FastAPI Dev Server" dir=in action=allow protocol=TCP localport=8000
    Write-Host "✓ Regla para FastAPI creada exitosamente" -ForegroundColor Green
} catch {
    Write-Host "✗ Error al crear regla para FastAPI" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan

# Mostrar IPs locales
Write-Host "Tus direcciones IP locales:" -ForegroundColor Cyan
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "192.168.*" }
foreach ($ip in $ips) {
    Write-Host "  http://$($ip.IPAddress):5173" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Configuración completada!" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso:" -ForegroundColor Yellow
Write-Host "1. Reinicia el servidor Vite (Ctrl+C y 'npm run dev')" -ForegroundColor White
Write-Host "2. Accede desde tu móvil usando una de las IPs de arriba" -ForegroundColor White
Write-Host ""
Write-Host "Presiona cualquier tecla para salir..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

