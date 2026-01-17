<#
.SYNOPSIS
    Auto-fixes key order in .manifest files to match canonical structure.
.DESCRIPTION
    - Canonicalizes key order based on predefined list
    - Supports optional --check mode for CI validation
.PARAMETER Path
    Optional path to a file or directory. Defaults to current directory.
.PARAMETER Check
    If specified, only checks for key order problems, does not modify files.
#>

param(
    [string]$Path = ".",
    [switch]$Check
)

$canonicalOrder = @(
    "name",
    "version",
    "description",
    "author",
    "dependencies",
    "scripts"
)

function Get-ManifestFiles($basePath) {
    if (Test-Path $basePath -PathType Leaf -and $basePath -like "*.manifest") {
        return @($basePath)
    }
    return Get-ChildItem -Path $basePath -Recurse -Include "*.manifest" -File | Select-Object -ExpandProperty FullName
}

function Reorder-ManifestKeys($json) {
    $ordered = [ordered]@{}
    foreach ($key in $canonicalOrder) {
        if ($json.PSObject.Properties.Name -contains $key) {
            $ordered[$key] = $json.$key
        }
    }
    foreach ($prop in $json.PSObject.Properties.Name) {
        if (-not $ordered.Contains($prop)) {
            $ordered[$prop] = $json.$prop
        }
    }
    return $ordered
}

$files = Get-ManifestFiles $Path
$filesWithIssues = @()

foreach ($file in $files) {
    try {
        $originalText = Get-Content $file -Raw
        $originalJson = $originalText | ConvertFrom-Json -ErrorAction Stop

        $reordered = Reorder-ManifestKeys $originalJson
        $reorderedText = $reordered | ConvertTo-Json -Depth 10

        if ($originalText -ne $reorderedText) {
            if ($Check) {
                Write-Output "❌ [OUT OF ORDER] $file"
                $filesWithIssues += $file
            }
            else {
                Set-Content -Path $file -Value $reorderedText
                Write-Output "✅ [FIXED] $file"
            }
        }
        else {
            if ($Check) {
                Write-Output "✅ [OK] $file"
            }
        }

    }
    catch {
        Write-Output "❌ [ERROR] $file — $_"
    }
}

if ($Check -and $filesWithIssues.Count -gt 0) {
    Write-Output "`n❌ $($filesWithIssues.Count) file(s) have incorrect key order."
    exit 1
}

if ($Check) {
    Write-Output "`n✅ All files have correct key order."
}
