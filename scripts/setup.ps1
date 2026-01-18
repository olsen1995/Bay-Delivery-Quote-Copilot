# scripts/setup.ps1
$ErrorActionPreference = "Stop"

Write-Host "🛠️ Setting up pre-commit hook..."

$gitHookPath = ".git/hooks/pre-commit"
$scriptHookSource = "scripts/hooks/pre-commit.ps1"
$bashWrapperSource = ".git_hooks/pre-commit"

# Ensure we're in the repo root
if (-not (Test-Path $scriptHookSource)) {
    Write-Error "❌ Run this from the repo root!"
    exit 1
}

# Copy the bash wrapper
if (Test-Path $bashWrapperSource) {
    Copy-Item $bashWrapperSource $gitHookPath -Force
    Write-Host "✅ Copied Bash pre-commit hook"
}
else {
    Write-Error "❌ Missing Bash wrapper file at $bashWrapperSource"
    exit 1
}

# Make it executable on Unix
if ($IsLinux -or $IsMacOS) {
    chmod +x $gitHookPath
}

Write-Host "🎉 Hook installed! You’re ready to commit cleanly."
Write-Host "👉 To test, try making a commit now."