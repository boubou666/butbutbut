param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$TeamId
)

$ErrorActionPreference = 'Stop'
if ($TeamId -notmatch '^\d+$') {
    throw "Identifiant ESPN invalide: $TeamId"
}

$sourcePath = [System.IO.Path]::GetFullPath($Source)
$generatedRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $env:USERPROFILE '.codex\generated_images')) +
    [System.IO.Path]::DirectorySeparatorChar
if (-not $sourcePath.StartsWith(
        $generatedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Source hors du dossier ImageGen: $sourcePath"
}
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "ImageGen n'a pas produit: $sourcePath"
}

$assetRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot '..\butbutbut\assets\clubs'))
New-Item -ItemType Directory -Force -Path $assetRoot | Out-Null
$targetPath = Join-Path $assetRoot ($TeamId + '.png')

Add-Type -AssemblyName System.Drawing
$image = [System.Drawing.Image]::FromFile($sourcePath)
try {
    $bitmap = New-Object System.Drawing.Bitmap(
        512, 512, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.InterpolationMode =
                [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.SmoothingMode =
                [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.DrawImage($image, 0, 0, 512, 512)
        }
        finally {
            $graphics.Dispose()
        }
        $bitmap.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $bitmap.Dispose()
    }
}
finally {
    $image.Dispose()
}

Write-Output $targetPath
