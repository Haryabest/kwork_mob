# E2E cloud restore smoke — presigned ZIP §9.1.3
param(
  [string]$ApiBase = $env:API_BASE,
  [string]$Token = $env:API_TOKEN,
  [string]$ModelUuid = $env:MODEL_UUID
)

if (-not $ApiBase) { $ApiBase = "http://localhost:8000/api/v1" }
if (-not $Token) { throw "Set API_TOKEN (JWT)" }
if (-not $ModelUuid) { throw "Set MODEL_UUID" }

$headers = @{ Authorization = "Bearer $Token" }

Write-Host "POST restore-sources for $ModelUuid"
$prep = Invoke-RestMethod -Method Post -Uri "$ApiBase/models/$ModelUuid/restore-sources" -Headers $headers
$url = $prep.download_url
if (-not $url) { throw "No download_url in response" }

Write-Host "GET presigned ZIP"
$resp = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing
if ($resp.StatusCode -lt 200 -or $resp.StatusCode -ge 300) {
  throw "ZIP download failed: $($resp.StatusCode)"
}

$bytes = $resp.RawContentLength
Write-Host "OK cloud restore smoke: $bytes bytes"
exit 0
