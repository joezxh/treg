$ErrorActionPreference = "Continue"
$ROOT = "d:/projects/github/treg"
$keysFile = Join-Path $ROOT "scripts/.dev-home/dev-keys.env"
if (Test-Path $keysFile) {
  Get-Content $keysFile | ForEach-Object {
    if ($_ -match '^([^=#][^=]*)=(.*)$') {
      [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
  }
}
$env:TREG_EMAIL_DEV_MODE = "true"
$env:TREG_FRONTEND_DEV = "true"
$env:TREG_PUBLIC_URL = "http://localhost:18790"
$env:TREG_CONNECT_DEMO_ENABLED = "true"
$env:TREG_DATABASE_URL = "sqlite+aiosqlite:///d:/projects/github/treg/treg-dev.db"

Set-Location $ROOT
& uv run --no-sync python -m treg --reload
