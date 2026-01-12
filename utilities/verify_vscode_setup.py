#!/usr/bin/env python3
"""
Verification script for memcord VSCode integration.

This script checks if memcord is correctly configured for use with
VSCode and GitHub Copilot agent mode.

Usage:
    python utilities/verify_vscode_setup.py
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {text}")


def check_python_version() -> bool:
    """Check if Python version is 3.10 or higher."""
    version = sys.version_info
    if version >= (3, 10):
        print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} detected")
        print_error("Python 3.10 or higher is required")
        return False


def check_uv_installed() -> bool:
    """Check if uv package manager is installed."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"uv package manager found: {version}")
            return True
        else:
            print_error("uv package manager not working properly")
            return False
    except FileNotFoundError:
        print_error("uv package manager not found")
        print_info("Install from: https://github.com/astral-sh/uv")
        return False
    except subprocess.TimeoutExpired:
        print_error("uv command timed out")
        return False


def find_vscode_config_paths() -> List[Path]:
    """Find possible VSCode configuration paths based on platform."""
    system = platform.system()
    home = Path.home()

    paths = []

    if system == "Windows":
        paths.extend([
            home / "AppData" / "Roaming" / "Code" / "User" / "mcp.json",
            home / "AppData" / "Roaming" / "Code - Insiders" / "User" / "mcp.json",
        ])
    elif system == "Darwin":  # macOS
        paths.extend([
            home / "Library" / "Application Support" / "Code" / "User" / "mcp.json",
            home / "Library" / "Application Support" / "Code - Insiders" / "User" / "mcp.json",
        ])
    else:  # Linux
        paths.extend([
            home / ".config" / "Code" / "User" / "mcp.json",
            home / ".config" / "Code - Insiders" / "User" / "mcp.json",
        ])

    return paths


def find_mcp_config() -> Optional[Tuple[Path, Dict]]:
    """Find and load MCP configuration file."""
    # Check workspace configurations first
    workspace_configs = [
        Path(".vscode") / "mcp.json",
        Path(".mcp.json"),
    ]

    for config_path in workspace_configs:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                print_success(f"Found workspace configuration: {config_path}")
                return (config_path, config)
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON in {config_path}: {e}")
                return None
            except Exception as e:
                print_error(f"Error reading {config_path}: {e}")
                return None

    # Check user profile configurations
    user_configs = find_vscode_config_paths()

    for config_path in user_configs:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                print_success(f"Found user configuration: {config_path}")
                return (config_path, config)
            except json.JSONDecodeError as e:
                print_error(f"Invalid JSON in {config_path}: {e}")
                return None
            except Exception as e:
                print_error(f"Error reading {config_path}: {e}")
                return None

    print_error("No MCP configuration found")
    print_info("Expected locations:")
    print_info("  - .vscode/mcp.json (workspace)")
    print_info("  - .mcp.json (workspace root)")
    for path in user_configs:
        print_info(f"  - {path} (user profile)")

    return None


def check_memcord_config(config: Dict) -> bool:
    """Check if memcord is configured in MCP config."""
    servers = config.get("servers", {})

    if "memcord" not in servers:
        print_error("memcord server not found in configuration")
        print_info("Add memcord to the 'servers' section of mcp.json")
        return False

    memcord_config = servers["memcord"]
    print_success("memcord server found in configuration")

    # Check command
    command = memcord_config.get("command")
    if command != "uv":
        print_warning(f"Command is '{command}', expected 'uv'")

    # Check args
    args = memcord_config.get("args", [])
    if "--directory" not in args or "run" not in args or "memcord" not in args:
        print_warning("Args may be incorrect")
        print_info(f"Current args: {args}")
        print_info("Expected: ['--directory', '<path>', 'run', 'memcord']")

    # Check PYTHONPATH
    env = memcord_config.get("env", {})
    pythonpath = env.get("PYTHONPATH")
    if not pythonpath:
        print_warning("PYTHONPATH not set in environment")
    else:
        print_success(f"PYTHONPATH set to: {pythonpath}")

    # Check advanced mode
    advanced = env.get("MEMCORD_ENABLE_ADVANCED", "false")
    if advanced.lower() == "true":
        print_info("Advanced mode enabled (19 tools)")
    else:
        print_info("Basic mode enabled (11 tools)")

    return True


