$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$cliRoot = Join-Path $projectRoot "tools\render-cli"
$env:RENDER_CLI_CONFIG_PATH = Join-Path $cliRoot "cli.yaml"

& (Join-Path $cliRoot "render.exe") login
if ($LASTEXITCODE -ne 0) {
    throw "Render CLI login failed with exit code $LASTEXITCODE"
}

Write-Host "Render CLI authorization completed. You may close this window."
Read-Host "Press Enter to close"
