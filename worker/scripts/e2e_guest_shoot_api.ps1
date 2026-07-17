# E2E guest shoot via API §3.15 — create link → presign PUT ×12 → complete
param(
  [string]$ApiBase = $env:API_BASE,
  [string]$Token = $env:API_TOKEN,
  [string]$Category = "other",
  [string]$Tier = "small"
)

if (-not $ApiBase) { $ApiBase = "https://staging.3d.app/api/v1" }
if (-not $Token) { throw "Set API_TOKEN (Owner/Manager JWT)" }

$headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }

# minimal 1x1 JPEG
$jpegB64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGfAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAQUCf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8Bf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8Bf//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEABj8Cf//Z"
$jpegBytes = [Convert]::FromBase64String($jpegB64)

Write-Host "create shoot_link"
$body = @{
  category = $Category
  tier = $Tier
  ttl_hours = 48
  max_uses = 1
} | ConvertTo-Json
$link = Invoke-RestMethod -Method Post -Uri "$ApiBase/company/shoot_link" -Headers $headers -Body $body
$url = $link.url
if (-not $url) { throw "shoot_link response missing url" }
$token = ($url -split "/")[-1]
Write-Host "token=$token task=$($link.task_uuid)"

Write-Host "GET shoot data (guest)"
$shoot = Invoke-RestMethod -Method Get -Uri "$ApiBase/shoot/$token"
$uploads = @($shoot.uploads)
if ($uploads.Count -lt 12) { throw "expected 12 uploads, got $($uploads.Count)" }

for ($i = 0; $i -lt $uploads.Count; $i++) {
  $u = $uploads[$i]
  $putUrl = $u.upload_url
  $ct = if ($u.content_type) { $u.content_type } else { "image/jpeg" }
  Write-Host "  PUT view $($u.index) ($($u.filename))"
  Invoke-WebRequest -Method Put -Uri $putUrl -Body $jpegBytes -ContentType $ct -UseBasicParsing | Out-Null
}

Write-Host "complete shoot"
$done = Invoke-RestMethod -Method Post -Uri "$ApiBase/shoot/$token/complete"
if (-not $done.ok) { throw "complete failed: $($done | ConvertTo-Json -Compress)" }
Write-Host "OK guest shoot E2E status=$($done.status) task=$($done.task_uuid)"
exit 0
