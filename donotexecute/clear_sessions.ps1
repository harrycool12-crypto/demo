# ─────────────────────────────────────────────────────────────────────────────
# Fit Zone Gym — Clear All Active Sessions
#
# Stops the running application (which wipes all in-memory login sessions),
# then restarts it automatically. All logged-in users will be sent to login.
# ─────────────────────────────────────────────────────────────────────────────

$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

Write-Host ""
Write-Host "  Fit Zone Gym — Clear Sessions" -ForegroundColor Cyan
Write-Host ""

# Find and stop the Python process running on port 8000
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $pid_to_kill = $conn.OwningProcess
    Write-Host "  Stopping application (PID $pid_to_kill)..." -ForegroundColor Yellow
    Stop-Process -Id $pid_to_kill -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "  Application stopped. All sessions cleared." -ForegroundColor Green
} else {
    Write-Host "  Application is not running on port 8000." -ForegroundColor Yellow
}

Write-Host ""
$restart = Read-Host "  Restart the application now? (Y/N)"
if ($restart -eq "Y" -or $restart -eq "y") {
    Write-Host ""
    Write-Host "  Starting application..." -ForegroundColor Cyan
    Start-Process python -ArgumentList "$ROOT\main.py" -WorkingDirectory $ROOT
    Write-Host "  Application started. Open http://127.0.0.1:8000" -ForegroundColor Green
}

Write-Host ""
