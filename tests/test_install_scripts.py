"""
Tests for installation scripts and configuration generator.

These tests verify that:
- install.sh (Bash) has correct structure and functionality
- install.ps1 (PowerShell) has correct structure and functionality
- scripts/generate-config.py works correctly for all platforms
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# =============================================================================
# Test install.sh (Bash Installation Script) - 12 tests
# =============================================================================


class TestInstallShScript:
    """Tests for the install.sh Bash installation script."""

    @pytest.fixture
    def script_path(self):
        """Get the path to install.sh."""
        return Path("install.sh")

    @pytest.fixture
    def script_content(self, script_path):
        """Load the install.sh script content."""
        with open(script_path, encoding="utf-8") as f:
            return f.read()

    def test_script_exists(self, script_path):
        """Test that install.sh exists in the repository root."""
        assert script_path.exists(), "install.sh should exist in repository root"

    def test_script_has_shebang(self, script_content):
        """Test that install.sh starts with proper bash shebang."""
        assert script_content.startswith("#!/bin/bash"), "install.sh should start with #!/bin/bash shebang"

    def test_script_uses_set_e(self, script_content):
        """Test that install.sh uses 'set -e' for error handling."""
        assert "set -e" in script_content, "install.sh should use 'set -e' to exit on errors"

    def test_script_clones_correct_repo(self, script_content):
        """Test that install.sh clones from the correct GitHub repository."""
        assert "git clone https://github.com/ukkit/memcord.git" in script_content, (
            "install.sh should clone from correct GitHub URL"
        )

    def test_script_checks_existing_data(self, script_content):
        """Test that install.sh checks for existing memory_slots data."""
        assert "memory_slots" in script_content, "install.sh should check for existing memory_slots directory"
        assert "EXISTING MEMORY DATA DETECTED" in script_content, "install.sh should warn about existing data"

    def test_script_runs_data_protection(self, script_content):
        """Test that install.sh runs data protection script when needed."""
        assert "utilities/protect_data.py" in script_content, "install.sh should reference data protection script"
        assert "python3 utilities/protect_data.py" in script_content, (
            "install.sh should run data protection with python3"
        )

    def test_script_creates_venv(self, script_content):
        """Test that install.sh creates virtual environment with uv."""
        assert "uv venv" in script_content, "install.sh should create virtual environment with uv"
        assert "source .venv/bin/activate" in script_content, "install.sh should activate the virtual environment"

    def test_script_installs_package(self, script_content):
        """Test that install.sh installs the memcord package."""
        assert "uv pip install -e ." in script_content, "install.sh should install memcord in editable mode"

    def test_script_calls_config_generator(self, script_content):
        """Test that install.sh calls the config generator script."""
        assert "scripts/generate-config.py" in script_content, "install.sh should call generate-config.py"
        assert "--install-path" in script_content, "install.sh should pass --install-path to config generator"

    def test_script_updates_readme(self, script_content):
        """Test that install.sh updates README.md with installation path."""
        assert "README.md" in script_content, "install.sh should reference README.md"
        assert "{{MEMCORD_PATH}}" in script_content, "install.sh should replace {{MEMCORD_PATH}} placeholder"

    def test_script_shows_next_steps(self, script_content):
        """Test that install.sh displays next steps after installation."""
        assert "Next steps:" in script_content, "install.sh should show next steps"
        assert "Restart Claude Desktop" in script_content, "install.sh should mention restarting Claude Desktop"
        assert "claude mcp list" in script_content, "install.sh should mention 'claude mcp list' command"

    def test_script_lists_generated_configs(self, script_content):
        """Test that install.sh lists all generated configuration files."""
        assert ".mcp.json" in script_content, "install.sh should mention .mcp.json"
        assert "claude_desktop_config.json" in script_content, "install.sh should mention claude_desktop_config.json"
        assert ".vscode/mcp.json" in script_content, "install.sh should mention .vscode/mcp.json"
        assert ".antigravity/mcp_config.json" in script_content, (
            "install.sh should mention .antigravity/mcp_config.json"
        )


# =============================================================================
# Test install.ps1 (PowerShell Installation Script) - 12 tests
# =============================================================================


class TestInstallPs1Script:
    """Tests for the install.ps1 PowerShell installation script."""

    @pytest.fixture
    def script_path(self):
        """Get the path to install.ps1."""
        return Path("install.ps1")

    @pytest.fixture
    def script_content(self, script_path):
        """Load the install.ps1 script content."""
        with open(script_path, encoding="utf-8") as f:
            return f.read()

    def test_script_exists(self, script_path):
        """Test that install.ps1 exists in the repository root."""
        assert script_path.exists(), "install.ps1 should exist in repository root"

    def test_script_uses_error_action_stop(self, script_content):
        """Test that install.ps1 uses ErrorActionPreference Stop."""
        assert '$ErrorActionPreference = "Stop"' in script_content, (
            "install.ps1 should set ErrorActionPreference to Stop"
        )

    def test_script_clones_correct_repo(self, script_content):
        """Test that install.ps1 clones from the correct GitHub repository."""
        assert "git clone https://github.com/ukkit/memcord.git" in script_content, (
            "install.ps1 should clone from correct GitHub URL"
        )

    def test_script_checks_existing_data(self, script_content):
        """Test that install.ps1 checks for existing memory_slots data."""
        assert "memory_slots" in script_content, "install.ps1 should check for existing memory_slots directory"
        assert "EXISTING MEMORY DATA DETECTED" in script_content, "install.ps1 should warn about existing data"

    def test_script_runs_data_protection(self, script_content):
        """Test that install.ps1 runs data protection script when needed."""
        assert "utilities/protect_data.py" in script_content, "install.ps1 should reference data protection script"
        assert "python utilities/protect_data.py" in script_content, (
            "install.ps1 should run data protection with python"
        )

    def test_script_checks_uv_installed(self, script_content):
        """Test that install.ps1 checks if uv is installed."""
        assert "uv --version" in script_content, "install.ps1 should check for uv installation"
        assert "astral.sh/uv/install.ps1" in script_content, "install.ps1 should install uv if missing"

    def test_script_creates_venv(self, script_content):
        """Test that install.ps1 creates virtual environment with uv."""
        assert "uv venv" in script_content, "install.ps1 should create virtual environment with uv"
        assert ".venv\\Scripts\\Activate.ps1" in script_content, "install.ps1 should activate the virtual environment"

    def test_script_installs_package(self, script_content):
        """Test that install.ps1 installs the memcord package."""
        assert "uv pip install -e ." in script_content, "install.ps1 should install memcord in editable mode"

    def test_script_calls_config_generator_with_platform(self, script_content):
        """Test that install.ps1 calls config generator with Windows platform."""
        assert "scripts/generate-config.py" in script_content, "install.ps1 should call generate-config.py"
        assert "--platform windows" in script_content, "install.ps1 should pass --platform windows to config generator"

    def test_script_updates_readme(self, script_content):
        """Test that install.ps1 updates README.md with installation path."""
        assert "README.md" in script_content, "install.ps1 should reference README.md"
        # PowerShell escapes braces in regex patterns, so check for the escaped version
        assert "MEMCORD_PATH" in script_content, "install.ps1 should replace MEMCORD_PATH placeholder"
        assert "-replace" in script_content, "install.ps1 should use -replace for substitution"

    def test_script_shows_next_steps(self, script_content):
        """Test that install.ps1 displays next steps after installation."""
        assert "Next steps:" in script_content, "install.ps1 should show next steps"
        assert "Restart Claude Desktop" in script_content, "install.ps1 should mention restarting Claude Desktop"
        assert "claude mcp list" in script_content, "install.ps1 should mention 'claude mcp list' command"

    def test_script_shows_claude_desktop_config_location(self, script_content):
        """Test that install.ps1 shows Claude Desktop config location."""
        assert "APPDATA" in script_content, "install.ps1 should reference APPDATA for config location"
        assert "Claude\\claude_desktop_config.json" in script_content, (
            "install.ps1 should show Claude Desktop config path"
        )


# =============================================================================
# Test scripts/generate-config.py (Configuration Generator) - 15 tests
# =============================================================================


class TestGenerateConfigScript:
    """Tests for the generate-config.py configuration generator."""

    @pytest.fixture
    def script_path(self):
        """Get the path to generate-config.py."""
        return Path("scripts/generate-config.py")

    @pytest.fixture
    def script_content(self, script_path):
        """Load the generate-config.py script content."""
        with open(script_path, encoding="utf-8") as f:
            return f.read()

    def test_script_exists(self, script_path):
        """Test that generate-config.py exists."""
        assert script_path.exists(), "generate-config.py should exist in scripts/"

    def test_script_has_shebang(self, script_content):
        """Test that generate-config.py has proper Python shebang."""
        assert script_content.startswith("#!/usr/bin/env python3"), (
            "generate-config.py should start with #!/usr/bin/env python3"
        )

    def test_script_can_be_imported(self):
        """Test that generate-config.py can be imported as a module."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            assert hasattr(module, "main")
            assert hasattr(module, "get_memcord_path")
            assert hasattr(module, "replace_placeholders")
            assert hasattr(module, "generate_configs")
        finally:
            sys.path.pop(0)

    def test_get_memcord_path_returns_correct_path(self):
        """Test that get_memcord_path returns the correct repository root."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            memcord_path = module.get_memcord_path()
            assert memcord_path.exists()
            assert (memcord_path / "pyproject.toml").exists()
        finally:
            sys.path.pop(0)

    def test_replace_placeholders_unix_paths(self):
        """Test placeholder replacement for Unix paths."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            config = {"path": "{{MEMCORD_PATH}}/src"}
            result = module.replace_placeholders(config, "/home/user/memcord", use_backslashes=False)
            assert result["path"] == "/home/user/memcord/src"
        finally:
            sys.path.pop(0)

    def test_replace_placeholders_windows_paths(self):
        """Test placeholder replacement for Windows paths with backslashes."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            config = {"path": "{{MEMCORD_PATH}}\\src"}
            result = module.replace_placeholders(config, "C:\\Users\\test\\memcord", use_backslashes=True)
            # Windows paths get double-escaped in JSON
            assert "C:\\" in result["path"] or "C:/" in result["path"]
        finally:
            sys.path.pop(0)

    def test_load_template_loads_json(self):
        """Test that load_template correctly loads JSON files."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            template_path = Path("config-templates/vscode/mcp.json")
            if template_path.exists():
                config = module.load_template(template_path)
                assert isinstance(config, dict)
                assert "servers" in config
        finally:
            sys.path.pop(0)

    def test_merge_mcp_servers_preserves_existing(self):
        """Test that merge_mcp_servers preserves existing server configs."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            existing = {"mcpServers": {"other-server": {"command": "other"}}}
            new_servers = {"mcpServers": {"memcord": {"command": "uv"}}}
            result = module.merge_mcp_servers(existing, new_servers)

            assert "other-server" in result["mcpServers"]
            assert "memcord" in result["mcpServers"]
        finally:
            sys.path.pop(0)

    def test_save_config_dry_run_mode(self):
        """Test that save_config respects dry_run mode."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "test_config.json"
                config = {"test": "value"}

                # Dry run should not create file
                result = module.save_config(config, output_path, dry_run=True)
                assert result is True
                assert not output_path.exists()
        finally:
            sys.path.pop(0)

    def test_save_config_creates_file(self):
        """Test that save_config creates the config file."""
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("generate_config", "scripts/generate-config.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "test_config.json"
                config = {"test": "value"}

                result = module.save_config(config, output_path, dry_run=False)
                assert result is True
                assert output_path.exists()

                with open(output_path) as f:
                    saved = json.load(f)
                assert saved == config
        finally:
            sys.path.pop(0)

    def test_platform_detection_variables_exist(self, script_content):
        """Test that platform detection variables are defined."""
        assert "IS_WINDOWS" in script_content
        assert "IS_MACOS" in script_content
        assert "IS_LINUX" in script_content
        assert 'sys.platform == "win32"' in script_content
        assert 'sys.platform == "darwin"' in script_content

    def test_script_has_cli_arguments(self, script_content):
        """Test that the script supports CLI arguments."""
        assert "--install-path" in script_content
        assert "--platform" in script_content
        assert "--dry-run" in script_content
        assert "--quiet" in script_content
        assert "--no-claude-desktop" in script_content
        assert "--no-claude-code" in script_content

    def test_script_handles_all_config_types(self, script_content):
        """Test that the script handles all configuration types."""
        assert "claude-desktop" in script_content
        assert "claude-code" in script_content
        assert "vscode" in script_content
        assert "antigravity" in script_content

    def test_get_claude_desktop_config_path_logic(self, script_content):
        """Test that Claude Desktop config path logic covers all platforms."""
        assert "Library" in script_content  # macOS
        assert "APPDATA" in script_content  # Windows
        assert "XDG_CONFIG_HOME" in script_content  # Linux
        assert ".config" in script_content  # Linux fallback

    def test_script_has_color_output_support(self, script_content):
        """Test that the script supports colored output."""
        assert "ANSI" in script_content or "color" in script_content
        assert "\\033[" in script_content  # ANSI escape codes


# =============================================================================
# Test Config Templates Existence and Validity - 10 tests
# =============================================================================


class TestConfigTemplates:
    """Tests for configuration template files."""

    def test_config_templates_directory_exists(self):
        """Test that config-templates directory exists."""
        assert Path("config-templates").exists()
        assert Path("config-templates").is_dir()

    def test_vscode_template_exists(self):
        """Test that VSCode template exists."""
        assert Path("config-templates/vscode/mcp.json").exists()

    def test_claude_code_template_exists(self):
        """Test that Claude Code templates exist."""
        assert Path("config-templates/claude-code/mcp.json").exists()
        assert Path("config-templates/claude-code/mcp.windows.json").exists()

    def test_claude_desktop_template_exists(self):
        """Test that Claude Desktop templates exist."""
        assert Path("config-templates/claude-desktop/config.json").exists()
        assert Path("config-templates/claude-desktop/config.windows.json").exists()

    def test_antigravity_template_exists(self):
        """Test that Antigravity template exists."""
        assert Path("config-templates/antigravity/mcp_config.json").exists()

    def test_vscode_template_valid_json(self):
        """Test that VSCode template is valid JSON."""
        with open("config-templates/vscode/mcp.json") as f:
            config = json.load(f)
        assert "servers" in config

    def test_claude_code_template_valid_json(self):
        """Test that Claude Code template is valid JSON."""
        with open("config-templates/claude-code/mcp.json") as f:
            config = json.load(f)
        assert "mcpServers" in config

    def test_claude_desktop_template_valid_json(self):
        """Test that Claude Desktop template is valid JSON."""
        with open("config-templates/claude-desktop/config.json") as f:
            config = json.load(f)
        assert "mcpServers" in config

    def test_templates_have_memcord_server(self):
        """Test that all templates define memcord server."""
        templates = [
            ("config-templates/vscode/mcp.json", "servers"),
            ("config-templates/claude-code/mcp.json", "mcpServers"),
            ("config-templates/claude-desktop/config.json", "mcpServers"),
        ]

        for template_path, servers_key in templates:
            with open(template_path) as f:
                config = json.load(f)
            assert "memcord" in config[servers_key], f"Template {template_path} should define memcord server"

    def test_templates_use_uv_command(self):
        """Test that all templates use uv as the command."""
        templates = [
            ("config-templates/vscode/mcp.json", "servers"),
            ("config-templates/claude-code/mcp.json", "mcpServers"),
            ("config-templates/claude-desktop/config.json", "mcpServers"),
        ]

        for template_path, servers_key in templates:
            with open(template_path) as f:
                config = json.load(f)
            assert config[servers_key]["memcord"]["command"] == "uv", (
                f"Template {template_path} should use 'uv' command"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
