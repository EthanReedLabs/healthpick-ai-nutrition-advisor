param(
    [int]$Port = 8010,
    [string]$OutputPath = "docs/evidence/phase-03-api-runtime.json"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$outputAbsolute = Join-Path $projectRoot $OutputPath
$apiOrigin = "http://127.0.0.1:$Port"

$env:APP_ENV = "test"
$env:LLM_MODE = "mock"
$env:LLM_MODEL = "mock-healthpick-v1"
$env:EMBEDDING_MODE = "disabled"
$env:RETRIEVAL_MODE = "keyword"

$process = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList @(
        "-m", "uvicorn", "healthpick_api.main:app",
        "--app-dir", "apps/api",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--log-level", "warning"
    ) `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    $healthResponse = $null
    for ($attempt = 1; $attempt -le 40; $attempt++) {
        try {
            $healthResponse = Invoke-WebRequest -Uri "$apiOrigin/healthz" -TimeoutSec 2
            break
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if ($null -eq $healthResponse) {
        throw "API did not become healthy within 10 seconds"
    }

    $openapiResponse = Invoke-WebRequest -Uri "$apiOrigin/openapi.json" -TimeoutSec 5
    $chatResponse = Invoke-WebRequest `
        -Uri "$apiOrigin/v1/chat/stream" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"conversation_id":"smoke","message":"膳食纤维有什么营养作用？"}' `
        -SkipHttpErrorCheck `
        -TimeoutSec 5

    $health = $healthResponse.Content | ConvertFrom-Json
    $openapi = $openapiResponse.Content | ConvertFrom-Json
    $eventNames = @(
        [regex]::Matches($chatResponse.Content, '(?m)^event: ([^\r\n]+)$') |
            ForEach-Object { $_.Groups[1].Value }
    )
    $finalBlock = @(
        $chatResponse.Content -split '(?:\r?\n){2}' |
            Where-Object { $_ -match '(?m)^event: final$' }
    )
    if ($finalBlock.Count -ne 1) { throw "SSE final event count mismatch" }
    $finalData = [regex]::Match($finalBlock[0], '(?m)^data: (.+)$').Groups[1].Value
    $chat = $finalData | ConvertFrom-Json
    if ($health.status -ne "ok") { throw "health status is not ok" }
    if ($health.modes.llm -ne "mock") { throw "smoke process did not expose mock mode" }
    if ($chatResponse.StatusCode -ne 200) { throw "chat SSE did not return 200" }
    if ($chatResponse.Headers.'Content-Type' -notlike 'text/event-stream*') { throw "chat is not SSE" }
    if ($eventNames[0] -ne 'meta' -or $eventNames[-1] -ne 'final') { throw "SSE event order mismatch" }
    if ($chat.model.mode -ne 'mock') { throw "SSE final did not disclose mock mode" }
    if ($chat.answer -notlike '[[]MOCK RESPONSE*') { throw "SSE final lacks mock disclosure" }
    if (@($chat.citations).Count -lt 1) { throw "SSE final has no citations" }

    $report = [ordered]@{
        schema_version = 1
        captured_at = (Get-Date).ToString("o")
        scope = "phase-03-p03-01-and-p03-05-local-uvicorn"
        environment = "test"
        api_origin = $apiOrigin
        health = [ordered]@{
            status_code = $healthResponse.StatusCode
            status = $health.status
            service = $health.service
            version = $health.version
            request_id = $health.request_id
            modes = $health.modes
            dependencies = $health.dependencies
        }
        openapi = [ordered]@{
            status_code = $openapiResponse.StatusCode
            version = $openapi.info.version
            path_count = @($openapi.paths.PSObject.Properties).Count
            has_health = $null -ne $openapi.paths.'/healthz'
            has_chat = $null -ne $openapi.paths.'/v1/chat/stream'
        }
        chat_sse = [ordered]@{
            status_code = $chatResponse.StatusCode
            content_type = $chatResponse.Headers.'Content-Type'
            event_names = $eventNames
            request_id = $chat.request_id
            route = $chat.route
            model = $chat.model
            citation_count = @($chat.citations).Count
            sources = @($chat.citations | ForEach-Object { $_.source } | Sort-Object -Unique)
            explicit_mock_disclosure = $chat.answer -like '[[]MOCK RESPONSE*'
        }
        result = "PASS"
    }
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputAbsolute -Encoding utf8
    Write-Output "API runtime smoke PASS -> $outputAbsolute"
}
finally {
    if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
        Stop-Process -Id $process.Id -Force
    }
}
