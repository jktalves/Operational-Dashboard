param(
    [string]$ProjectPath = "E:\PROJETOS DEV\Painel tv",
    [string]$ServiceName = "SalesforceTvDashboard",
    [string]$DisplayName = "Salesforce TV Dashboard",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$pythonExe = Join-Path $ProjectPath ".venv\Scripts\python.exe"
$appModule = "app.main:app"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python virtualenv nao encontrado em $pythonExe"
    exit 1
}

$serviceCommand = "`"$pythonExe`" -m uvicorn $appModule --host 0.0.0.0 --port $Port --app-dir `"$ProjectPath`""

sc.exe create $ServiceName "binPath= $serviceCommand" start= auto "DisplayName= $DisplayName" | Out-Null
sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/5000/restart/5000 | Out-Null
sc.exe start $ServiceName | Out-Null

Write-Host "Servico instalado e iniciado: $ServiceName"
