# new-log-entry.ps1
# Prepends a dated stub to docs/export-development-log.md, prefilled with the commits
# made since the last logged entry. Fill in the reasoning by hand — that part is the point.
#
# Usage (from the repo root):
#   .\scripts\new-log-entry.ps1

$ErrorActionPreference = "Stop"

$repoRoot = git rev-parse --show-toplevel
if (-not $repoRoot) { throw "Not inside a git repository." }

$logPath = Join-Path $repoRoot "docs\export-development-log.md"
if (-not (Test-Path $logPath)) { throw "Log not found at $logPath" }

$today = Get-Date -Format "yyyy-MM-dd"
$content = Get-Content $logPath -Raw

if ($content -match "(?m)^## $today\s*$") {
    Write-Host "An entry for $today already exists. Edit it directly:" -ForegroundColor Yellow
    Write-Host "  $logPath"
    exit 0
}

# Find the date of the most recent entry, so we can list commits since then.
$lastDate = $null
if ($content -match "(?m)^## (\d{4}-\d{2}-\d{2})\s*$") { $lastDate = $Matches[1] }

$commits = @()
if ($lastDate) {
    $commits = git log --since="$lastDate 00:00" --pretty=format:"- ``%h`` %s" 2>$null
} else {
    $commits = git log -10 --pretty=format:"- ``%h`` %s" 2>$null
}

$commitBlock = if ($commits) { ($commits -join "`n") } else { "- _(no commits yet)_" }
$branch = git rev-parse --abbrev-ref HEAD

$stub = @"
## $today

Branch: ``$branch``

**Done**

$commitBlock

**Decided**

-

**Open**

-

**Next**

-

---

"@

# Insert the stub directly above the first existing "## " entry.
$marker = "---`n`n"
$idx = $content.IndexOf($marker)
if ($idx -lt 0) { throw "Could not find the header separator in the log." }
$insertAt = $idx + $marker.Length

$new = $content.Substring(0, $insertAt) + $stub + $content.Substring($insertAt)
Set-Content -Path $logPath -Value $new -NoNewline -Encoding UTF8

Write-Host "Added a $today entry to docs/export-development-log.md" -ForegroundColor Green
Write-Host "Now fill in Decided / Open / Next." -ForegroundColor Cyan