def check_memcord_installation() -> bool:
    """Check if memcord is installed and can be imported."""
    try:
        # Try to import memcord
        import memcord
        print_success("memcord package is installed")

        # Try to get version
        try:
            from memcord import __version__
            print_success(f"memcord version: {__version__}")
        except ImportError:
            print_info("memcord version not available")

        return True
    except ImportError:
        print_error("memcord package not found")
        print_info("Run: uv pip install -e . (from memcord directory)")
        return False


def check_memcord_server() -> bool:
    """Check if memcord server can start."""
    try:
        # Try to import and instantiate server
        from memcord.server import ChatMemoryServer
        server = ChatMemoryServer()
        print_success("memcord server can be instantiated")
        return True
    except Exception as e:
        print_error(f"memcord server initialization failed: {e}")
        return False


def check_vscode_version() -> bool:
    """Check VSCode version (if available)."""
    try:
        result = subprocess.run(
            ["code", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            version = lines[0] if lines else "unknown"
            print_success(f"VSCode version: {version}")

            # Try to parse version and check if >= 1.102
            try:
                major, minor, *_ = version.split('.')
                if int(major) > 1 or (int(major) == 1 and int(minor) >= 102):
                    print_success("VSCode version supports MCP (1.102+)")
                    return True
                else:
                    print_warning("VSCode version may not support MCP")
                    print_info("MCP support requires VSCode 1.102 or higher")
                    return False
            except (ValueError, IndexError):
                print_info("Could not parse VSCode version")
                return True
        else:
            print_warning("Could not check VSCode version")
            return True
    except FileNotFoundError:
        print_warning("VSCode 'code' command not found")
        print_info("VSCode may not be in PATH, but could still be installed")
        return True
    except subprocess.TimeoutExpired:
        print_warning("VSCode version check timed out")
        return True


def check_memory_directories() -> bool:
    """Check if memory directories exist and are writable."""
    directories = [
        Path("memory_slots"),
        Path("shared_memories"),
        Path("archives"),
    ]

    all_ok = True

    for directory in directories:
        if directory.exists():
            if os.access(directory, os.W_OK):
                print_success(f"Directory exists and is writable: {directory}")
            else:
                print_warning(f"Directory exists but not writable: {directory}")
                all_ok = False
        else:
            print_info(f"Directory will be created on first use: {directory}")

    return all_ok


def print_summary(checks: Dict[str, bool]) -> None:
    """Print summary of all checks."""
    print_header("Verification Summary")

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    print(f"\nChecks passed: {passed}/{total}\n")

    for check_name, passed in checks.items():
        if passed:
            print_success(check_name)
        else:
            print_error(check_name)

    if all(checks.values()):
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed! ✓{Colors.RESET}")
        print(f"{Colors.GREEN}memcord is ready to use with VSCode and GitHub Copilot{Colors.RESET}\n")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Some checks failed or need attention{Colors.RESET}")
        print(f"{Colors.YELLOW}Review the warnings and errors above{Colors.RESET}\n")
        print_info("See docs/vscode-setup.md for detailed setup instructions")


def main() -> int:
    """Main verification function."""
    print_header("Memcord VSCode Setup Verification")

    checks = {}

    # Check Python version
    print_info("Checking Python version...")
    checks["Python 3.10+"] = check_python_version()

    # Check uv
    print_info("\nChecking uv package manager...")
    checks["uv package manager"] = check_uv_installed()

    # Check VSCode version
    print_info("\nChecking VSCode version...")
    checks["VSCode 1.102+"] = check_vscode_version()

    # Find and check MCP config
    print_info("\nChecking MCP configuration...")
    config_result = find_mcp_config()
    if config_result:
        config_path, config = config_result
        checks["MCP configuration found"] = True
        checks["memcord configured"] = check_memcord_config(config)
    else:
        checks["MCP configuration found"] = False
        checks["memcord configured"] = False

    # Check memcord installation
    print_info("\nChecking memcord installation...")
    checks["memcord installed"] = check_memcord_installation()

    if checks.get("memcord installed", False):
        checks["memcord server"] = check_memcord_server()

    # Check memory directories
    print_info("\nChecking memory directories...")
    checks["memory directories"] = check_memory_directories()

    # Print summary
    print_summary(checks)

    # Return exit code
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
