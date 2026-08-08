$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

$workspace = 'D:\OneDrive\文档\我的文件\git\仁爱物理竞赛'
$sourceDir = Join-Path $workspace '声速\声速测量可视化实验说明\声速四种方法_Julia综合可视化方案\output'
$outputDir = Join-Path $workspace 'tmp\ppt_build\sound\crops'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Save-Crop {
    param(
        [Parameter(Mandatory)] [string] $Source,
        [Parameter(Mandatory)] [string] $Destination,
        [Parameter(Mandatory)] [int] $X,
        [Parameter(Mandatory)] [int] $Y,
        [Parameter(Mandatory)] [int] $Width,
        [Parameter(Mandatory)] [int] $Height
    )

    $bitmap = [System.Drawing.Bitmap]::FromFile($Source)
    try {
        if ($X -lt 0 -or $Y -lt 0 -or ($X + $Width) -gt $bitmap.Width -or ($Y + $Height) -gt $bitmap.Height) {
            throw "Crop is outside source bounds: $Source"
        }
        $rectangle = [System.Drawing.Rectangle]::new($X, $Y, $Width, $Height)
        $cropped = $bitmap.Clone($rectangle, $bitmap.PixelFormat)
        try {
            $cropped.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $cropped.Dispose()
        }
    }
    finally {
        $bitmap.Dispose()
    }
}

Save-Crop -Source (Join-Path $sourceDir 'smoke_echo.png') `
    -Destination (Join-Path $outputDir 'echo_double_pulse.png') `
    -X 390 -Y 115 -Width 640 -Height 430

Save-Crop -Source (Join-Path $sourceDir 'smoke_dual_microphone.png') `
    -Destination (Join-Path $outputDir 'dual_correlation_peak.png') `
    -X 650 -Y 115 -Width 700 -Height 430

Save-Crop -Source (Join-Path $sourceDir 'smoke_oscilloscope_phase.png') `
    -Destination (Join-Path $outputDir 'phase_periodicity.png') `
    -X 600 -Y 115 -Width 750 -Height 430

Save-Crop -Source (Join-Path $sourceDir 'smoke_standing_wave.png') `
    -Destination (Join-Path $outputDir 'standing_envelope.png') `
    -X 590 -Y 115 -Width 760 -Height 430

Get-ChildItem -LiteralPath $outputDir -Filter '*.png' |
    Sort-Object Name |
    Select-Object Name, Length
