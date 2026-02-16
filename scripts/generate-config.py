#!/usr/bin/env python3
"""
Cross-platform MCP configuration generator for memcord.

This script generates platform-appropriate MCP configuration files
by replacing {{MEMCORD_PATH}} placeholders with the actual installation path.

Usage:
    python scripts/generate-config.py                    # Auto-detect path
    python scripts/generate-config.py --install-path /path/to/memcord
    python scripts/generate-config.py --platform windows  # Force platform
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, cast

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# ANSI colors (disabled on Windows unless terminal supports it)
if IS_WINDOWS:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        COLORS_ENABLED = True
    except Exception:
        COLORS_ENABLED = False
else:
    COLORS_ENABLED = True


def color(text: str, code: str) -> str:
    """Apply ANSI color code to text."""
    if not COLORS_ENABLED:
        return text
    codes = {"green": "32", "yellow": "33", "red": "31", "cyan": "36", "bold": "1"}
    return f"\033[{codes.get(code, '0')}m{text}\033[0m"


def get_memcord_path() -> Path:
    """Get the memcord installation directory."""
    # Script is in scripts/, so parent is memcord root
    return Path(__file__).parent.parent.resolve()


def get_claude_desktop_config_path() -> Path | None:
    """Get the Claude Desktop config file path for current platform."""
    if IS_MACOS:
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif IS_WINDOWS:
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif IS_LINUX:
        # Linux uses XDG config or .config
        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(xdg_config) / "Claude" / "claude_desktop_config.json"
    return None


def get_claude_code_config_path() -> Path | None:
    """Get the Claude Code .mcp.json path (project-level)."""
    return get_memcord_path() / ".mcp.json"


def load_template(template_path: Path) -> dict[str, Any]:
    """Load a JSON template file."""
    with open(template_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def replace_placeholders(config: dict[str, Any], memcord_path: str, use_backslashes: bool = False) -> dict[str, Any]:
    """Replace {{MEMCORD_PATH}} placeholders in config."""
    config_str = json.dumps(config)

    # Normalize path for the platform
    if use_backslashes:
        # Windows: use double backslashes in JSON
        path_for_json = memcord_path.replace("\\", "\\\\")
    else:
        # Unix: use forward slashes
        path_for_json = memcord_path.replace("\\", "/")

    config_str = config_str.replace("{{MEMCORD_PATH}}", path_for_json)
    return cast(dict[str, Any], json.loads(config_str))


def save_config(config: dict, output_path: Path, dry_run: bool = False) -> bool:
    """Save configuration to file."""
    if dry_run:
        print(f"  {color('[DRY RUN]', 'yellow')} Would write to: {output_path}")
        return True

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"  {color('Error:', 'red')} Failed to write {output_path}: {e}")
        return False


def load_hooks_template(templates_dir: Path) -> dict[str, Any]:
    """Load the Claude Code hooks template."""
    hooks_path = templates_dir / "claude-code" / "hooks.json"
    if not hooks_path.exists():
        print(f"  {color('Error:', 'red')} Hooks template not found: {hooks_path}")
        return {}
    return load_template(hooks_path)


def merge_hooks(existing: dict[str, Any], new_hooks: dict[str, Any]) -> dict[str, Any]:
    """Merge memcord hooks into existing Claude Code settings.

    Deduplicates by checking for 'memcord:' prefix in hook descriptions.
    Preserves all non-memcord hooks and other settings.
    """
    result = existing.copy()

    if "hooks" not in new_hooks:
        return result

    if "hooks" not in result:
        result["hooks"] = {}

    for event_key, hook_entries in new_hooks["hooks"].items():
        if event_key not in result["hooks"]:
            result["hooks"][event_key] = []

        # Remove existing memcord hooks (deduplication)
        result["hooks"][event_key] = [
            hook for hook in result["hooks"][event_key]
            if not hook.get("description", "").startswith("memcord:")
        ]

        # Add new memcord hooks
        result["hooks"][event_key].extend(hook_entries)

    return result


def install_hooks(
    memcord_path: Path,
    templates_dir: Path,
    dry_run: bool = False,
    verbose: bool = True,
) -> bool:
    """Install Claude Code agent hooks for auto-save."""
    if verbose:
        print(f"\n{color('[Hooks]', 'green')} Claude Code Auto-Save Hooks")

    hooks_template = load_hooks_template(templates_dir)
    if not hooks_template:
        return False

    settings_path = memcord_path / ".claude" / "settings.json"

    # Load existing settings or start fresh
    existing = {}
    if settings_path.exists():
        try:
            existing = load_template(settings_path)
        except Exception as e:
            if verbose:
                print(f"  {color('Warning:', 'yellow')} Could not read existing settings: {e}")
            existing = {}

    merged = merge_hooks(existing, hooks_template)

    if dry_run:
        print(f"  {color('[DRY RUN]', 'yellow')} Would write hooks to: {settings_path}")
        if verbose:
            hook_events = list(hooks_template.get("hooks", {}).keys())
            print(f"  Hook events: {', '.join(hook_events)}")
        return True

    if save_config(merged, settings_path):
        if verbose:
            print(f"  {color('Installed:', 'green')} {settings_path}")
            hook_events = list(hooks_template.get("hooks", {}).keys())
            print(f"  Hook events: {', '.join(hook_events)}")
        return True
    return False


def merge_mcp_servers(existing: dict, new_servers: dict) -> dict:
    """Merge new MCP servers into existing config without overwriting other servers."""
    result = existing.copy()

    # Handle both "mcpServers" and "servers" keys
    for key in ["mcpServers", "servers"]:
        if key in new_servers:
            if key not in result:
                result[key] = {}
            result[key].update(new_servers[key])

    return result


def generate_configs(
    memcord_path: Path,
    force_platform: str | None = None,
    install_claude_desktop: bool = True,
    install_claude_code: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
) -> bool:
    """Generate all configuration files."""

    templates_dir = memcord_path / "config-templates"
    if not templates_dir.exists():
        print(f"{color('Error:', 'red')} config-templates directory not found at {templates_dir}")
        return False

    # Determine platform
    if force_platform:
        is_windows = force_platform.lower() == "windows"
    else:
        is_windows = IS_WINDOWS

    platform_name = "Windows" if is_windows else ("macOS" if IS_MACOS else "Linux")
    path_str = str(memcord_path)

    if verbose:
        print(f"\n{color('Memcord Configuration Generator', 'bold')}")
        print(f"{'=' * 40}")
        print(f"Platform: {color(platform_name, 'cyan')}")
        print(f"Memcord path: {color(path_str, 'cyan')}")
        print()

    success = True

    # 1. Generate Claude Desktop config
    if install_claude_desktop:
        if verbose:
            print(f"{color('[1/2]', 'green')} Claude Desktop Configuration")

        template_name = "config.windows.json" if is_windows else "config.json"
        template_path = templates_dir / "claude-desktop" / template_name

        if template_path.exists():
            template = load_template(template_path)
            config = replace_placeholders(template, path_str, use_backslashes=is_windows)

            # Save to project directory (for reference)
            project_config = memcord_path / "claude_desktop_config.json"
            if save_config(config, project_config, dry_run):
                if verbose:
                    print(f"  {color('Created:', 'green')} {project_config}")
            else:
                success = False

            # Also save/merge to system Claude Desktop config location
            system_config_path = get_claude_desktop_config_path()
            if system_config_path:
                if system_config_path.exists():
                    try:
                        existing = load_template(system_config_path)
                        merged = merge_mcp_servers(existing, config)
                        if save_config(merged, system_config_path, dry_run):
                            if verbose:
                                print(f"  {color('Merged into:', 'green')} {system_config_path}")
                    except Exception as e:
                        if verbose:
                            print(f"  {color('Note:', 'yellow')} Could not merge into system config: {e}")
                else:
                    if verbose:
                        print(f"  {color('Note:', 'yellow')} System config not found at {system_config_path}")
                        print(f"       Copy {project_config} there after Claude Desktop is installed.")
        else:
            print(f"  {color('Warning:', 'yellow')} Template not found: {template_path}")

    # 2. Generate Claude Code .mcp.json
    if install_claude_code:
        if verbose:
            print(f"\n{color('[2/2]', 'green')} Claude Code Configuration")

        template_name = "mcp.windows.json" if is_windows else "mcp.json"
        template_path = templates_dir / "claude-code" / template_name

        if template_path.exists():
            template = load_template(template_path)
            config = replace_placeholders(template, path_str, use_backslashes=is_windows)

            output_path = memcord_path / ".mcp.json"
            if save_config(config, output_path, dry_run):
                if verbose:
                    print(f"  {color('Created:', 'green')} {output_path}")
            else:
                success = False
        else:
            print(f"  {color('Warning:', 'yellow')} Template not found: {template_path}")

    # 3. Copy VSCode config (uses ${workspaceFolder}, no path replacement needed)
    vscode_template = templates_dir / "vscode" / "mcp.json"
    vscode_dest = memcord_path / ".vscode" / "mcp.json"
    if vscode_template.exists():
        if not dry_run:
            shutil.copy2(vscode_template, vscode_dest)
        if verbose:
            print(f"\n{color('[Bonus]', 'green')} VSCode/GitHub Copilot Configuration")
            print(f"  {color('Created:', 'green')} {vscode_dest}")

    # 4. Update Antigravity config
    antigravity_template = templates_dir / "antigravity" / "mcp_config.json"
    antigravity_dest = memcord_path / ".antigravity" / "mcp_config.json"
    if antigravity_template.exists():
        template = load_template(antigravity_template)
        config = replace_placeholders(template, path_str, use_backslashes=False)  # Antigravity uses Unix paths
        if save_config(config, antigravity_dest, dry_run):
            if verbose:
                print(f"\n{color('[Bonus]', 'green')} Google Antigravity IDE Configuration")
                print(f"  {color('Created:', 'green')} {antigravity_dest}")

    if verbose:
        print(f"\n{'=' * 40}")
        if success:
            print(f"{color('Configuration complete!', 'green')}")
            print("\nNext steps:")
            print("  1. Restart Claude Desktop (if using)")
            print(f"  2. Run: {color('claude mcp list', 'cyan')} to verify Claude Code sees memcord")
            print(f"  3. Test with: {color('/mcp', 'cyan')} command in Claude Code")
        else:
            print(f"{color('Configuration completed with errors.', 'yellow')}")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Generate MCP configuration files for memcord",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate-config.py                     # Auto-detect everything
  python scripts/generate-config.py --dry-run           # Preview changes
  python scripts/generate-config.py --platform windows  # Force Windows configs
  python scripts/generate-config.py --install-path /custom/path
        """,
    )

    parser.add_argument("--install-path", type=str, help="Override the memcord installation path")

    parser.add_argument(
        "--platform", choices=["windows", "unix", "auto"], default="auto", help="Force platform (default: auto-detect)"
    )

    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output except errors")

    parser.add_argument("--no-claude-desktop", action="store_true", help="Skip Claude Desktop configuration")

    parser.add_argument("--no-claude-code", action="store_true", help="Skip Claude Code .mcp.json configuration")

    parser.add_argument(
        "--install-hooks", action="store_true", help="Install Claude Code agent hooks for auto-save on compaction and session end"
    )

    args = parser.parse_args()

    # Determine memcord path
    if args.install_path:
        memcord_path = Path(args.install_path).resolve()
    else:
        memcord_path = get_memcord_path()

    # Validate path
    if not memcord_path.exists():
        print(f"{color('Error:', 'red')} Memcord path does not exist: {memcord_path}")
        sys.exit(1)

    # Determine platform override
    force_platform = None
    if args.platform != "auto":
        force_platform = args.platform

    # Generate configs
    success = generate_configs(
        memcord_path=memcord_path,
        force_platform=force_platform,
        install_claude_desktop=not args.no_claude_desktop,
        install_claude_code=not args.no_claude_code,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )

    # Install hooks if requested
    if args.install_hooks:
        templates_dir = memcord_path / "config-templates"
        hooks_ok = install_hooks(
            memcord_path=memcord_path,
            templates_dir=templates_dir,
            dry_run=args.dry_run,
            verbose=not args.quiet,
        )
        if not hooks_ok:
            success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
