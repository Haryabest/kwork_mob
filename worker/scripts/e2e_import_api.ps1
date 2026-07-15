# E2E import via API §6.10 — prepare → PUT → import → poll order
param(
  [Parameter(Mandatory = $true)][string]$GlbPath,
  [string]$ApiBase = $env:API_BASE,
  [string]$Token = $env:API_TOKEN,
  [string]$Category = "other",
  [int]$PollSec = 120
)

if (-not $ApiBase) { $ApiBase = "http://localhost:8000/api/v1" }
if (-not $Token) { throw "Set API_TOKEN (Owner JWT)" }
if (-not (Test-Path $GlbPath)) { throw "GLB not found: $GlbPath" }

$headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }

Write-Host "prepare import"
$prep = Invoke-RestMethod -Method Post -Uri "$ApiBase/models/import/prepare" -Headers $headers
$bytes = [IO.File]::ReadAllBytes($GlbPath)
Invoke-WebRequest -Method Put -Uri $prep.upload_url -Body $bytes -ContentType "model/gltf-binary" -UseBasicParsing | Out-Null

Write-Host "import model"
$body = @{
  glb_key = $prep.key
  company_id = $prep.company_id
  model_uuid = $prep.model_uuid
  category = $Category
  display_name = "E2E import"
} | ConvertTo-Json
$imp = Invoke-RestMethod -Method Post -Uri "$ApiBase/models/import" -Headers $headers -Body $body

$orderId = $imp.order_id
$uuid = $imp.uuid
Write-Host "order=$orderId uuid=$uuid status=$($imp.status)"

$deadline = (Get-Date).AddSeconds($PollSec)
do {
  Start-Sleep -Seconds 3
  $ord = Invoke-RestMethod -Method Get -Uri "$ApiBase/orders/$orderId" -Headers $headers
  Write-Host "  order status: $($ord.status)"
  if ($ord.status -in @("completed", "failed", "blocked_nsfw", "cancelled")) { break }
} while ((Get-Date) -lt $deadline)

if ($ord.status -ne "completed") { throw "Import order not completed: $($ord.status)" }

Write-Host "thumbnail check"
Invoke-WebRequest -Method Get -Uri "$ApiBase/models/$uuid/thumbnail" -Headers $headers -UseBasicParsing | Out-Null
Write-Host "OK import E2E"
exit 0
