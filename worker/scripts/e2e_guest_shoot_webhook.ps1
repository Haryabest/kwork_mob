# E2E guest shoot + webhook shoot_link.uploaded on staging §3.15
param(
  [string]$ApiBase = $env:API_BASE,
  [string]$Token = $env:API_TOKEN,
  [string]$WebhookUrl = $env:WEBHOOK_URL,
  [int]$PollSec = 60
)

if (-not $ApiBase) { $ApiBase = "https://staging.3d.app/api/v1" }
if (-not $Token) { throw "Set API_TOKEN (Owner JWT)" }
if (-not $WebhookUrl) { throw "Set WEBHOOK_URL (https receiver, e.g. webhook.site)" }

$headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }
$secret = [guid]::NewGuid().ToString("N")

Write-Host "register webhook $WebhookUrl"
$whBody = @{
  url = $WebhookUrl
  events = @("shoot_link.uploaded")
  secret = $secret
} | ConvertTo-Json
$wh = Invoke-RestMethod -Method Post -Uri "$ApiBase/company/webhooks" -Headers $headers -Body $whBody
Write-Host "webhook id=$($wh.id)"

& "$PSScriptRoot\e2e_guest_shoot_api.ps1" -ApiBase $ApiBase -Token $Token

Write-Host "poll deliveries"
$deadline = (Get-Date).AddSeconds($PollSec)
do {
  Start-Sleep -Seconds 2
  $del = Invoke-RestMethod -Method Get -Uri "$ApiBase/company/webhooks/deliveries?limit=20" -Headers $headers
  $hit = @($del.items | Where-Object { $_.event -eq "shoot_link.uploaded" -and $_.ok -eq $true })
  if ($hit.Count -gt 0) {
    Write-Host "OK webhook delivered id=$($hit[0].id) status=$($hit[0].status)"
    exit 0
  }
} while ((Get-Date) -lt $deadline)

throw "shoot_link.uploaded webhook not delivered within ${PollSec}s"
