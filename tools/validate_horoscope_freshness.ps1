#requires -Version 7.0
<#
Validates that today's horoscope is meaningfully different from the last.
Use:
  .\tools\validate_horoscope_freshness.ps1 -TodayPath path/to/todays_candidate.md

If similarity is too high, exits with failure and message: "No major shift"
#>

param (
    [Parameter(Mandatory = $true)]
    [string]$TodayPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host "FAIL: $Message" -ForegroundColor Red
    exit 1
}

function Ok([string]$Message) {
    Write-Host "OK: $Message" -ForegroundColor Green
}

function Get-Words([string]$Text) {
    return (
        $Text -replace '[^\w\s]', '' `
              -split '\s+' |
        Where-Object { $_ -ne '' } |
        ForEach-Object { $_.ToLowerInvariant() }
    )
}

# --- Load today's horoscope ---
if (-not (Test-Path $TodayPath)) {
    Fail "Today's file not found: $TodayPath"
}

$todayText  = Get-Content $TodayPath -Raw
$todayWords = Get-Words $todayText

# --- Locate horoscope log folder ---
$logFolder = Join-Path $PSScriptRoot "..\daily-horoscope-log"

if (-not (Test-Path $logFolder)) {
    Fail "Log folder not found: $logFolder"
}

# --- Find most recent previous horoscope ---
$latestFile = Get-ChildItem -Path $logFolder -Filter "*.md" |
              Sort-Object Name -Descending |
              Select-Object -First 1

if (-not $latestFile) {
    Ok "No previous horoscope found. Skipping freshness check."
    exit 0
}

# --- Load previous horoscope ---
$lastText  = Get-Content $latestFile.FullName -Raw
$lastWords = Get-Words $lastText

# --- Compute word diffs ---
$diffToday = $todayWords | Where-Object { $_ -notin $lastWords }
$diffLast  = $lastWords  | Where-Object { $_ -notin $todayWords }

# --- Robust count (NO PowerShell scalar bug) ---
$combinedDiffs = $diffToday + $diffLast
$totalUnique = ($combinedDiffs | Sort-Object -Unique | Measure-Object).Count

# --- Enforce freshness threshold ---
if ($totalUnique -lt 5) {
    Fail "No major shift — today’s horoscope is too similar to the previous one."
}

Ok "Horoscope passes freshness gate — change detected ($totalUnique unique word difference(s))"
exit 0
