#Requires -Version 5.1
<#
.SYNOPSIS
  Domashniy GPU E2E TRELLIS (TZ KPI <=3 min local).

.EXAMPLE
  .\run_e2e_home.ps1 -PhotosDir D:\samples\dome12
  .\run_e2e_home.ps1 -PhotosDir D:\samples\dome12 -UseDocker
  .\run_e2e_home.ps1 -PhotosDir D:\samples\dome12 -HostPython
#>
param(
  [Parameter(Mandatory = $true)][string]$PhotosDir,
  [string]$WorkDir = "",
  [switch]$WithUpsells,
  [switch]$KeepWorkdir,
  [switch]$UseDocker,
  [switch]$HostPython,
  [string]$DockerImage = "kwork-worker:trellis2"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $Root "worker"))) {
  $Root = Split-Path $PSScriptRoot -Parent
}

$env:WORKER_DEPLOY = "local"
$env:WORKER_PIPELINE_MODE = "trellis"
$env:TRELLIS_VERSION = "2"
$env:TRELLIS_WEIGHTS = "microsoft/TRELLIS.2-4B"
$env:TRELLIS2_PIPELINE_TYPE = "512"
$env:TRELLIS2_LOW_VRAM = "1"
$env:ATTN_BACKEND = "xformers"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"
$env:TRELLIS_ALLOW_STUB_FALLBACK = "0"
$env:WORKER_FORCE_REAL_NOBG = "1"
if ($KeepWorkdir) { $env:E2E_KEEP_WORKDIR = "1" }

$script = Join-Path $Root "worker\scripts\e2e_trellis_acceptance.py"
$e2eArgs = @(
  "--photos", $PhotosDir,
  "--fail-on-budget",
  "--preflight"
)
if ($WorkDir) { $e2eArgs += @("--workdir", $WorkDir) }
if ($WithUpsells) { $e2eArgs += "--with-upsells" }

Write-Host "[e2e-home] ROOT=$Root photos=$PhotosDir"

$imageOk = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker image inspect $DockerImage 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $imageOk = $true }
}

$runDocker = (-not $HostPython) -and ($UseDocker -or $imageOk)

if ($runDocker) {
  if (-not $imageOk) {
    Write-Error "Docker image '$DockerImage' not found. Build: docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 --build-arg TRELLIS_VERSION=2 -t $DockerImage worker"
  }
  $photosPath = (Resolve-Path -LiteralPath $PhotosDir).Path
  $reportsDir = Join-Path $Root "worker\e2e_reports"
  New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

  Write-Host "[e2e-home] mode=docker image=$DockerImage"
  $dockerArgs = @(
    "run", "--rm", "--gpus", "all",
    "-v", "${photosPath}:/photos:ro",
    "-v", "${reportsDir}:/app/e2e_reports",
    "-e", "WORKER_DEPLOY=local",
    "-e", "WORKER_PIPELINE_MODE=trellis",
    "-e", "TRELLIS_VERSION=2",
    "-e", "TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B",
    "-e", "TRELLIS2_PIPELINE_TYPE=512",
    "-e", "TRELLIS2_LOW_VRAM=1",
    "-e", "ATTN_BACKEND=xformers",
    "-e", "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True",
    "-e", "TRELLIS_ALLOW_STUB_FALLBACK=0",
    "-e", "WORKER_FORCE_REAL_NOBG=1",
    "-e", "E2E_REPORT_DIR=/app/e2e_reports"
  )
  if ($KeepWorkdir) { $dockerArgs += "-e", "E2E_KEEP_WORKDIR=1" }
  if ($WorkDir) {
    $workPath = (Resolve-Path -LiteralPath $WorkDir).Path
    $dockerArgs += @("-v", "${workPath}:/work")
    $e2eArgs = @("--photos", "/photos", "--fail-on-budget", "--preflight", "--workdir", "/work")
    if ($WithUpsells) { $e2eArgs += "--with-upsells" }
  } else {
    $e2eArgs = @("--photos", "/photos", "--fail-on-budget", "--preflight")
    if ($WithUpsells) { $e2eArgs += "--with-upsells" }
  }
  $dockerArgs += @($DockerImage, "python3", "/app/scripts/e2e_trellis_acceptance.py")
  $dockerArgs += $e2eArgs
  & docker @dockerArgs
  exit $LASTEXITCODE
}

Write-Host "[e2e-home] mode=host-python (use -UseDocker for GPU; host needs CUDA torch + worker/trellis)"
$argsList = @($script) + $e2eArgs
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 @argsList
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python @argsList
} else {
  Write-Error "Python not found. Wait for docker build, then: .\worker\scripts\run_e2e_home.ps1 -PhotosDir $PhotosDir -UseDocker"
}
exit $LASTEXITCODE
