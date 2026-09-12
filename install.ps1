<#
.SYNOPSIS
    Installe butbutbut pour l'utilisateur courant (Windows 10/11). Pas besoin d'admin.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -NoAutostart
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -Leagues "l1,pl" -Position top-right

.NOTES
    Les options passees ici sont notees dans install.json, au chaud dans
    %LOCALAPPDATA%\butbutbut, et `butbutbut --update` les rejoue telles
    quelles. Celles qu'on ne passe pas ne sont pas posees non plus dans le
    raccourci de demarrage : le fichier de configuration reste alors maitre
    de ces reglages.
#>
[CmdletBinding()]
# Vides tant qu'on ne les a pas recus. Materialiser un defaut en argument du
# raccourci ecraserait silencieusement la meme cle du fichier de configuration,
# que la ligne de commande l'emporte toujours sur le fichier.
param(
    [string] $Leagues  = '',
    [string] $Position = '',
    [int]    $Interval = 0,
    [switch] $NoAutostart
)

$ErrorActionPreference = 'Stop'

function Write-Head { param($Text) Write-Host "`n$Text" -ForegroundColor White }
function Write-Item { param($Text) Write-Host "  $Text" }

# Lance python en silence et rend son code de sortie.
#
# Deux pieges de PowerShell 5.1 evites ici :
#   - `2>$null` sur un exe natif emballe chaque ligne d'erreur dans un
#     ErrorRecord et, avec ErrorActionPreference = Stop, fait echouer le script
#     alors que python n'a rien de casse : on redirige donc dans le pipeline ;
#   - les guillemets doubles internes sont manges au passage vers l'exe : le
#     code python n'en contient aucun, ce qui varie passe par argv.
function Invoke-PythonQuiet {
    param(
        [Parameter(Mandatory = $true)][string] $Exe,
        [Parameter(Mandatory = $true)][string] $Code,
        [string[]] $Extra = @()
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $callArgs = @('-c', $Code) + $Extra
        & $Exe @callArgs 2>&1 | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
}

Write-Head 'butbutbut - installation'

$Src        = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\butbutbut'
$AppDir     = Join-Path $InstallDir 'app'
$BinDir     = Join-Path $InstallDir 'bin'

# Seul --quiet est pose sans condition : un daemon de session ecrit sur une
# sortie qui n'existe pas, et le journal reste alimente de toute facon.
$DaemonArgList = @()
if ($Leagues)      { $DaemonArgList += @('--leagues', $Leagues) }
if ($Position)     { $DaemonArgList += @('--position', $Position) }
if ($Interval -gt 0) { $DaemonArgList += @('--interval', "$Interval") }
$DaemonArgList += '--quiet'
$DaemonArgs = $DaemonArgList -join ' '

# ------------------------------------------------------------- python --------

function Find-Python {
    # Sans guillemets internes : PowerShell les mange en passant a un exe natif.
    $probeScript = 'import sys; print(sys.executable); print(sys.version_info[0]); print(sys.version_info[1])'
    $candidates = @(
        @{ File = 'py';      Args = @('-3') },
        @{ File = 'python3'; Args = @() },
        @{ File = 'python';  Args = @() }
    )

    # Le stub "Python" du Microsoft Store repond du texte libre et un code
    # d'erreur : on verifie le code de sortie et on parse defensivement.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        foreach ($c in $candidates) {
            if (-not (Get-Command $c.File -ErrorAction SilentlyContinue)) { continue }

            # @callArgs : splatting. Un @(...) litteral serait passe comme UN seul argument.
            $callArgs = @($c.Args) + @('-c', $probeScript)
            try {
                $probe = @(& $c.File @callArgs)
            } catch { continue }

            if ($LASTEXITCODE -ne 0 -or $probe.Count -lt 3) { continue }
            $exe = "$($probe[0])".Trim()
            try {
                $ver = [version]::new([int]"$($probe[1])".Trim(), [int]"$($probe[2])".Trim())
            } catch { continue }
            if ($exe -and (Test-Path $exe) -and $ver -ge [version]'3.8') { return $exe }
        }
    } finally {
        $ErrorActionPreference = $previous
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Item 'Python 3.8+ est introuvable.'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Item 'Installe-le puis relance ce script :'
        Write-Item '  winget install -e --id Python.Python.3.12'
    } else {
        Write-Item 'Installe-le depuis https://www.python.org/downloads/ (coche "tcl/tk" et "Add to PATH").'
    }
    exit 1
}
Write-Item "python      : $python"

$pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = $python }

if ((Invoke-PythonQuiet -Exe $python -Code 'import tkinter') -eq 0) {
    Write-Item 'tkinter     : OK'
} else {
    Write-Item 'tkinter     : MANQUANT -> reinstalle Python en cochant "tcl/tk and IDLE"'
}
Write-Item 'audio       : winsound + MCI (integres a Windows)'

# ----------------------------------------------------------- connexion ------

# L'URL passe par argv : aucun guillemet a faire survivre a PowerShell.
$probeCode = 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=8).read(64)'
$probeUrl  = 'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard'
if ((Invoke-PythonQuiet -Exe $python -Code $probeCode -Extra @($probeUrl)) -eq 0) {
    Write-Item 'source      : ESPN joignable'
} else {
    Write-Item 'source      : ESPN INJOIGNABLE pour l''instant (le daemon reessaiera)'
}

# ------------------------------------------------------------ fichiers -------

Write-Head 'Copie des fichiers'

# Un daemon deja lance continuerait sur du code efface : on l'arrete, et on le
# relance en fin d'installation s'il tournait. C'est aussi ce que fait
# `butbutbut --update`, qui rejoue ce script.
$RecordDir = Join-Path $env:LOCALAPPDATA 'butbutbut'
$pidFile = Join-Path $RecordDir 'butbutbut.pid'
$daemonTournait = $false
if (Test-Path $pidFile) {
    $daemonPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($daemonPid -and (Get-Process -Id $daemonPid -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $daemonPid -Force -ErrorAction SilentlyContinue
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        $daemonTournait = $true
        Write-Item "daemon      : arrete (pid $daemonPid) le temps de la copie"
    }
}

if (Test-Path $AppDir) { Remove-Item $AppDir -Recurse -Force }
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
Copy-Item (Join-Path $Src 'butbutbut') -Destination (Join-Path $AppDir 'butbutbut') -Recurse -Force
Write-Item "code        : $AppDir\butbutbut"

$EngineVersion = '0.2.0'
$EngineUrl = "https://github.com/boubou666/desktop-overlay/releases/download/v$EngineVersion/desktop_overlay-$EngineVersion-py3-none-any.whl"
$EngineSha256 = '9ac3676603f73f30bf2d756040cdc35faed9fd5977a6ebf53b5eafd0a5db4f34'
$EngineInstaller = @"
import hashlib
import io
import sys
import urllib.request
import zipfile

url, expected, target = sys.argv[1:]
with urllib.request.urlopen(url, timeout=30) as response:
    wheel = response.read()
actual = hashlib.sha256(wheel).hexdigest()
if actual != expected:
    raise SystemExit(
        "desktop-overlay: SHA-256 inattendu ({} au lieu de {})".format(
            actual, expected
        )
    )
with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
    archive.extractall(target)
"@
& $python -c $EngineInstaller $EngineUrl $EngineSha256 $AppDir
if ($LASTEXITCODE -ne 0) {
    Write-Item "Echec de l'installation de desktop-overlay $EngineVersion."
    exit 1
}
Write-Item "moteur      : desktop-overlay $EngineVersion"

foreach ($name in @('butbutbut', 'but')) {
    $cmdPath = Join-Path $BinDir "$name.cmd"
    @"
@echo off
set "PYTHONPATH=$AppDir;%PYTHONPATH%"
"$python" -m butbutbut %*
"@ | Set-Content -Path $cmdPath -Encoding ASCII
}
Write-Item "commande    : $BinDir\butbutbut.cmd  (alias : but.cmd)"

# PATH utilisateur (pas de PATH machine, pas d'admin)
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$BinDir", 'User')
    Write-Item "PATH        : $BinDir ajoute (rouvre ton terminal)"
} else {
    Write-Item 'PATH        : deja configure'
}

