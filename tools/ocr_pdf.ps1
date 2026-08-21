param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [int]$StartPage = 1,
    [int]$EndPage = 0,
    [int]$RenderWidth = 1800
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapPixelFormat, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapAlphaMode, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Media.Ocr, ContentType = WindowsRuntime]

$script:AsTaskActionMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq 'AsTask' -and
        -not $_.IsGenericMethod -and
        $_.GetParameters().Count -eq 1
    } |
    Select-Object -First 1

$script:AsTaskOperationMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq 'AsTask' -and
        $_.IsGenericMethod -and
        $_.GetGenericArguments().Count -eq 1 -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -like 'IAsyncOperation*'
    } |
    Select-Object -First 1

function Wait-WinRtOperation {
    param(
        [Parameter(Mandatory = $true)]$Operation,
        [Type]$ResultType
    )

    if ($ResultType) {
        $method = $script:AsTaskOperationMethod.MakeGenericMethod($ResultType)
        $task = $method.Invoke($null, @($Operation))
        return $task.GetAwaiter().GetResult()
    }

    $task = $script:AsTaskActionMethod.Invoke($null, @($Operation))
    $task.GetAwaiter().GetResult()
}

$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
$storageFile = Wait-WinRtOperation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($resolvedPath)) ([Windows.Storage.StorageFile])
$pdf = Wait-WinRtOperation ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($storageFile)) ([Windows.Data.Pdf.PdfDocument])
$ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()

if (-not $ocr) {
    throw 'No Windows OCR engine is available for the current user languages.'
}

$pageCount = [int]$pdf.PageCount
if ($StartPage -lt 1 -or $StartPage -gt $pageCount) {
    throw "StartPage must be between 1 and $pageCount."
}

if ($EndPage -eq 0) {
    $EndPage = $pageCount
}

if ($EndPage -lt $StartPage -or $EndPage -gt $pageCount) {
    throw "EndPage must be between StartPage and $pageCount."
}

Write-Output "FILE: $resolvedPath"
Write-Output "PAGES: $pageCount"

for ($pageNumber = $StartPage; $pageNumber -le $EndPage; $pageNumber++) {
    $page = $pdf.GetPage([uint32]($pageNumber - 1))
    $stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $options = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth = [uint32]$RenderWidth

    try {
        $null = Wait-WinRtOperation ($page.RenderToStreamAsync($stream, $options))
        $stream.Seek(0)
        $decoder = Wait-WinRtOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $softwareBitmap = Wait-WinRtOperation ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

        if ($softwareBitmap.BitmapPixelFormat -ne [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8 -or
            $softwareBitmap.BitmapAlphaMode -ne [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore) {
            $converted = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert(
                $softwareBitmap,
                [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
                [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore
            )
            $softwareBitmap.Dispose()
            $softwareBitmap = $converted
        }

        $result = Wait-WinRtOperation ($ocr.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])
        Write-Output "`n===== PAGE $pageNumber / $pageCount ====="
        Write-Output $result.Text
    }
    finally {
        if ($softwareBitmap) { $softwareBitmap.Dispose() }
        if ($stream) { $stream.Dispose() }
        if ($page) { $page.Dispose() }
    }
}
