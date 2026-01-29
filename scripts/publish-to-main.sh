#!/bin/bash
# publish-to-main.sh - Publish dev changes to public main branch excluding internal files
#
# Usage: ./scripts/publish-to-main.sh [OPTIONS]
#
# Options:
#   --dry-run                 Show what would be done without making changes
#   --squash                  Squash all commits into one (recommended for cleaner history)
#   --target-remote <name>    Target remote to push to (default: origin)
#   --source-branch <name>    Source branch with dev changes (default: main)
#   --target-branch <name>    Target branch to publish to (default: main)
#
# Examples:
#   ./scripts/publish-to-main.sh --dry-run
#   ./scripts/publish-to-main.sh --target-remote upstream --target-branch main
#   ./scripts/publish-to-main.sh --source-branch develop --target-branch release

set -e

# =============================================================================
# CONFIGURATION - Defaults (can be overridden via command-line)
# =============================================================================

# Files/patterns to exclude from public repo (relative to repo root)
EXCLUDE_FILES=(
    # Git and CI
    ".git/"
    ".github/workflows/"
    ".releaseexclude"

    # Development files - NOT for public repo
    "OPTIMIZE_PLAN.md"
    "SMART_SAVE.md"
    "TODO.md"
    "CLAUDE.md"
    "CLAUDE-RECOVERY-PROMPT.md"
    "SESSION-RECOVERY.md"
    "TASK-MATRIX.md"
    "DRY_MAINTAINABILITY_ANALYSIS.md"
    "TESTING_METHODOLOGY_VALIDATION.md"
    "PR-DESCRIPTION*.md"
    "PR-READINESS*.md"

    # Claude Code internal files
    ".claude/settings.local.json"
    ".claude/skills/"
    ".claude/agents/"
    ".claude/utils/"

    # Scripts (internal dev tools)
    "scripts/publish-to-main.sh"
    "scripts/publish-to-main.ps1"

    # Python artifacts
    "__pycache__/"
    "*.pyc"
    "*.pyo"
    ".pytest_cache/"
    ".mypy_cache/"
    ".ruff_cache/"
    "*.egg-info/"
    "dist/"
    "build/"
    ".eggs/"

    # Virtual environments
    ".venv/"
    "venv/"
    "env/"

    # IDE and editor files
    ".vscode/"
    ".idea/"
    "*.swp"
    "*.swo"
    "*~"

    # OS files
    ".DS_Store"
    "Thumbs.db"

    # Environment and secrets
    ".env"
    ".env.local"
    ".env.development"
    ".env.test"
    ".env.production"

    # Logs and temp files
    "*.log"
    "*.tmp"
    "*.temp"
    ".tmp/"
    ".temp/"
    "tmpclaude-*"

    # Coverage and test artifacts
    "coverage/"
    ".coverage"
    "htmlcov/"

    # Data directories (user-specific)
    "memory_slots/"
    "shared_memories/"
    "archives/"
    "cache/"
    "logs/"
)

# Remote names (defaults)
PUBLIC_REMOTE="origin"         # Public repo remote

# Branch names (defaults)
SOURCE_BRANCH="main"           # Branch with dev changes
TARGET_BRANCH="main"           # Branch to publish to

# =============================================================================
# SCRIPT LOGIC
# =============================================================================

DRY_RUN=false
SQUASH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --squash)
            SQUASH=true
            shift
            ;;
        --target-remote)
            PUBLIC_REMOTE="$2"
            shift 2
            ;;
        --source-branch)
            SOURCE_BRANCH="$2"
            shift 2
            ;;
        --target-branch)
            TARGET_BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run                 Show what would be done without making changes"
            echo "  --squash                  Squash all commits into one"
            echo "  --target-remote <name>    Target remote to push to (default: origin)"
            echo "  --source-branch <name>    Source branch with dev changes (default: main)"
            echo "  --target-branch <name>    Target branch to publish to (default: main)"
            echo ""
            echo "Examples:"
            echo "  $0 --dry-run"
            echo "  $0 --target-remote upstream --target-branch main"
            echo "  $0 --source-branch develop --target-branch release"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
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
log_info "Target remote: $PUBLIC_REMOTE"
log_info "Source branch: $SOURCE_BRANCH"
log_info "Target branch: $TARGET_BRANCH"
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