# --------------------------------------------------------- demarrage ---------

$startup = [Environment]::GetFolderPath('Startup')
$lnkPath = Join-Path $startup 'butbutbut.lnk'

if (-not $NoAutostart) {
    Write-Head 'Demarrage automatique'
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($lnkPath)
    $lnk.TargetPath       = $pythonw
    $lnk.Arguments        = "-m butbutbut $DaemonArgs"
    $lnk.WorkingDirectory = $AppDir
    $lnk.Description      = 'butbutbut - alerte de buts des 5 grands championnats'
    $lnk.WindowStyle      = 7
    $lnk.Save()

    # PYTHONPATH utilisateur pour que le raccourci trouve le module
    $envPyPath = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'User')
    if (-not $envPyPath -or $envPyPath -notlike "*$AppDir*") {
        $newPyPath = if ($envPyPath) { "$envPyPath;$AppDir" } else { $AppDir }
        [Environment]::SetEnvironmentVariable('PYTHONPATH', $newPyPath, 'User')
    }
    Write-Item "raccourci   : $lnkPath"
    Write-Item 'butbutbut demarrera a la prochaine ouverture de session.'
} else {
    if (Test-Path $lnkPath) { Remove-Item $lnkPath -Force }
    Write-Item 'demarrage automatique ignore (-NoAutostart)'
}

# Fiche d'installation, relue par `butbutbut --update` : d'ou vient le code,
# quel commit, et avec quelles options il a ete installe.
New-Item -ItemType Directory -Path $RecordDir -Force | Out-Null
$commit = ''
if ((Test-Path (Join-Path $Src '.git')) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $commit = (& git -C $Src rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0) { $commit = '' }
}
$version = ''
$initFile = Join-Path $Src 'butbutbut\__init__.py'
if (Test-Path $initFile) {
    $trouve = Select-String -Path $initFile -Pattern '^__version__ = "(.+)"' | Select-Object -First 1
    if ($trouve) { $version = $trouve.Matches[0].Groups[1].Value }
}
[ordered]@{
    source       = $Src
    commit       = "$commit".Trim()
    version      = $version
    leagues      = $Leagues
    position     = $Position
    interval     = $(if ($Interval -gt 0) { $Interval } else { $null })
    autostart    = (-not $NoAutostart.IsPresent)
    app_dir      = $AppDir
    bin_dir      = $BinDir
    python       = $python
    pythonw      = $pythonw
    platform     = 'Windows'
    installed_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
} | ConvertTo-Json | Set-Content -Path (Join-Path $RecordDir 'install.json') -Encoding utf8
Write-Item "fiche       : $RecordDir\install.json"

if ($daemonTournait -and -not $NoAutostart) {
    $env:PYTHONPATH = "$AppDir;$env:PYTHONPATH"
    Start-Process -FilePath $pythonw -ArgumentList (@('-m', 'butbutbut') + $DaemonArgList) `
        -WorkingDirectory $AppDir -WindowStyle Hidden
    Write-Item 'daemon      : redemarre avec le nouveau code'
}

Write-Head 'Termine'
Write-Item 'Voir trois cartes s''empiler : butbutbut --test 3'
Write-Item 'Les matchs du jour          : butbutbut --scores'
Write-Item 'Etat                        : butbutbut --status'
Write-Item 'Mettre a jour               : butbutbut --update'
Write-Item 'Desinstaller                : powershell -ExecutionPolicy Bypass -File .\uninstall.ps1'
Write-Host ''
$env:PYTHONPATH = "$AppDir;$env:PYTHONPATH"
& $python -m butbutbut --status
