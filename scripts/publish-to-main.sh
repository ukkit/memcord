#!/bin/bash
# publish-to-main.sh - Publish dev changes to public main branch excluding internal files
#
# Usage: ./scripts/publish-to-main.sh [--dry-run] [--squash]
#
# Options:
#   --dry-run   Show what would be done without making changes
#   --squash    Squash all commits into one (recommended for cleaner history)

set -e

# =============================================================================
# CONFIGURATION - Edit these as needed
# =============================================================================

# Files/patterns to exclude from public repo (relative to repo root)
EXCLUDE_FILES=(
    "OPTIMIZE_PLAN.md"
    "SMART_SAVE.md"
    "TODO.md"
    ".claude/settings.local.json"
    ".claude/skills/"
    ".claude/agents/"
    ".claude/utils/"
)

# Remote names
DEV_REMOTE="memcord_dev"      # Your dev remote
PUBLIC_REMOTE="origin"         # Public repo remote

# Branch names
SOURCE_BRANCH="main"           # Branch with dev changes
TARGET_BRANCH="main"           # Branch to publish to

# =============================================================================
# SCRIPT LOGIC
# =============================================================================

DRY_RUN=false
SQUASH=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --squash) SQUASH=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--squash]"
            echo ""
            echo "Options:"
            echo "  --dry-run   Show what would be done without making changes"
            echo "  --squash    Squash all commits into one"
            exit 0
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

log_info "Repository: $REPO_ROOT"
log_info "Dry run: $DRY_RUN"
log_info "Squash: $SQUASH"
echo ""

# Fetch latest from remotes
log_info "Fetching from remotes..."
if [ "$DRY_RUN" = false ]; then
    git fetch "$PUBLIC_REMOTE" 2>/dev/null || log_warn "Could not fetch from $PUBLIC_REMOTE"
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    log_error "You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Get commit range
COMMITS_AHEAD=$(git rev-list "$PUBLIC_REMOTE/$TARGET_BRANCH..HEAD" --count 2>/dev/null || echo "0")
log_info "Commits to publish: $COMMITS_AHEAD"

if [ "$COMMITS_AHEAD" = "0" ]; then
    log_success "Already up to date with $PUBLIC_REMOTE/$TARGET_BRANCH"
    exit 0
fi

# Show commits that will be published
echo ""
log_info "Commits to be published:"
git log "$PUBLIC_REMOTE/$TARGET_BRANCH..HEAD" --oneline
echo ""

# Check for excluded files in the commits
log_info "Checking for files to exclude..."
FOUND_EXCLUDED=()
for pattern in "${EXCLUDE_FILES[@]}"; do
    if git diff "$PUBLIC_REMOTE/$TARGET_BRANCH..HEAD" --name-only | grep -q "^${pattern}"; then
        FOUND_EXCLUDED+=("$pattern")
        log_warn "Found: $pattern"
    fi
done

if [ ${#FOUND_EXCLUDED[@]} -eq 0 ]; then
    log_success "No excluded files found in commits"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would push directly to $PUBLIC_REMOTE/$TARGET_BRANCH"
        exit 0
    fi

    # Simple push if no excluded files
    log_info "Pushing to $PUBLIC_REMOTE/$TARGET_BRANCH..."
    git push "$PUBLIC_REMOTE" "$SOURCE_BRANCH:$TARGET_BRANCH"
    log_success "Published successfully!"
    exit 0
fi

echo ""
log_info "Files to be excluded from publish:"
for f in "${FOUND_EXCLUDED[@]}"; do
    echo "  - $f"
done
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would create clean branch and remove excluded files"
    log_info "[DRY RUN] Would push to $PUBLIC_REMOTE/$TARGET_BRANCH"
    exit 0
fi

# Create temporary branch for clean publish
TEMP_BRANCH="publish-clean-$(date +%s)"
ORIGINAL_BRANCH=$(git branch --show-current)

log_info "Creating temporary branch: $TEMP_BRANCH"
git checkout -b "$TEMP_BRANCH"

# Remove excluded files from tracking (but keep locally)
log_info "Removing excluded files from git tracking..."
for pattern in "${FOUND_EXCLUDED[@]}"; do
    if [ -e "$pattern" ]; then
        git rm -rf --cached "$pattern" 2>/dev/null || true
        log_success "Removed from tracking: $pattern"
    fi
done

# Add exclusions to .gitignore if not already there
log_info "Ensuring exclusions are in .gitignore..."
for pattern in "${FOUND_EXCLUDED[@]}"; do
    if ! grep -q "^${pattern}$" .gitignore 2>/dev/null; then
        echo "$pattern" >> .gitignore
        log_success "Added to .gitignore: $pattern"
    fi
done

# Commit the removal
if ! git diff --cached --quiet; then
    git add .gitignore
    git commit -m "chore: exclude internal development files from public repo

Excluded files:
$(printf '- %s\n' "${FOUND_EXCLUDED[@]}")

These files are for internal development only."
    log_success "Created cleanup commit"
fi

# Push to public remote
log_info "Pushing to $PUBLIC_REMOTE/$TARGET_BRANCH..."
git push "$PUBLIC_REMOTE" "$TEMP_BRANCH:$TARGET_BRANCH"

# Cleanup: go back to original branch
log_info "Cleaning up..."
git checkout "$ORIGINAL_BRANCH"
git branch -D "$TEMP_BRANCH"

# Update local tracking
git fetch "$PUBLIC_REMOTE"

log_success "Successfully published to $PUBLIC_REMOTE/$TARGET_BRANCH!"
echo ""
log_info "Summary:"
echo "  - Commits published: $COMMITS_AHEAD"
echo "  - Files excluded: ${#FOUND_EXCLUDED[@]}"
echo ""
log_info "Excluded files remain in your local repo but are not in the public repo."
