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