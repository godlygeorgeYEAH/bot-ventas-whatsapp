# Script para abrir 4 ventanas de PowerShell en cuadrantes
# Requiere ejecutarse con: powershell -ExecutionPolicy Bypass -File start-quad-windows.ps1

Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();
    }
"@

# Obtener dimensiones de la pantalla
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$width = $screen.Width
$height = $screen.Height

# Calcular tamaño de cada cuadrante (25% de la pantalla)
$quadrantWidth = [math]::Floor($width / 2)
$quadrantHeight = [math]::Floor($height / 2)

# Función para iniciar PowerShell y posicionar ventana
function Start-QuadrantWindow {
    param(
        [int]$X,
        [int]$Y,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $arguments = "-NoExit", "-Command", "cd '$WorkingDirectory'; $Command"
    $process = Start-Process powershell -ArgumentList $arguments -PassThru

    # Esperar a que la ventana se cree
    Start-Sleep -Milliseconds 500

    # Intentar obtener el handle de la ventana
    $hWnd = $process.MainWindowHandle
    if ($hWnd -eq 0) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
        $hWnd = $process.MainWindowHandle
    }

    # Posicionar y redimensionar la ventana
    if ($hWnd -ne 0) {
        [Win32]::ShowWindow($hWnd, 9) # SW_RESTORE
        [Win32]::MoveWindow($hWnd, $X, $Y, $quadrantWidth, $quadrantHeight, $true)
    }

    return $process
}

Write-Host "Iniciando 4 ventanas de PowerShell en cuadrantes..." -ForegroundColor Green
Write-Host ""

# Cuadrante Superior Izquierdo (0, 0)
Write-Host "[1/4] Ventana superior izquierda - bot-ventas-whatsapp (activate)" -ForegroundColor Cyan
$window1 = Start-QuadrantWindow -X 0 -Y 0 -WorkingDirectory "C:\work\work\Context Bot V2\bot-ventas-whatsapp" -Command "..\libs\scripts\activate"

Start-Sleep -Milliseconds 300

# Cuadrante Superior Derecho (mitad del ancho, 0)
Write-Host "[2/4] Ventana superior derecha - bot-ventas-whatsapp (activate)" -ForegroundColor Cyan
$window2 = Start-QuadrantWindow -X $quadrantWidth -Y 0 -WorkingDirectory "C:\work\work\Context Bot V2\bot-ventas-whatsapp" -Command "..\libs\scripts\activate"

Start-Sleep -Milliseconds 300

# Cuadrante Inferior Izquierdo (0, mitad de la altura)
Write-Host "[3/4] Ventana inferior izquierda - dashboard (npm run dev)" -ForegroundColor Cyan
$window3 = Start-QuadrantWindow -X 0 -Y $quadrantHeight -WorkingDirectory "C:\work\work\Context Bot V2\bot-ventas-whatsapp\dashboard" -Command "npm run dev"

Start-Sleep -Milliseconds 300

# Cuadrante Inferior Derecho (mitad del ancho, mitad de la altura)
Write-Host "[4/4] Ventana inferior derecha - webapp-cart (npm run dev)" -ForegroundColor Cyan
$window4 = Start-QuadrantWindow -X $quadrantWidth -Y $quadrantHeight -WorkingDirectory "C:\work\work\Context Bot V2\bot-ventas-whatsapp\webapp-cart" -Command "npm run dev"

Write-Host ""
Write-Host "¡Todas las ventanas han sido iniciadas!" -ForegroundColor Green
Write-Host ""
Write-Host "Distribución de ventanas:" -ForegroundColor Yellow
Write-Host "  Superior Izquierda  : bot-ventas-whatsapp (activate)" -ForegroundColor White
Write-Host "  Superior Derecha    : bot-ventas-whatsapp (activate)" -ForegroundColor White
Write-Host "  Inferior Izquierda  : dashboard (npm run dev)" -ForegroundColor White
Write-Host "  Inferior Derecha    : webapp-cart (npm run dev)" -ForegroundColor White
Write-Host ""
Write-Host "Presiona cualquier tecla para cerrar esta ventana..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
