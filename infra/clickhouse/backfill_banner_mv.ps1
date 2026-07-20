# Backfill mobile_analytics_banner_daily on existing ClickHouse §19.20
param(
  [string]$ChHost = $env:CLICKHOUSE_HOST,
  [int]$ChPort = $(if ($env:CLICKHOUSE_PORT) { [int]$env:CLICKHOUSE_PORT } else { 8123 }),
  [string]$ChUser = $env:CLICKHOUSE_USER,
  [string]$ChPassword = $env:CLICKHOUSE_PASSWORD,
  [string]$ChDb = $(if ($env:CLICKHOUSE_DB) { $env:CLICKHOUSE_DB } else { "kwork_metrics" })
)

if (-not $ChHost) { $ChHost = "localhost" }
if (-not $ChUser) { $ChUser = "default" }

$sqlPath = Join-Path $PSScriptRoot "backfill_mobile_analytics_banner_daily.sql"
$sql = Get-Content $sqlPath -Raw -Encoding UTF8
$uri = "http://${ChHost}:${ChPort}/?database=$ChDb"

Write-Host "backfill mobile_analytics_banner_daily -> $uri"
$headers = @{}
if ($ChPassword) {
  $pair = "${ChUser}:${ChPassword}"
  $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
  $headers["Authorization"] = "Basic $b64"
}

Invoke-WebRequest -Method Post -Uri $uri -Body $sql -Headers $headers -UseBasicParsing | Out-Null
Write-Host "OK backfill complete"
exit 0
