# Memcord Installation Script for Windows
# Run with: irm https://github.com/ukkit/memcord/raw/main/install.ps1 | iex
# Or: PowerShell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Installing Memcord..." -ForegroundColor Cyan

# Clone the repository
Write-Host "📦 Cloning repository..." -ForegroundColor Yellow
git clone https://github.com/ukkit/memcord.git
Set-Location memcord

# Get the absolute path
$MEMCORD_PATH = (Get-Location).Path
Write-Host "📍 Installation path: $MEMCORD_PATH" -ForegroundColor Green

# Data protection check
Write-Host "🛡️  Checking for existing memory data..." -ForegroundColor Yellow
if (Test-Path "memory_slots") {
    $files = Get-ChildItem "memory_slots" -ErrorAction SilentlyContinue
    if ($files) {
        Write-Host "⚠️  EXISTING MEMORY DATA DETECTED!" -ForegroundColor Red
        Write-Host "📊 Running data protection script..." -ForegroundColor Yellow

        if (Test-Path "utilities/protect_data.py") {
            python utilities/protect_data.py --force
            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ Data protection failed - installation aborted!" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "🚨 Data protection script not found!" -ForegroundColor Red
            Write-Host "⚠️  Manual backup recommended:" -ForegroundColor Yellow
            $backupDate = Get-Date -Format "yyyyMMdd"
            Write-Host "   Copy-Item -Recurse memory_slots $env:USERPROFILE\backup_memory_slots_$backupDate" -ForegroundColor Gray

            $response = Read-Host "Continue anyway? [y/N]"
            if ($response -notmatch "^[Yy]$") {
                Write-Host "Installation cancelled for data safety." -ForegroundColor Yellow
                exit 1
            }
        }
    }
} else {
    Write-Host "✅ No existing memory data found - proceeding safely." -ForegroundColor Green
}

# Check if uv is installed
Write-Host "🔍 Checking for uv package manager..." -ForegroundColor Yellow
try {
    $uvVersion = uv --version 2>&1
    Write-Host "✅ Found uv: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  uv not found. Installing uv..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Create virtual environment
Write-Host "🐍 Setting up Python virtual environment..." -ForegroundColor Yellow
uv venv

# Activate virtual environment
Write-Host "📋 Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Install the package
Write-Host "📋 Installing memcord package..." -ForegroundColor Yellow
uv pip install -e .

# Generate MCP configuration files using Python script
Write-Host "📝 Generating MCP configuration files..." -ForegroundColor Yellow
if (Test-Path "scripts/generate-config.py") {
    uv run python scripts/generate-config.py --install-path "$MEMCORD_PATH" --platform windows
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Config generation had issues, but installation can continue." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Config generator script not found - falling back to manual update" -ForegroundColor Yellow

    # Fallback: Update config files manually
    if (Test-Path "config-templates/claude-desktop/config.windows.json") {
        $config = Get-Content "config-templates/claude-desktop/config.windows.json" -Raw
        $config = $config -replace '\{\{MEMCORD_PATH\}\}', ($MEMCORD_PATH -replace '\\', '\\\\')
        $config | Set-Content "claude_desktop_config.json"
        Write-Host "✅ Updated claude_desktop_config.json" -ForegroundColor Green
    }

    if (Test-Path "config-templates/claude-code/mcp.windows.json") {
        $config = Get-Content "config-templates/claude-code/mcp.windows.json" -Raw
        $config = $config -replace '\{\{MEMCORD_PATH\}\}', ($MEMCORD_PATH -replace '\\', '\\\\')
        $config | Set-Content ".mcp.json"
        Write-Host "✅ Updated .mcp.json" -ForegroundColor Green
    }
}

# Update README.md with actual path
Write-Host "📝 Updating README.md with installation path..." -ForegroundColor Yellow
if (Test-Path "README.md") {
    $readme = Get-Content "README.md" -Raw
    $readme = $readme -replace '</path/to/memcord>', $MEMCORD_PATH
    $readme = $readme -replace '\{\{MEMCORD_PATH\}\}', $MEMCORD_PATH
    $readme | Set-Content "README.md"
    Write-Host "✅ Updated README.md with path: $MEMCORD_PATH" -ForegroundColor Green
} else {
    Write-Host "⚠️  README.md not found in repository" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✨ Installation complete!" -ForegroundColor Green
Write-Host "📂 Memcord installed at: $MEMCORD_PATH" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Activate the virtual environment: & $MEMCORD_PATH\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   2. Restart Claude Desktop to load the MCP server" -ForegroundColor Gray
Write-Host "   3. In Claude Code, run: claude mcp list" -ForegroundColor Gray
Write-Host ""
Write-Host "📚 Configuration files generated:" -ForegroundColor Yellow
Write-Host "   - .mcp.json (Claude Code)" -ForegroundColor Gray
Write-Host "   - claude_desktop_config.json (Claude Desktop)" -ForegroundColor Gray
Write-Host "   - .vscode\mcp.json (VSCode/GitHub Copilot)" -ForegroundColor Gray
Write-Host "   - .antigravity\mcp_config.json (Google Antigravity IDE)" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Optional: Enable auto-save hooks for Claude Code:" -ForegroundColor Yellow
Write-Host "   uv run python scripts/generate-config.py --install-hooks" -ForegroundColor Gray
Write-Host ""
Write-Host "📋 Claude Desktop config location:" -ForegroundColor Yellow
Write-Host "   Copy claude_desktop_config.json to:" -ForegroundColor Gray
Write-Host "   $env:APPDATA\Claude\claude_desktop_config.json" -ForegroundColor Cyan
