Write-Host "🚦 Running QuickSmoke Checks..."

$RequiredFiles = @(
  "knowledge/00_LifeOS_Constitution.md",
  "knowledge/01_ModeRouter.md",
  "instructions/Instructions.txt",
  "canon/CANON_MANIFEST.json"
)

$failures = 0

foreach ($file in $RequiredFiles) {
  if (!(Test-Path $file)) {
    Write-Host "❌ MISSING: $file"
    $failures++
  }
  else {
    Write-Host "✅ Found: $file"
  }
}

if ($failures -gt 0) {
  Write-Host "`n🚫 QuickSmoke FAILED — $failures file(s) missing."
  exit 1
}
else {
  Write-Host "`n✅ QuickSmoke PASSED — All core files present."
  exit 0
}
Write-Host "🚦 Running QuickSmoke Checks..."