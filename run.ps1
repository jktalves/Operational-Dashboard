param(
    [string]$HostName = "0.0.0.0",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    Write-Host "Criando virtualenv..."
    py -m venv .venv
}

Write-Host "Ativando virtualenv..."
. .\.venv\Scripts\Activate.ps1

Write-Host "Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Iniciando servidor em http://$HostName`:$Port"
uvicorn app.main:app --host $HostName --port $Port
