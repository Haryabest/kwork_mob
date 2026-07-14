#Requires -Version 5.1
<#
.SYNOPSIS
  Домашний GPU E2E TRELLIS по ТЗ (§1 KPI ≤3 мин local).

.EXAMPLE
  .\run_e2e_home.ps1 -PhotosDir D:\samples\dome12
#>
param(
  [Parameter(Mandatory = $true)][string]$PhotosDir,
  [string]$WorkDir = "",
  [switch]$WithUpsells,
  [switch]$KeepWorkdir
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

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } else { "python" }
$script = Join-Path $Root "worker\scripts\e2e_trellis_acceptance.py"

$argsList = @(
  $script,
  "--photos", $PhotosDir,
  "--fail-on-budget",
  "--preflight"
)
if ($WorkDir) { $argsList += @("--workdir", $WorkDir) }
if ($WithUpsells) { $argsList += "--with-upsells" }

Write-Host "[e2e-home] ROOT=$Root photos=$PhotosDir"
& $py @argsList
exit $LASTEXITCODE
