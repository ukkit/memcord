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

# Update claude_desktop_config.json with actual path
echo "📝 Updating claude_desktop_config.json with installation path..."
if [ -f "claude_desktop_config.json" ]; then
    # Use sed to replace the placeholder path with actual path
    sed -i "s|</path/to/memcord>|$MEMCORD_PATH|g" claude_desktop_config.json
    echo "✅ Updated claude_desktop_config.json with path: $MEMCORD_PATH"
else
    echo "⚠️  claude_desktop_config.json not found in repository"
fi

# Update README.md with actual path
echo "📝 Updating README.md with installation path..."
if [ -f "README.md" ]; then
    # Use sed to replace the placeholder path with actual path
    sed -i "s|</path/to/memcord>|$MEMCORD_PATH|g" README.md
    echo "✅ Updated README.md with path: $MEMCORD_PATH"
else
    echo "⚠️  README.md not found in repository"
fi

echo "✨ Installation complete!"
echo "📂 Memcord installed at: $MEMCORD_PATH"
echo "🔧 To activate the virtual environment later, run: source $MEMCORD_PATH/.venv/bin/activate"