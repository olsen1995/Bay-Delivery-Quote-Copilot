<#
.SYNOPSIS
    Lints and validates .manifest files for canonical structure and hygiene.
.DESCRIPTION
    - Validates key presence and order
    - Detects formatting anomalies
    - Supports standalone run or QuickSmoke integration
.PARAMETER Path
    Optional path to a single .manifest file or directory to recursively scan.
#>

param(
    [string]$Path = "."
)

# Define canonical key order (customize this list as needed)
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
    return Get-ChildItem -Path $basePath -Recurse -Include "*.manifest" -File | Select-Object -ExpandProperty FullName
}

function Test-ManifestFile($filePath) {
    $content = Get-Content $filePath -Raw
    $lines = $content -split "`r?`n"

    $json = $null
    try {
        $json = $content | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Write-Output "❌ [INVALID JSON] $filePath"
        return $false
    }

    # Check key order
    $actualKeys = ($json.PSObject.Properties | Select-Object -ExpandProperty Name)
    $expectedKeys = $canonicalOrder | Where-Object { $actualKeys -contains $_ }

    if (-not ($actualKeys -eq $expectedKeys)) {
        Write-Output "⚠️  [KEY ORDER] $filePath — Expected order: $($expectedKeys -join ', ')"
    }

    # Validate required fields
    $missing = @()
    foreach ($key in $canonicalOrder) {
        if (-not $actualKeys -contains $key) {
            $missing += $key
        }
    }
    if ($missing.Count -gt 0) {
        Write-Output "❌ [MISSING KEYS] $filePath — Missing: $($missing -join ', ')"
    }

    # Check for trailing commas
    if ($content -match ",\s*[\}\]]") {
        Write-Output "❌ [TRAILING COMMA] $filePath — Remove trailing commas"
    }

    # Optional: Check for 2-space indentation
    foreach ($line in $lines) {
        if ($line -match "^\s+" -and ($line -match "^\s{2}\S" -eq $false)) {
            Write-Output "⚠️  [INDENTATION] $filePath — Non-2-space indent detected"
            break
        }
    }

    return $true
}

# Main execution
$files = Get-ManifestFiles $Path
$failureCount = 0

foreach ($file in $files) {
    $result = Test-ManifestFile -filePath $file
    if (-not $result) {
        $failureCount++
    }
}

if ($failureCount -eq 0) {
    Write-Output "✅ All manifest files passed lint checks."
    exit 0
}
else {
    Write-Output "`n❌ $failureCount file(s) failed linting."
    exit 1
}

Write-Host "🚦 Running QuickSmoke Checks..."
