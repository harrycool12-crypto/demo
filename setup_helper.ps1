# ─────────────────────────────────────────────────────────────────────────────
#  Fit Zone Gym Management System - System Readiness Setup
#  Run via setup.bat (auto-elevates to Administrator)
# ─────────────────────────────────────────────────────────────────────────────

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

$pass = 0
$fail = 0

function Write-Step($msg) { Write-Host "`n  >> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "     [OK]  $msg" -ForegroundColor Green;  $script:pass++ }
function Write-FAIL($msg) { Write-Host "     [FAIL] $msg" -ForegroundColor Red;   $script:fail++ }
function Write-INFO($msg) { Write-Host "     [INFO] $msg" -ForegroundColor Yellow }

Clear-Host
Write-Host ""
Write-Host "  +==================================================+" -ForegroundColor Green
Write-Host "  |   FIT ZONE GYM - SYSTEM READINESS SETUP          |" -ForegroundColor Green
Write-Host "  +==================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Working directory: $ROOT" -ForegroundColor Gray
Write-Host ""

# ── STEP 1: Check Windows Version ────────────────────────────────────────────
Write-Step "Step 1: Checking Windows version..."
$os = (Get-CimInstance Win32_OperatingSystem).Caption
Write-OK "OS: $os"

# ── STEP 2: Check / Install Python ───────────────────────────────────────────
Write-Step "Step 2: Checking Python..."
$pythonOK = $false
try {
    $ver = & python --version 2>&1
    if ($ver -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 9) {
            Write-OK "Python $major.$minor found - meets requirement (3.9+)"
            $pythonOK = $true
        } else {
            Write-FAIL "Python $major.$minor found but 3.9+ is required."
        }
    }
} catch {
    Write-FAIL "Python not found in PATH."
}

if (-not $pythonOK) {
    Write-INFO "Attempting to install Python 3.12 via winget..."
    try {
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path","User")
        $ver = & python --version 2>&1
        if ($ver -match "Python") {
            Write-OK "Python installed successfully: $ver"
            $pythonOK = $true
        } else {
            Write-FAIL "Python installation finished but still not found in PATH."
            Write-INFO "Install Python 3.12 manually from https://www.python.org/downloads/"
            Write-INFO "IMPORTANT: Tick 'Add Python to PATH' during installation, then re-run setup."
        }
    } catch {
        Write-FAIL "winget unavailable or installation failed."
        Write-INFO "Install Python 3.12 manually from https://www.python.org/downloads/"
        Write-INFO "IMPORTANT: Tick 'Add Python to PATH' during installation, then re-run setup."
    }
}

# ── STEP 3: Check pip ────────────────────────────────────────────────────────
Write-Step "Step 3: Checking pip..."
try {
    $pipVer = & python -m pip --version 2>&1
    if ($pipVer -match "pip") {
        Write-OK "pip found - $pipVer"
    } else {
        throw "pip not found"
    }
} catch {
    Write-INFO "pip not found - installing..."
    & python -m ensurepip --upgrade 2>&1 | Out-Null
    Write-OK "pip installed."
}

# ── STEP 4: Upgrade pip ──────────────────────────────────────────────────────
Write-Step "Step 4: Upgrading pip..."
& python -m pip install --upgrade pip --quiet
Write-OK "pip is up to date."

# ── STEP 5: Install requirements ─────────────────────────────────────────────
Write-Step "Step 5: Installing Python packages from requirements.txt..."
if (Test-Path "$ROOT\requirements.txt") {
    $result = & python -m pip install -r "$ROOT\requirements.txt" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-OK "All packages installed successfully."
    } else {
        Write-FAIL "Some packages failed to install:"
        Write-Host "     $result" -ForegroundColor Red
    }
} else {
    Write-FAIL "requirements.txt not found at $ROOT"
}

# ── STEP 6: Verify key imports ───────────────────────────────────────────────
Write-Step "Step 6: Verifying package imports..."
$packages = @("fastapi", "uvicorn", "jinja2", "openpyxl", "dateutil", "multipart")
foreach ($pkg in $packages) {
    $null = & python -c "import $pkg" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-OK "$pkg"
    } else {
        Write-FAIL "$pkg - import failed"
    }
}

# ── STEP 7: Create required folders ──────────────────────────────────────────
Write-Step "Step 7: Checking required folders..."
foreach ($folder in @("backup", "static", "templates", "routers")) {
    if (Test-Path "$ROOT\$folder") {
        Write-OK "Folder exists: $folder\"
    } else {
        New-Item -ItemType Directory -Path "$ROOT\$folder" -Force | Out-Null
        Write-OK "Folder created: $folder\"
    }
}

# ── STEP 8: Check application files ──────────────────────────────────────────
Write-Step "Step 8: Checking application files..."
$files = @("main.py", "database.py", "auth.py", "config.py", "requirements.txt", "start.bat")
foreach ($f in $files) {
    if (Test-Path "$ROOT\$f") {
        Write-OK "$f"
    } else {
        Write-FAIL "$f - NOT FOUND (re-clone the repository)"
    }
}

# ── STEP 9: Application startup test ─────────────────────────────────────────
Write-Step "Step 9: Running startup test (database init)..."
$rootEscaped = $ROOT -replace "\\", "\\"
$test = & python -c @"
import sys, os
sys.path.insert(0, r'$ROOT')
os.chdir(r'$ROOT')
from database import init_db
init_db()
print('STARTUP_OK')
"@ 2>&1

if ($test -match "STARTUP_OK") {
    Write-OK "Database initialised successfully."
} else {
    Write-FAIL "Startup test failed. Output: $test"
}

# ── SUMMARY ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ====================================================" -ForegroundColor Gray
if ($fail -eq 0) {
    Write-Host "  RESULT : ALL CHECKS PASSED - System is READY" -ForegroundColor Green
} else {
    Write-Host "  RESULT : $fail check(s) FAILED - Review errors above" -ForegroundColor Red
}
Write-Host "  Passed : $pass   |   Failed : $fail" -ForegroundColor White
Write-Host "  ====================================================" -ForegroundColor Gray
Write-Host ""

if ($fail -eq 0) {
    Write-Host "  Default login credentials:" -ForegroundColor Cyan
    Write-Host "    Username : admin" -ForegroundColor White
    Write-Host "    Password : admin123" -ForegroundColor White
    Write-Host ""
    $launch = Read-Host "  Launch the application now? (Y/N)"
    if ($launch -eq "Y" -or $launch -eq "y") {
        Write-Host ""
        Write-Host "  Starting Fit Zone Gym..." -ForegroundColor Green
        Start-Process python -ArgumentList "$ROOT\main.py" -WorkingDirectory $ROOT
        Write-Host "  Done. Browser will open at http://127.0.0.1:8000" -ForegroundColor Green
    }
}

Write-Host ""
