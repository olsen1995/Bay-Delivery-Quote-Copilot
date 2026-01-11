#requires -Version 7.0

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail($Message) {
  Write-Host "FAIL: $Message" -ForegroundColor Red
  exit 1
}

function Ok($Message) {
  Write-Host "OK: $Message" -ForegroundColor Green
}

# Repo root = parent folder of /tools
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$InstructionsPath = Join-Path $RepoRoot "instructions\Instructions.txt"
$ManifestPath     = Join-Path $RepoRoot "canon\CANON_MANIFEST.json"

Write-Host "Life OS QuickSmoke running..." -ForegroundColor Cyan
Write-Host ""

# 1) Check Instructions.txt exists and is long enough
if (-not (Test-Path $InstructionsPath)) {
  Fail "instructions/Instructions.txt is missing"
}

$instr = Get-Content $InstructionsPath -Raw
if ($instr.Trim().Length -lt 2000) {
  Fail "Instructions.txt is too short"
}

Ok "Instructions.txt exists and looks good"

# 2) Check CANON_MANIFEST.json exists and parses
if (-not (Test-Path $ManifestPath)) {
  Fail "canon/CANON_MANIFEST.json is missing"
}

try {
  $manifest = (Get-Content $ManifestPath -Raw | ConvertFrom-Json)
} catch {
  Fail "canon/CANON_MANIFEST.json is not valid JSON"
}

Ok "Canon manifest exists and parses"

# 3) Check for placeholder words
$placeholders = @("TODO","FIXME","TBD","<INSERT","REPLACE ME")
$hits = Select-String -Path $InstructionsPath, $ManifestPath -Pattern $placeholders -SimpleMatch -ErrorAction SilentlyContinue

if ($hits) {
  Fail "Placeholder words found (TODO / FIXME / etc.)"
}

Ok "No placeholder words found"

Write-Host ""
Write-Host "PASS: QuickSmoke completed successfully" -ForegroundColor Green
exit 0
