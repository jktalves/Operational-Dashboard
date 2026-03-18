param(
    [string]$TaskName = "OpenSalesforceDashboardOnBoot",
    [string]$DashboardUrl = "http://localhost:8080",
    [string]$BrowserPath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    [string]$UserName = "$env:USERNAME"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BrowserPath)) {
    Write-Error "Microsoft Edge nao encontrado em $BrowserPath"
    exit 1
}

$actionArgs = "--kiosk $DashboardUrl --edge-kiosk-type=fullscreen --no-first-run"
$action = New-ScheduledTaskAction -Execute $BrowserPath -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserName
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Abre painel Salesforce em modo TV" -Force | Out-Null
Write-Host "Task criada: $TaskName"
