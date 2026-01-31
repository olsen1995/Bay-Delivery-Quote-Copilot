Write-Host "Starting LifeOS Co-Pilot cleanup phase..."

# 1. Remove legacy OpenAPI files (outside /public/.well-known/)
$openapiFiles = Get-ChildItem -Path . -Recurse -Include openapi.json | Where-Object {
    $_.FullName -notmatch "\\public\\.well-known\\openapi.json$"
}
foreach ($file in $openapiFiles) {
    Write-Host "Removing legacy OpenAPI file: $($file.FullName)"
    Remove-Item $file.FullName -Force
}

# 2. Remove nested repo under /lifeos/canon/
$canonRepoPath = "lifeos/canon/Life-OS-Private-Practical-Co-Pilot"
if (Test-Path $canonRepoPath) {
    Write-Host "Removing nested repo folder: $canonRepoPath"
    Remove-Item $canonRepoPath -Recurse -Force
}

# 3. Remove legacy memory implementations (outside /lifeos/storage/)
$memoryLegacy = @(
    "memory.py",
    "memory_manager.py"
)
foreach ($name in $memoryLegacy) {
    $legacyFiles = Get-ChildItem -Path . -Recurse -Include $name | Where-Object {
        $_.FullName -notmatch "\\lifeos\\storage\\"
    }
    foreach ($file in $legacyFiles) {
        Write-Host "Removing legacy memory file: $($file.FullName)"
        Remove-Item $file.FullName -Force
    }
}

# 4. Remove legacy mode implementations (outside /lifeos/routes/)
$modeLegacy = @(
    "mode.py",
    "mode_router.py"
)
foreach ($name in $modeLegacy) {
    $legacyFiles = Get-ChildItem -Path . -Recurse -Include $name | Where-Object {
        $_.FullName -notmatch "\\lifeos\\routes\\"
    }
    foreach ($file in $legacyFiles) {
        Write-Host "Removing legacy mode file: $($file.FullName)"
        Remove-Item $file.FullName -Force
    }
}

Write-Host "Cleanup complete."
