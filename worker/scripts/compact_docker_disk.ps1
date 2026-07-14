# Compact docker_data.vhdx after removing large Docker images.
# Run as Administrator:
#   cd D:\projects\kwork_mob\worker\scripts
#   .\compact_docker_disk.ps1

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error 'Run PowerShell as Administrator'
}

$vhdx = Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx'
if (-not (Test-Path -LiteralPath $vhdx)) {
    Write-Error "Not found: $vhdx"
}

$vhdxFull = (Resolve-Path -LiteralPath $vhdx).Path

# DiskPart breaks on Cyrillic user profile paths — use 8.3 short path.
$fso = New-Object -ComObject Scripting.FileSystemObject
$vhdxDiskPart = $fso.GetFile($vhdxFull).ShortPath
if (-not $vhdxDiskPart) {
    $vhdxDiskPart = $vhdxFull
}

Write-Host "VHDX: $vhdxFull"
Write-Host "DiskPart path: $vhdxDiskPart"
Write-Host 'Stopping Docker...'
Stop-Process -Name 'Docker Desktop', 'com.docker.backend' -Force -ErrorAction SilentlyContinue
Start-Sleep 3
wsl --shutdown
Start-Sleep 3

$before = (Get-Item -LiteralPath $vhdxFull).Length
Write-Host ('Size before: {0:N2} GB' -f ($before / 1GB))

$diskpartScript = @"
select vdisk file="$vhdxDiskPart"
attach vdisk readonly
compact vdisk
detach vdisk
exit
"@
$scriptFile = Join-Path $env:TEMP 'docker_compact_diskpart.txt'
Set-Content -Path $scriptFile -Value $diskpartScript -Encoding ASCII
Write-Host "Running diskpart /s $scriptFile"
diskpart /s $scriptFile | Out-Host
Remove-Item -LiteralPath $scriptFile -Force -ErrorAction SilentlyContinue

$after = (Get-Item -LiteralPath $vhdxFull).Length
$saved = $before - $after
Write-Host ('Size after:  {0:N2} GB' -f ($after / 1GB))
Write-Host ('Freed:       {0:N2} GB' -f ($saved / 1GB))

if ($saved -lt 1GB) {
    Write-Host ''
    Write-Host 'DiskPart compact did not shrink the file. Try:'
    Write-Host '  1. Docker Desktop -> Troubleshoot -> Clean / Purge data'
    Write-Host '  2. Or Settings -> Resources -> Advanced -> Disk image -> Reclaim space'
    Write-Host ''
    if (Get-Command Optimize-VHD -ErrorAction SilentlyContinue) {
        Write-Host 'Trying Optimize-VHD...'
        Optimize-VHD -Path $vhdxFull -Mode Full
        $after2 = (Get-Item -LiteralPath $vhdxFull).Length
        Write-Host ('After Optimize-VHD: {0:N2} GB (freed {1:N2} GB)' -f ($after2 / 1GB), (($after - $after2) / 1GB))
    }
}

Write-Host 'Start Docker Desktop again.'
