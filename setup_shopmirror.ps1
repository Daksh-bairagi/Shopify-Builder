$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "shopmirror\backend"
$frontendDir = Join-Path $repoRoot "shopmirror\frontend"

$backendVenvDir = Join-Path $backendDir ".venv"
$backendPython = Join-Path $backendVenvDir "Scripts\python.exe"
$backendRequirements = Join-Path $backendDir "requirements.txt"
$backendEnvExample = Join-Path $backendDir ".env.example"
$backendEnv = Join-Path $backendDir ".env"

$frontendEnvExample = Join-Path $frontendDir ".env.example"
$frontendEnv = Join-Path $frontendDir ".env"

Write-Host "Setting up ShopMirror..." -ForegroundColor Cyan

if (-not (Test-Path $backendPython)) {
    Write-Host "Creating backend virtualenv..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        python -m venv .venv
    }
    finally {
        Pop-Location
    }
}

Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
& $backendPython -m pip install --upgrade pip
& $backendPython -m pip install -r $backendRequirements

Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Push-Location $frontendDir
try {
    npm install
}
finally {
    Pop-Location
}

if (-not (Test-Path $backendEnv) -and (Test-Path $backendEnvExample)) {
    Copy-Item -LiteralPath $backendEnvExample -Destination $backendEnv
    Write-Host "Created backend .env from .env.example" -ForegroundColor Green
}

if (-not (Test-Path $frontendEnv) -and (Test-Path $frontendEnvExample)) {
    Copy-Item -LiteralPath $frontendEnvExample -Destination $frontendEnv
    Write-Host "Created frontend .env from .env.example" -ForegroundColor Green
}

Write-Host "" 
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Fill in shopmirror\backend\.env with your API keys and config."
Write-Host "2. Run: cd shopmirror && docker compose up -d"
Write-Host "3. Run: powershell -ExecutionPolicy Bypass -File .\shopmirror\backend\start_backend.ps1"
Write-Host "4. Run: cd shopmirror\frontend && npm run dev"
