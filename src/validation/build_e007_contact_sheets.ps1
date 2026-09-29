param(
    [string]$InputDirectory = "kaggle/phase_03_morphology_survival/output_e007_full_extraction/qc_overlays",
    [string]$OutputDirectory = "reports/phase_03_e007_ai_contact_sheets",
    [int]$ImagesPerSheet = 8,
    [int]$Columns = 2,
    [int]$ThumbnailWidth = 1200
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = (Resolve-Path -LiteralPath ".").Path
$inputPath = [System.IO.Path]::GetFullPath((Join-Path $root $InputDirectory))
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))

if (-not (Test-Path -LiteralPath $inputPath -PathType Container)) {
    throw "Overlay directory not found: $inputPath"
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$files = @(Get-ChildItem -LiteralPath $inputPath -Filter "*.png" -File | Sort-Object Name)
if ($files.Count -ne 170) {
    throw "Expected 170 overlay PNGs, found $($files.Count)"
}

$rows = [int][Math]::Ceiling($ImagesPerSheet / [double]$Columns)
$labelHeight = 34
$thumbnailHeight = [int][Math]::Round($ThumbnailWidth / 3.0)
$cellHeight = $thumbnailHeight + $labelHeight
$sheetWidth = $Columns * $ThumbnailWidth
$sheetHeight = $rows * $cellHeight
$font = New-Object System.Drawing.Font("Arial", 15, [System.Drawing.FontStyle]::Bold)
$brush = [System.Drawing.Brushes]::Black
$background = [System.Drawing.Brushes]::White
$highQuality = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic

try {
    $pageCount = [int][Math]::Ceiling($files.Count / [double]$ImagesPerSheet)
    for ($page = 0; $page -lt $pageCount; $page++) {
        $canvas = New-Object System.Drawing.Bitmap($sheetWidth, $sheetHeight)
        $graphics = [System.Drawing.Graphics]::FromImage($canvas)
        try {
            $graphics.FillRectangle($background, 0, 0, $sheetWidth, $sheetHeight)
            $graphics.InterpolationMode = $highQuality
            $start = $page * $ImagesPerSheet
            $end = [Math]::Min($start + $ImagesPerSheet, $files.Count)

            for ($index = $start; $index -lt $end; $index++) {
                $slot = $index - $start
                $column = $slot % $Columns
                $row = [int][Math]::Floor($slot / [double]$Columns)
                $x = $column * $ThumbnailWidth
                $y = $row * $cellHeight
                $image = [System.Drawing.Image]::FromFile($files[$index].FullName)
                try {
                    $graphics.DrawImage($image, $x, $y + $labelHeight, $ThumbnailWidth, $thumbnailHeight)
                    $graphics.DrawString($files[$index].BaseName, $font, $brush, $x + 8, $y + 5)
                }
                finally {
                    $image.Dispose()
                }
            }

            $name = "e007_ai_contact_sheet_{0:D2}.png" -f ($page + 1)
            $destination = Join-Path $outputPath $name
            $canvas.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $graphics.Dispose()
            $canvas.Dispose()
        }
    }
}
finally {
    $font.Dispose()
}

Write-Output "Created $pageCount contact sheets in $outputPath"
