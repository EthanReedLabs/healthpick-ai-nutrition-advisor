param(
    [string]$EvidencePath = "docs/evidence/action-01-database-runtime.json",
    [int]$ReadyTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$capturedAt = [DateTimeOffset]::Now.ToString("o")
$deadline = [DateTimeOffset]::Now.AddSeconds($ReadyTimeoutSeconds)
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "healthpick" }
$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "healthpick" }
$containerId = (& docker compose ps -q postgres).Trim()
if (-not $containerId) {
    throw "postgres container is not present; run docker compose up -d postgres"
}

$health = ""
do {
    $health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $containerId).Trim()
    if ($health -eq "healthy") {
        break
    }
    Start-Sleep -Seconds 2
} while ([DateTimeOffset]::Now -lt $deadline)

if ($health -ne "healthy") {
    throw "postgres container did not become healthy; final state=$health"
}

$probeSql = @"
SELECT json_build_object(
  'database', current_database(),
  'server_version', current_setting('server_version'),
  'pgcrypto_version', (SELECT extversion FROM pg_extension WHERE extname = 'pgcrypto'),
  'vector_version', (SELECT extversion FROM pg_extension WHERE extname = 'vector'),
  'knowledge_tables', (
    SELECT count(*)
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name LIKE 'knowledge_%'
  ),
  'embedding_column_type', (
    SELECT format_type(a.atttypid, a.atttypmod)
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    WHERE c.relname = 'knowledge_chunks' AND a.attname = 'embedding'
  ),
  'embedding_index_present', to_regclass('public.knowledge_chunks_embedding_hnsw_idx') IS NOT NULL
)::text;
"@

$result = (& docker compose exec -T postgres psql `
    -v ON_ERROR_STOP=1 `
    -U $dbUser `
    -d $dbName `
    -Atc $probeSql).Trim()

if (-not $result) {
    throw "database probe returned no result"
}

$probe = $result | ConvertFrom-Json
if (
    -not $probe.pgcrypto_version `
    -or -not $probe.vector_version `
    -or $probe.knowledge_tables -lt 4 `
    -or $probe.embedding_column_type -ne "vector(1024)" `
    -or -not $probe.embedding_index_present
) {
    throw "database probe did not satisfy extension/table requirements"
}

$evidence = [ordered]@{
    schema_version = 1
    evidence_id = "ACTION-01-DB-RUNTIME"
    action_id = "ACTION-01"
    scope = "compose/postgresql/pgvector"
    captured_at = $capturedAt
    compose_project = "healthpick"
    container_id = $containerId
    health = $health
    database = $probe.database
    server_version = $probe.server_version
    pgcrypto_version = $probe.pgcrypto_version
    vector_version = $probe.vector_version
    knowledge_tables = [int]$probe.knowledge_tables
    embedding_column_type = $probe.embedding_column_type
    embedding_index_present = [bool]$probe.embedding_index_present
    migration_001_sha256 = (Get-FileHash "infra/migrations/001_knowledge_base.sql" -Algorithm SHA256).Hash.ToLowerInvariant()
    status = "PASS"
}

$evidenceDirectory = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
$evidence | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 $EvidencePath
$evidence | ConvertTo-Json -Depth 4
