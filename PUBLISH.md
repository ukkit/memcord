# Publishing to Production Repository

This document describes how to use the local publish scripts to sync changes from the development repository to the public production repository.

## Overview

The publish scripts (`publish-to-main.sh` for Unix/macOS and `publish-to-main.ps1` for Windows) provide a way to push changes from your local development environment to the public repository while automatically excluding internal development files.

**Key features:**
- Automatically excludes 60+ internal/development files and patterns
- Supports dry-run mode to preview changes
- Configurable source/target branches and remotes
- Creates clean commits without internal files

## Prerequisites

1. Git installed and configured
2. Remote configured for the target (public) repository:
   ```bash
   git remote add origin https://github.com/ukkit/memcord.git
   # or verify existing remote
   git remote -v
   ```

## Usage

### Windows (PowerShell)

```powershell
.\scripts\publish-to-main.ps1 [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `-DryRun` | Preview changes without making them | `false` |
| `-Squash` | Squash all commits into one | `false` |
| `-TargetRemote <name>` | Remote to push to | `origin` |
| `-SourceBranch <name>` | Local branch with changes | `main` |
| `-TargetBranch <name>` | Remote branch to push to | `main` |
| `-Help` | Show help message | - |

### Unix/macOS (Bash)

```bash
./scripts/publish-to-main.sh [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Preview changes without making them | `false` |
| `--squash` | Squash all commits into one | `false` |
| `--target-remote <name>` | Remote to push to | `origin` |
| `--source-branch <name>` | Local branch with changes | `main` |
| `--target-branch <name>` | Remote branch to push to | `main` |
| `--help`, `-h` | Show help message | - |

## Examples

### Preview changes (dry run)

See what would be published without making any changes:

```powershell
# Windows
.\scripts\publish-to-main.ps1 -DryRun
```

```bash
# Unix/macOS
./scripts/publish-to-main.sh --dry-run
```

### Basic publish

Publish from local `main` to `origin/main`:

```powershell
# Windows
.\scripts\publish-to-main.ps1
```

```bash
# Unix/macOS
./scripts/publish-to-main.sh
```

### Publish to a different remote

If your public repo is configured as `upstream` instead of `origin`:

```powershell
# Windows
.\scripts\publish-to-main.ps1 -TargetRemote upstream
```

```bash
# Unix/macOS
./scripts/publish-to-main.sh --target-remote upstream
```

### Publish from a feature branch

Publish changes from `develop` branch to `main`:

```powershell
# Windows
.\scripts\publish-to-main.ps1 -SourceBranch develop -TargetBranch main
```

```bash
# Unix/macOS
./scripts/publish-to-main.sh --source-branch develop --target-branch main
```

### Full example with all options

```powershell
# Windows - dry run from develop to upstream/release
.\scripts\publish-to-main.ps1 -DryRun -TargetRemote upstream -SourceBranch develop -TargetBranch release
```

```bash
# Unix/macOS - dry run from develop to upstream/release
./scripts/publish-to-main.sh --dry-run --target-remote upstream --source-branch develop --target-branch release
```

## What Gets Excluded

The scripts automatically exclude the following files and patterns from being published:

### Development Files
- `OPTIMIZE_PLAN.md`, `SMART_SAVE.md`, `TODO.md`
- `CLAUDE.md`, `CLAUDE-RECOVERY-PROMPT.md`, `SESSION-RECOVERY.md`
- `TASK-MATRIX.md`, `DRY_MAINTAINABILITY_ANALYSIS.md`
- `TESTING_METHODOLOGY_VALIDATION.md`
- `PR-DESCRIPTION*.md`, `PR-READINESS*.md`

### Git and CI
- `.git/`, `.github/workflows/`, `.releaseexclude`

### Claude Code Internal Files
- `.claude/settings.local.json`
- `.claude/skills/`, `.claude/agents/`, `.claude/utils/`

### Scripts (Internal Dev Tools)
- `scripts/publish-to-main.sh`, `scripts/publish-to-main.ps1`

### Python Artifacts
- `__pycache__/`, `*.pyc`, `*.pyo`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `*.egg-info/`, `dist/`, `build/`, `.eggs/`

### Virtual Environments
- `.venv/`, `venv/`, `env/`

### IDE and Editor Files
- `.vscode/`, `.idea/`
- `*.swp`, `*.swo`, `*~`

### OS Files
- `.DS_Store`, `Thumbs.db`

### Environment and Secrets
- `.env`, `.env.local`, `.env.development`
- `.env.test`, `.env.production`

### Logs and Temp Files
- `*.log`, `*.tmp`, `*.temp`
- `.tmp/`, `.temp/`, `tmpclaude-*`

### Coverage and Test Artifacts
- `coverage/`, `.coverage`, `htmlcov/`

### Data Directories
- `memory_slots/`, `shared_memories/`
- `archives/`, `cache/`, `logs/`

## How It Works

1. **Fetches** the latest state from the target remote
2. **Compares** local commits against the remote branch
3. **Checks** if any excluded files are in the commits to be published
4. **If no excluded files**: Pushes directly to the target
5. **If excluded files found**:
   - Creates a temporary branch
   - Removes excluded files from git tracking (keeps them locally)
   - Commits the cleanup
   - Pushes to the target remote
   - Cleans up the temporary branch

## Comparison with GitHub Actions Workflow

For automated releases with more features (PR creation, release tagging, etc.), use the GitHub Actions workflow:

```bash
# Trigger via GitHub CLI
gh workflow run release-sync.yml -f release_version=v2.4.0 -f dry_run=true
```

| Feature | Local Scripts | GitHub Workflow |
|---------|---------------|-----------------|
| Runs on | Your machine | GitHub runners |
| Sync method | Git push | rsync |
| PR creation | No | Yes |
| Release tagging | No | Yes |
| Force replace mode | No | Yes |
| Authentication | Local git config | `RELEASE_PAT` secret |

## Troubleshooting

### "Not in a git repository"
Run the script from within the memcord repository directory.

### "You have uncommitted changes"
Commit or stash your changes before running the script:
```bash
git stash
# run script
git stash pop
```

### "Could not fetch from origin"
Verify your remote is configured correctly:
```bash
git remote -v
git fetch origin
```

### Remote branch doesn't exist
For first-time publish, create the branch on the remote first or push with `-u`:
```bash
git push -u origin main
```
