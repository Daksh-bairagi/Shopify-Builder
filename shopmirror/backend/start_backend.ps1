$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
$requirementsFile = Join-Path $scriptDir "requirements.txt"

if (-not (Test-Path $venvPython)) {
    throw "Backend virtualenv not found at '$venvPython'. Recreate it before starting the API."
}

& $venvPython -c "import langchain_google_genai" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend dependencies into .venv..."
    & $venvPython -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency install failed."
    }
}

Push-Location $scriptDir
try {
    & $venvPython -m uvicorn app.main:app --reload --port 8000
}
finally {
    Pop-Location
}
