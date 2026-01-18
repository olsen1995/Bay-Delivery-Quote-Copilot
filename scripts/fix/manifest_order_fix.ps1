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

# Canonical manifest key order
$canonicalOrder = @(
    "name",
    "version",
    "description",
    "author",
    "dependencies",
    "scripts"
)

function Get-ManifestFiles($basePath) {
    if ((Test-Path $basePath -PathType Leaf) -and ($basePath -like "*.manifest")) {
        return @($basePath)
    }

    return Get-ChildItem -Path $basePath -Recurse -Include "*.manifest" -File |
    Select-Object -ExpandProperty FullName
}

function Format-ManifestKeys($json) {
    $ordered = [ordered]@{}

    foreach ($key in $canonicalOrder) {
        if ($json.PSObject.Properties.Name -contains $key) {
            $ordered[$key] = $json.$key
        }
    }

    # Preserve any non-canonical / unknown keys at the end
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

        $formatted = Format-ManifestKeys $originalJson
        $formattedText = $formatted | ConvertTo-Json -Depth 10

        if ($originalText -ne $formattedText) {
            if ($Check) {
                Write-Output "❌ [OUT OF ORDER] $file"
                $filesWithIssues += $file
            }
            else {
                Set-Content -Path $file -Value $formattedText -Encoding UTF8
                Write-Output "✅ [FIXED] $file"
            }
        }
        elseif ($Check) {
            Write-Output "✅ [OK] $file"
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
# Auto-stage any modified .manifest files
$changed = git status --porcelain | Where-Object { $_ -match '\.manifest$' -and $_ -match '^ M ' }

foreach ($line in $changed) {
    $file = $line -replace '^ M ', ''
    Write-Host "📌 Auto-staging fixed file: $file"
    git add $file
}
