# publish-to-main.ps1 - Publish dev changes to public main branch excluding internal files
#
# Usage: .\scripts\publish-to-main.ps1 [-DryRun] [-Squash]
#
# Options:
#   -DryRun   Show what would be done without making changes
#   -Squash   Squash all commits into one (recommended for cleaner history)

param(
    [switch]$DryRun,
    [switch]$Squash,
    [switch]$Help
)

# =============================================================================
# CONFIGURATION - Edit these as needed
# =============================================================================

# Files/patterns to exclude from public repo (relative to repo root)
$ExcludeFiles = @(
    "OPTIMIZE_PLAN.md"
    "SMART_SAVE.md"
    "TODO.md"
    ".claude/settings.local.json"
    ".claude/skills/"
    ".claude/agents/"
    ".claude/utils/"
)

# Remote names
$DevRemote = "memcord_dev"      # Your dev remote
$PublicRemote = "origin"        # Public repo remote

# Branch names
$SourceBranch = "main"          # Branch with dev changes
$TargetBranch = "main"          # Branch to publish to

# =============================================================================
# SCRIPT LOGIC
# =============================================================================

$ErrorActionPreference = "Stop"

function Write-Info { param($msg) Write-Host "[INFO] " -ForegroundColor Blue -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "[OK] " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Warn { param($msg) Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err { param($msg) Write-Host "[ERROR] " -ForegroundColor Red -NoNewline; Write-Host $msg }

if ($Help) {
    Write-Host "Usage: .\scripts\publish-to-main.ps1 [-DryRun] [-Squash]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -DryRun   Show what would be done without making changes"
    Write-Host "  -Squash   Squash all commits into one"
    exit 0
}

# Check we're in a git repo
$gitDir = git rev-parse --git-dir 2>$null
if (-not $gitDir) {
    Write-Err "Not in a git repository"
    exit 1
}

$RepoRoot = git rev-parse --show-toplevel
Set-Location $RepoRoot

Write-Info "Repository: $RepoRoot"
Write-Info "Dry run: $DryRun"
Write-Info "Squash: $Squash"
Write-Host ""

# Fetch latest from remotes
Write-Info "Fetching from remotes..."
if (-not $DryRun) {
    git fetch $PublicRemote 2>$null
}

# Check for uncommitted changes
$status = git status --porcelain
if ($status -and ($status | Where-Object { $_ -match "^[MADRC]" })) {
    Write-Err "You have uncommitted changes. Please commit or stash them first."
    exit 1
}

# Get commit range
$CommitsAhead = (git rev-list "$PublicRemote/$TargetBranch..HEAD" 2>$null | Measure-Object -Line).Lines
Write-Info "Commits to publish: $CommitsAhead"

if ($CommitsAhead -eq 0) {
    Write-Success "Already up to date with $PublicRemote/$TargetBranch"
    exit 0
}

# Show commits that will be published
Write-Host ""
Write-Info "Commits to be published:"
git log "$PublicRemote/$TargetBranch..HEAD" --oneline
Write-Host ""

# Check for excluded files in the commits
Write-Info "Checking for files to exclude..."
$ChangedFiles = git diff "$PublicRemote/$TargetBranch..HEAD" --name-only
$FoundExcluded = @()

foreach ($pattern in $ExcludeFiles) {
    $matched = $ChangedFiles | Where-Object { $_ -like "$pattern*" -or $_ -eq $pattern }
    if ($matched) {
        $FoundExcluded += $pattern
        Write-Warn "Found: $pattern"
    }
}

if ($FoundExcluded.Count -eq 0) {
    Write-Success "No excluded files found in commits"

    if ($DryRun) {
        Write-Info "[DRY RUN] Would push directly to $PublicRemote/$TargetBranch"
        exit 0
    }

    # Simple push if no excluded files
    Write-Info "Pushing to $PublicRemote/$TargetBranch..."
    git push $PublicRemote "${SourceBranch}:${TargetBranch}"
    Write-Success "Published successfully!"
    exit 0
}

Write-Host ""
Write-Info "Files to be excluded from publish:"
foreach ($f in $FoundExcluded) {
    Write-Host "  - $f"
}
Write-Host ""

if ($DryRun) {
    Write-Info "[DRY RUN] Would create clean branch and remove excluded files"
    Write-Info "[DRY RUN] Would push to $PublicRemote/$TargetBranch"
    exit 0
}

# Create temporary branch for clean publish
$TempBranch = "publish-clean-$(Get-Date -Format 'yyyyMMddHHmmss')"
$OriginalBranch = git branch --show-current

Write-Info "Creating temporary branch: $TempBranch"
git checkout -b $TempBranch

# Remove excluded files from tracking (but keep locally)
Write-Info "Removing excluded files from git tracking..."
foreach ($pattern in $FoundExcluded) {
    if (Test-Path $pattern) {
        git rm -rf --cached $pattern 2>$null
        Write-Success "Removed from tracking: $pattern"
    }
}

# Add exclusions to .gitignore if not already there
Write-Info "Ensuring exclusions are in .gitignore..."
$gitignoreContent = Get-Content .gitignore -ErrorAction SilentlyContinue
foreach ($pattern in $FoundExcluded) {
    if ($gitignoreContent -notcontains $pattern) {
        Add-Content .gitignore $pattern
        Write-Success "Added to .gitignore: $pattern"
    }
}

# Commit the removal
$staged = git diff --cached --name-only
if ($staged) {
    git add .gitignore
    $commitMsg = @"
chore: exclude internal development files from public repo

Excluded files:
$($FoundExcluded | ForEach-Object { "- $_" } | Out-String)
These files are for internal development only.
"@
    git commit -m $commitMsg
    Write-Success "Created cleanup commit"
}

# Push to public remote
Write-Info "Pushing to $PublicRemote/$TargetBranch..."
git push $PublicRemote "${TempBranch}:${TargetBranch}"

# Cleanup: go back to original branch
Write-Info "Cleaning up..."
git checkout $OriginalBranch
git branch -D $TempBranch

# Update local tracking
git fetch $PublicRemote

Write-Success "Successfully published to $PublicRemote/$TargetBranch!"
Write-Host ""
Write-Info "Summary:"
Write-Host "  - Commits published: $CommitsAhead"
Write-Host "  - Files excluded: $($FoundExcluded.Count)"
Write-Host ""
Write-Info "Excluded files remain in your local repo but are not in the public repo."
