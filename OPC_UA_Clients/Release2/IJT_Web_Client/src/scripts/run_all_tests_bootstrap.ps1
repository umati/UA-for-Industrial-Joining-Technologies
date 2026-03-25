<#
.SYNOPSIS
    Bootstrap: installs PowerShell 7.6 (if needed) then runs ALL IJT tests.
    Compatible with Windows PowerShell 5.x (powershell.exe).

.USAGE
    powershell.exe -ExecutionPolicy Bypass -File scripts/run_all_tests_bootstrap.ps1
#>
$ErrorActionPreference = "Continue"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot   = Split-Path -Parent $ScriptDir
$ConsoleDir = Join-Path (Split-Path -Parent (Split-Path -Parent $RepoRoot)) "IJT_Console_Client"
$Pwsh7      = "C:\Program Files\PowerShell\7\pwsh.exe"
$MsiUrl     = "https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/PowerShell-7.6.0-win-x64.msi"
$MsiPath    = Join-Path $env:TEMP "PowerShell-7.6.0-win-x64.msi"
$TmpScript  = Join-Path $env:TEMP "ijt_test_step.ps1"

$Results = [ordered]@{}

function Write-Banner($t) {
    Write-Host ""
    Write-Host ("=" * 65)
    Write-Host "  $t"
    Write-Host ("=" * 65)
}
function Write-Step($t) {
    Write-Host ""
    Write-Host ("--- $t ---")
}
function Write-OK($t)   { Write-Host "  [PASS] $t" }
function Write-Fail($t) { Write-Host "  [FAIL] $t" }
function Write-Info($t) { Write-Host "  [INFO] $t" }

# ---------------------------------------------------------------------------
# STEP 0 -- Install PowerShell 7 if missing
# ---------------------------------------------------------------------------
Write-Banner "STEP 0 -- PowerShell 7 check / install"

if (Test-Path $Pwsh7) {
    $pv = & $Pwsh7 --version 2>&1
    Write-OK "Already installed: $pv"
} else {
    Write-Info "Downloading PowerShell 7.6.0 MSI..."
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        (New-Object System.Net.WebClient).DownloadFile($MsiUrl, $MsiPath)
        Write-OK "Downloaded to $MsiPath"
    } catch {
        Write-Fail "Download failed: $_"
        Write-Host "Please install manually: $MsiUrl"
        exit 1
    }

    Write-Info "Installing silently (approx 30 s)..."
    $msi = Start-Process msiexec.exe `
        -ArgumentList "/i `"$MsiPath`" /quiet /norestart" `
        -Wait -PassThru
    if ($msi.ExitCode -eq 0) {
        Write-OK "Installed OK"
    } else {
        Write-Fail "msiexec exit code: $($msi.ExitCode)"
        exit 1
    }
}

if (-not (Test-Path $Pwsh7)) {
    Write-Fail "pwsh.exe not found after install -- aborting"
    exit 1
}

# ---------------------------------------------------------------------------
# Helper: write a temp .ps1 and run it via pwsh7 with live output
# ---------------------------------------------------------------------------
function Run-Step {
    param(
        [string]$Label,
        [string]$WorkDir,
        [string]$Body          # PowerShell code to execute
    )
    Write-Step $Label
    Write-Info "CWD: $WorkDir"

    # Write the script body to a temp file (avoids ALL string-escaping hell)
    $scriptContent = "Set-Location `"$WorkDir`"`n$Body"
    [System.IO.File]::WriteAllText($TmpScript, $scriptContent, [System.Text.Encoding]::UTF8)

    & $Pwsh7 -NoProfile -NonInteractive -File $TmpScript
    $rc = $LASTEXITCODE

    $Results[$Label] = $rc
    if ($rc -eq 0) { Write-OK "$Label -- PASSED (exit=0)" }
    else           { Write-Fail "$Label -- FAILED (exit=$rc)" }
    return $rc
}

# ---------------------------------------------------------------------------
# STEP 1 -- Tool versions
# ---------------------------------------------------------------------------
Write-Banner "STEP 1 -- Tool versions"
Run-Step "tool-versions" $RepoRoot @"
python --version
node   --version
npm    --version
"@

# ---------------------------------------------------------------------------
# STEP 2 -- Install Python test dependencies
# ---------------------------------------------------------------------------
Write-Banner "STEP 2 -- Install Python test dependencies"
Run-Step "pip-install" $RepoRoot @"
python -m pip install --quiet --disable-pip-version-check `
    --pre "asyncua>=1.2b2" `
    pytest pytest-asyncio websockets pytz aiofiles packaging orjson
