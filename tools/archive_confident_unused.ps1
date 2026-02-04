$ErrorActionPreference = "Stop"

Write-Host "Archiving confidently unused items (reversible)..."

# Repo root is two levels up from tools/
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

# Sentinels: confirm we're at repo root
$RenderYaml = Join-Path $RepoRoot "render.yaml"
$OpenApi = Join-Path $RepoRoot "public/.well-known/openapi.json"

if (!(Test-Path $RenderYaml)) {
    Write-Host "STOP: render.yaml not found at repo root: $RenderYaml"
    exit 1
}
if (!(Test-Path $OpenApi)) {
    Write-Host "STOP: OpenAPI contract missing: $OpenApi"
    exit 1
}

$DateStamp = (Get-Date).ToString("yyyy-MM-dd")
$ArchiveRoot = Join-Path $RepoRoot ("archive/confident_unused/" + $DateStamp)

# Ensure archive destination exists
New-Item -ItemType Directory -Force -Path $ArchiveRoot | Out-Null

# Targets to archive (relative to repo root)
$Targets = @(
    "templates",
    "static",
    "tools/validate_canon.py",
    "dashboard.md"
)

$ArchivedAny = $false

foreach ($t in $Targets) {
    $src = Join-Path $RepoRoot $t
    if (Test-Path $src) {
        $dst = Join-Path $ArchiveRoot $t

        # Ensure destination parent dir exists
        $dstParent = Split-Path -Parent $dst
        New-Item -ItemType Directory -Force -Path $dstParent | Out-Null

        Write-Host "ARCHIVE: $t -> archive/confident_unused/$DateStamp/$t"
        Move-Item -Force -Path $src -Destination $dst
        $ArchivedAny = $true
    }
    else {
        Write-Host "SKIP (not found): $t"
    }
}

if (-not $ArchivedAny) {
    Write-Host "No targets found to archive. Nothing changed."
    exit 0
}

Write-Host "Archive complete."
Write-Host "Next: git status / stage / commit."
