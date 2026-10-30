# Registers a Windows scheduled task that starts the webpages monitor every hour (at the full hour).
# The script itself decides whether a check is due ("check_interval_hours" / "check_anchor_hour"
# in settings.json). Runs without a console window (pythonw.exe); with "dev_mode": {"enabled": true}
# in settings.json the script opens a visible terminal window for each check.
# Usage (PowerShell):  .\install_task.ps1            -> install / update
#                      .\install_task.ps1 -Remove    -> uninstall
param(
    [string]$TaskName = "PP-Webpages-Monitor",
    [switch]$Remove
)

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $projectDir "webpages_monitor.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Task '$TaskName' removed."
    return
}

# pythonw.exe runs without a console window (dev mode opens a window when needed)
$python = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python.exe).Source }

# first start at the next full hour, then every hour
$now = Get-Date
$start = $now.Date.AddHours($now.Hour + 1)

$action   = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $projectDir
$trigger  = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 50)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Task '$TaskName' registered: every hour from $($start.ToString('yyyy-MM-dd HH:mm')) using $python"
