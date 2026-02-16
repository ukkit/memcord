#!/bin/bash

set -e

echo "🚀 Installing Memcord..."

# Clone the repository
echo "📦 Cloning repository..."
git clone https://github.com/ukkit/memcord.git
cd memcord

# Get the absolute path
MEMCORD_PATH=$(pwd)
echo "📍 Installation path: $MEMCORD_PATH"

# Data protection check
echo "🛡️  Checking for existing memory data..."
if [ -d "memory_slots" ] && [ "$(ls -A memory_slots 2>/dev/null)" ]; then
    echo "⚠️  EXISTING MEMORY DATA DETECTED!"
    echo "📊 Running data protection script..."

    if [ -f "utilities/protect_data.py" ]; then
        python3 utilities/protect_data.py --force
        if [ $? -ne 0 ]; then
            echo "❌ Data protection failed - installation aborted!"
            exit 1
        fi
    else
        echo "🚨 Data protection script not found!"
        echo "⚠️  Manual backup recommended:"
        echo "   cp -r memory_slots ~/backup_memory_slots_$(date +%Y%m%d)"
        read -p "Continue anyway? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled for data safety."
            exit 1
        fi
    fi
else
    echo "✅ No existing memory data found - proceeding safely."
fi

# Create and activate virtual environment
echo "🐍 Setting up Python virtual environment..."
uv venv
source .venv/bin/activate

# Install the package
echo "📋 Installing memcord package..."
uv pip install -e .

# Generate MCP configuration files using Python script
echo "📝 Generating MCP configuration files..."
if [ -f "scripts/generate-config.py" ]; then
    uv run python scripts/generate-config.py --install-path "$MEMCORD_PATH"
    if [ $? -ne 0 ]; then
        echo "⚠️  Config generation had issues, but installation can continue."
    fi
else
    echo "⚠️  Config generator script not found - falling back to manual update"
    # Fallback: Update claude_desktop_config.json with actual path
    if [ -f "claude_desktop_config.json" ]; then
        sed "s|{{MEMCORD_PATH}}|$MEMCORD_PATH|g" claude_desktop_config.json > claude_desktop_config.json.tmp && mv claude_desktop_config.json.tmp claude_desktop_config.json
        echo "✅ Updated claude_desktop_config.json"
    fi
fi

# Update README.md with actual path (for documentation purposes)
echo "📝 Updating README.md with installation path..."
if [ -f "README.md" ]; then
    # Replace both old placeholder format and new placeholder format
    sed -e "s|</path/to/memcord>|$MEMCORD_PATH|g" \
        -e "s|{{MEMCORD_PATH}}|$MEMCORD_PATH|g" \
        README.md > README.md.tmp && mv README.md.tmp README.md
    echo "✅ Updated README.md with path: $MEMCORD_PATH"
else
    echo "⚠️  README.md not found in repository"
fi

echo ""
echo "✨ Installation complete!"
echo "📂 Memcord installed at: $MEMCORD_PATH"
echo ""
echo "🔧 Next steps:"
echo "   1. Activate the virtual environment: source $MEMCORD_PATH/.venv/bin/activate"
echo "   2. Restart Claude Desktop to load the MCP server"
echo "   3. In Claude Code, run: claude mcp list"
echo ""
echo "📚 Configuration files generated:"
echo "   - .mcp.json (Claude Code)"
echo "   - claude_desktop_config.json (Claude Desktop)"
echo "   - .vscode/mcp.json (VSCode/GitHub Copilot)"
echo "   - .antigravity/mcp_config.json (Google Antigravity IDE)"
echo ""
echo "💡 Optional: Enable auto-save hooks for Claude Code:"
echo "   uv run python scripts/generate-config.py --install-hooks"