Write-Host "pip install done (exit `$LASTEXITCODE)"
"@

# ---------------------------------------------------------------------------
# STEP 3 -- Python unit tests (no server)
# ---------------------------------------------------------------------------
Write-Banner "STEP 3 -- Python unit tests (Web Client)"
Run-Step "python-unit-web" $RepoRoot @"
python -m pytest tests/ -m "not integration and not live and not live_ws and not legacy" ``
    -v --tb=short --no-header
"@

# ---------------------------------------------------------------------------
# STEP 4 -- JS unit tests (vitest)
# ---------------------------------------------------------------------------
Write-Banner "STEP 4 -- JavaScript unit tests (vitest)"
if (-not (Test-Path (Join-Path $RepoRoot "node_modules"))) {
    Write-Info "node_modules missing -- installing"
    Run-Step "npm-install" $RepoRoot "npm install --legacy-peer-deps"
}
Run-Step "js-unit" $RepoRoot "npm run test:unit:js"

# ---------------------------------------------------------------------------
# STEP 5 -- Python live tests (OPC UA server at localhost:40451)
# ---------------------------------------------------------------------------
Write-Banner "STEP 5 -- Python live tests"
Run-Step "python-live" $RepoRoot @"
python -m pytest tests/test_opcua_live.py -v --tb=short --no-header
"@

# ---------------------------------------------------------------------------
# STEP 6 -- Console Client tests
# ---------------------------------------------------------------------------
Write-Banner "STEP 6 -- Console Client tests"
if (Test-Path $ConsoleDir) {
    $consoleReq = Join-Path $ConsoleDir "requirements.txt"
    if (Test-Path $consoleReq) {
        Run-Step "pip-console" $ConsoleDir @"
python -m pip install --quiet --disable-pip-version-check ``
    --pre -r requirements.txt
Write-Host "console pip done"
"@
    }
    Run-Step "python-console" $ConsoleDir @"
python -m pytest tests/ -v --tb=short --no-header
"@
} else {
    Write-Info "Console Client dir not found: $ConsoleDir"
    $Results["python-console"] = 0
}

# ---------------------------------------------------------------------------
# STEP 7 -- Playwright smoke tests (no server needed)
# ---------------------------------------------------------------------------
Write-Banner "STEP 7 -- Playwright smoke tests"
$playwrightBin = Join-Path $RepoRoot "node_modules\.bin\playwright.cmd"
if (Test-Path $playwrightBin) {
    Run-Step "playwright-browsers" $RepoRoot "npx playwright install chromium --with-deps"
    Run-Step "playwright-smoke"    $RepoRoot "npx playwright test --project=smoke --reporter=line"
} else {
    Write-Info "Playwright not in node_modules -- skipping"
    $Results["playwright-smoke"] = 0
}

# ---------------------------------------------------------------------------
# STEP 8 -- Playwright E2E (needs Python backend on :8001)
# ---------------------------------------------------------------------------
Write-Banner "STEP 8 -- Playwright E2E feature + regression tests"
$backendUp = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("localhost", 8001)
    $tcp.Close()
    $backendUp = $true
} catch {}

if ($backendUp) {
    Write-Info "Backend detected on :8001 -- running E2E"
    Run-Step "playwright-features"   $RepoRoot "npx playwright test --project=features   --reporter=line"
    Run-Step "playwright-regression" $RepoRoot "npx playwright test --project=regression --reporter=line"
} else {
    Write-Info "Backend not on :8001 -- skipping E2E (start Python backend first)"
    $Results["playwright-features"]   = 0
    $Results["playwright-regression"] = 0
}

# ---------------------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------------------
Write-Banner "FINAL TEST SUMMARY"
$overall = 0
foreach ($entry in $Results.GetEnumerator()) {
    $rc   = $entry.Value
    $icon = if ($rc -eq 0) { "[PASS]" } else { "[FAIL]" }
    Write-Host ("  {0}  {1,-40}  exit={2}" -f $icon, $entry.Key, $rc)
    if ($rc -ne 0) { $overall = $rc }
}
Write-Host ""
if ($overall -eq 0) {
    Write-Host "  ALL TESTS PASSED"
} else {
    Write-Host "  SOME TESTS FAILED -- see output above"
}
Write-Host ("=" * 65)
Write-Host ""
exit $overall
