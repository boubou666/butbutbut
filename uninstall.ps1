<#
.SYNOPSIS
    Desinstalle butbutbut (Windows). Ne touche pas a tes sons perso sauf -Purge.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
    powershell -ExecutionPolicy Bypass -File .\uninstall.ps1 -Purge
#>
[CmdletBinding()]
param([switch] $Purge)

$ErrorActionPreference = 'Stop'

function Write-Head { param($Text) Write-Host "`n$Text" -ForegroundColor White }
function Write-Item { param($Text) Write-Host "  $Text" }

Write-Head 'butbutbut - desinstallation'

$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\butbutbut'
$AppDir     = Join-Path $InstallDir 'app'
$BinDir     = Join-Path $InstallDir 'bin'
$DataDir    = Join-Path $env:LOCALAPPDATA 'butbutbut'
$lnkPath    = Join-Path ([Environment]::GetFolderPath('Startup')) 'butbutbut.lnk'

# --- daemon en cours
$cmd = Join-Path $BinDir 'butbutbut.cmd'
if (Test-Path $cmd) {
    & $cmd --stop 2>$null | Out-Null
    Write-Item 'daemon      : arrete'
}

# --- demarrage automatique
if (Test-Path $lnkPath) {
    Remove-Item $lnkPath -Force
    Write-Item 'raccourci   : retire du demarrage'
}

# --- code et commandes
if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
    Write-Item "code        : $InstallDir supprime"
}

# --- PATH et PYTHONPATH utilisateur
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -and $userPath -like "*$BinDir*") {
    $cleaned = ($userPath -split ';' | Where-Object { $_ -and $_ -ne $BinDir }) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $cleaned, 'User')
    Write-Item 'PATH        : nettoye'
}

$envPyPath = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'User')
if ($envPyPath -and $envPyPath -like "*$AppDir*") {
    $cleaned = ($envPyPath -split ';' | Where-Object { $_ -and $_ -ne $AppDir }) -join ';'
    if ($cleaned) {
        [Environment]::SetEnvironmentVariable('PYTHONPATH', $cleaned, 'User')
    } else {
        [Environment]::SetEnvironmentVariable('PYTHONPATH', $null, 'User')
    }
    Write-Item 'PYTHONPATH  : nettoye'
}

# --- donnees
if ($Purge) {
    if (Test-Path $DataDir) {
        Remove-Item $DataDir -Recurse -Force
        Write-Item "donnees     : $DataDir supprime"
    }
} elseif (Test-Path $DataDir) {
    Write-Item "donnees     : $DataDir conserve (sons perso, journal)"
    Write-Item '  -> relance avec -Purge pour tout supprimer'
}

Write-Head 'Termine'
Write-Item 'Rouvre ton terminal pour que le PATH soit a jour.'
