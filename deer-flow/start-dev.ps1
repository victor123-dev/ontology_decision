# DeerFlow Development Server Start Script for Windows
# This script replicates the functionality of 'make dev' on Windows

param(
    [switch]$Dev = $true,
    [switch]$Prod = $false
)

$ErrorActionPreference = "Stop"
$REPO_ROOT = $PSScriptRoot

# Validate config exists
if (!(Test-Path "$REPO_ROOT/config.yaml") -and !(Test-Path "$REPO_ROOT/backend/config.yaml")) {
    Write-Host "✗ No DeerFlow config file found." -ForegroundColor Red
    Write-Host "  Checked these locations:" -ForegroundColor Red
    Write-Host "    - $REPO_ROOT/config.yaml" -ForegroundColor Red
    Write-Host "    - $REPO_ROOT/backend/config.yaml" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Run 'python scripts/configure.py' from the repo root to generate ./config.yaml, then set required model API keys in .env or your config file." -ForegroundColor Red
    exit 1
}

# Create logs directory
if (!(Test-Path "$REPO_ROOT/logs")) {
    New-Item -ItemType Directory -Path "$REPO_ROOT/logs" | Out-Null
}

# Set frontend command based on mode
if ($Dev) {
    $FRONTEND_CMD = "pnpm run dev"
    Write-Host "Starting DeerFlow Development Server (DEV mode with hot-reload)" -ForegroundColor Green
} else {
    $BETTER_AUTH_SECRET = python -c "import secrets; print(secrets.token_hex(16))"
    $env:BETTER_AUTH_SECRET = $BETTER_AUTH_SECRET
    $FRONTEND_CMD = "pnpm run preview"
    Write-Host "Starting DeerFlow Production Server (PROD mode without hot-reload)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Services starting up..." -ForegroundColor Cyan
Write-Host "  → Backend: LangGraph + Gateway" -ForegroundColor Cyan
Write-Host "  → Frontend: Next.js" -ForegroundColor Cyan

# Function to wait for port
function Wait-ForPort {
    param($Port, $TimeoutSeconds, $ServiceName)
    $StartTime = Get-Date
    while ((Get-Date) -lt $StartTime.AddSeconds($TimeoutSeconds)) {
        try {
            $TcpClient = New-Object System.Net.Sockets.TcpClient
            $AsyncResult = $TcpClient.BeginConnect("localhost", $Port, $null, $null)
            $WaitHandle = $AsyncResult.AsyncWaitHandle
            if ($WaitHandle.WaitOne(1000, $false)) {
                $TcpClient.EndConnect($AsyncResult)
                $TcpClient.Close()
                Write-Host "✓ $ServiceName started on localhost:$Port" -ForegroundColor Green
                return $true
            }
        } catch {
            # Port not ready yet, continue waiting
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# Start LangGraph server
Write-Host "Starting LangGraph server..."
Start-Process -FilePath "powershell" -ArgumentList "-Command `"cd '$REPO_ROOT\backend'; `$env:NO_COLOR='1'; uv run langgraph dev --no-browser --allow-blocking > '$REPO_ROOT\logs\langgraph.log' 2>&1`"" -PassThru | Out-Null

if (-not (Wait-ForPort -Port 2024 -TimeoutSeconds 60 -ServiceName "LangGraph server")) {
    Write-Host "✗ LangGraph server failed to start. See logs/langgraph.log for details" -ForegroundColor Red
    Get-Content "$REPO_ROOT\logs\langgraph.log" -Tail 20
    if (Select-String -Path "$REPO_ROOT\logs\langgraph.log" -Pattern "config_version|outdated|Environment variable .* not found|KeyError|ValidationError|config\.yaml") {
        Write-Host ""
        Write-Host "  Hint: This may be a configuration issue. Try running './scripts/config-upgrade.sh' to update your config.yaml." -ForegroundColor Yellow
    }
    exit 1
}

# Start Gateway API
Write-Host "Starting Gateway API..."
$GatewayArgs = "--host 0.0.0.0 --port 8001"
if ($Dev) {
    $GatewayArgs += " --reload --reload-include='*.yaml' --reload-include='.env'"
}
Start-Process -FilePath "powershell" -ArgumentList "-Command `"cd '$REPO_ROOT\backend'; `$env:PYTHONPATH='.'; uv run uvicorn app.gateway.app:app $GatewayArgs > '$REPO_ROOT\logs\gateway.log' 2>&1`"" -PassThru | Out-Null

if (-not (Wait-ForPort -Port 8001 -TimeoutSeconds 30 -ServiceName "Gateway API")) {
    Write-Host "✗ Gateway API failed to start. Last log output:" -ForegroundColor Red
    Get-Content "$REPO_ROOT\logs\gateway.log" -Tail 60
    Write-Host ""
    Write-Host "Likely configuration errors:" -ForegroundColor Red
    Select-String -Path "$REPO_ROOT\logs\gateway.log" -Pattern "Failed to load configuration|Environment variable .* not found|config\.yaml.*not found" | Select-Object -Last 5
    Write-Host ""
    Write-Host "  Hint: Try running './scripts/config-upgrade.sh' to update your config.yaml with the latest fields." -ForegroundColor Yellow
    exit 1
}

# Start Frontend
Write-Host "Starting Frontend..."
Start-Process -FilePath "powershell" -ArgumentList "-Command `"cd '$REPO_ROOT\frontend'; $FRONTEND_CMD > '$REPO_ROOT\logs\frontend.log' 2>&1`"" -PassThru | Out-Null

if (-not (Wait-ForPort -Port 3000 -TimeoutSeconds 120 -ServiceName "Frontend")) {
    Write-Host "✗ Frontend failed to start. See logs/frontend.log for details" -ForegroundColor Red
    Get-Content "$REPO_ROOT\logs\frontend.log" -Tail 20
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✓ DeerFlow development server is running!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  🌐 Direct access URLs:" -ForegroundColor Cyan
Write-Host "     - Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "     - API Gateway: http://localhost:8001" -ForegroundColor Cyan  
Write-Host "     - LangGraph: http://localhost:2024" -ForegroundColor Cyan
Write-Host ""
Write-Host "  📋 Logs:" -ForegroundColor Cyan
Write-Host "     - LangGraph: logs/langgraph.log" -ForegroundColor Cyan
Write-Host "     - Gateway:   logs/gateway.log" -ForegroundColor Cyan
Write-Host "     - Frontend:  logs/frontend.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

# Keep the script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "Shutting down services..." -ForegroundColor Yellow
    
    # Kill all child processes (this is a simplified approach)
    Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*node*" } | 
        ForEach-Object {
            if ($_.MainWindowTitle -eq "" -and $_.Id -ne $PID) {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        }
    
    Write-Host "✓ All services stopped" -ForegroundColor Green
}