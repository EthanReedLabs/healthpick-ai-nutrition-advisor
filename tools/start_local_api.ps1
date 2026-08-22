[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8010
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project virtual environment is missing: $python"
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port $Port is already in use by PID $($listener.OwningProcess)."
}

$env:WEB_ORIGIN = "http://127.0.0.1:3100"
$env:DATABASE_URL = "postgresql://healthpick:healthpick-local-only@127.0.0.1:54329/healthpick"
$env:CONVERSATION_STORE_MODE = "postgres"
$env:LLM_MODE = "real"
$env:LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:LLM_API_KEY = "ollama-local-only"
$env:LLM_MODEL = "qwen2.5:3b-instruct"
$env:EMBEDDING_MODE = "real"
$env:EMBEDDING_BASE_URL = "http://127.0.0.1:11434/v1"
$env:EMBEDDING_API_KEY = "ollama-local-only"
$env:EMBEDDING_MODEL = "qwen3-embedding:0.6b"
$env:EMBEDDING_DIMENSIONS = "1024"

$process = Start-Process `
    -FilePath $python `
    -ArgumentList @(
        "-m", "uvicorn", "healthpick_api.main:app",
        "--app-dir", "apps/api",
        "--host", "127.0.0.1",
        "--port", $Port
    ) `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

[pscustomobject]@{
    Status = "STARTED"
    PID = $process.Id
    Origin = "http://127.0.0.1:$Port"
    Model = $env:LLM_MODEL
    Embedding = $env:EMBEDDING_MODEL
    Database = "127.0.0.1:54329/healthpick"
}
