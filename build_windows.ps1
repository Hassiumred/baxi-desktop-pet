$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$AppName = "BaxiPet-v0.9-hotfix5-sourceprep2"
$LogPath = Join-Path $PSScriptRoot "build_error.log"
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Program" }
}
try {
    if (Test-Path $LogPath) { Remove-Item $LogPath -Force }
    Invoke-Checked "py" @("-3", "tools/check_asset_presence.py")
    Invoke-Checked "py" @("-3", "-m", "venv", ".venv-build")
    $Python = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
    Invoke-Checked $Python @("-m", "pip", "install", "-r", "requirements-build.txt")
    Invoke-Checked $Python @("tools/validate_baxi_assets.py")
    Invoke-Checked $Python @("-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--name", $AppName, "--paths", "app", "--add-data", "app\assets;assets", "app\main.py")
    $ExePath = Join-Path $PSScriptRoot "dist\$AppName\$AppName.exe"
    if (!(Test-Path $ExePath)) { throw "EXE not found: $ExePath" }
    Write-Host "Built for local testing only: $ExePath. Dependency and asset redistribution review still required."
}
catch {
    $_ | Out-String | Set-Content -LiteralPath $LogPath -Encoding UTF8
    Write-Error -ErrorAction Continue "Build failed; see build_error.log"
    exit 1
}
