"""Tests for generate-config.py hook merge logic."""

import json
import sys
from pathlib import Path

import pytest

# Add scripts directory to path so we can import generate-config
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import with hyphen workaround
import importlib.util

spec = importlib.util.spec_from_file_location("generate_config", scripts_dir / "generate-config.py")
generate_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_config)

merge_hooks = generate_config.merge_hooks


class TestHooksTemplate:
    """Test that the hooks template file is valid."""

    def test_hooks_template_is_valid_json(self):
        template_path = Path(__file__).parent.parent / "config-templates" / "claude-code" / "hooks.json"
        assert template_path.exists(), "hooks.json template must exist"

        with open(template_path) as f:
            data = json.load(f)

        assert "hooks" in data

    def test_hooks_template_has_expected_events(self):
        template_path = Path(__file__).parent.parent / "config-templates" / "claude-code" / "hooks.json"
        with open(template_path) as f:
            data = json.load(f)

        hooks = data["hooks"]
        assert "PreCompact" in hooks
        assert "SessionEnd" in hooks

    def test_hooks_template_entries_have_required_fields(self):
        template_path = Path(__file__).parent.parent / "config-templates" / "claude-code" / "hooks.json"
        with open(template_path) as f:
            data = json.load(f)

        for event_key, entries in data["hooks"].items():
            assert isinstance(entries, list), f"{event_key} should be a list"
            for entry in entries:
                assert entry.get("type") == "agent", f"{event_key} entry should be agent type"
                assert "description" in entry, f"{event_key} entry must have description"
                assert "prompt" in entry, f"{event_key} entry must have prompt"
                assert entry["description"].startswith("memcord:"), f"{event_key} description should start with 'memcord:'"


class TestMergeHooks:
    """Test the merge_hooks function."""

    def _sample_hooks(self):
        return {
            "hooks": {
                "PreCompact": [
                    {
                        "type": "agent",
                        "description": "memcord: auto-save progress before context compaction",
                        "prompt": "Save progress.",
                    }
                ],
                "SessionEnd": [
                    {
                        "type": "agent",
                        "description": "memcord: auto-save and close slot on session end",
                        "prompt": "Save and close.",
                    }
                ],
            }
        }

    def test_merge_into_empty_settings(self):
        existing = {}
        new_hooks = self._sample_hooks()

        result = merge_hooks(existing, new_hooks)

        assert "hooks" in result
        assert len(result["hooks"]["PreCompact"]) == 1
        assert len(result["hooks"]["SessionEnd"]) == 1

    def test_merge_preserves_existing_settings(self):
        existing = {"permissions": {"allow": ["some_tool"]}, "other_key": True}
        new_hooks = self._sample_hooks()

        result = merge_hooks(existing, new_hooks)

        assert result["permissions"] == {"allow": ["some_tool"]}
        assert result["other_key"] is True
        assert "hooks" in result

    def test_merge_preserves_non_memcord_hooks(self):
        existing = {
            "hooks": {
                "PreCompact": [
                    {
                        "type": "agent",
                        "description": "other-tool: do something",
                        "prompt": "Other tool prompt.",
                    }
                ],
            }
        }
        new_hooks = self._sample_hooks()

        result = merge_hooks(existing, new_hooks)

        pre_compact = result["hooks"]["PreCompact"]
        assert len(pre_compact) == 2
        descriptions = [h["description"] for h in pre_compact]
        assert "other-tool: do something" in descriptions
        assert "memcord: auto-save progress before context compaction" in descriptions

    def test_deduplication_on_second_run(self):
        existing = {}
        new_hooks = self._sample_hooks()

        # First merge
        result = merge_hooks(existing, new_hooks)
        # Second merge (idempotent)
        result = merge_hooks(result, new_hooks)

        assert len(result["hooks"]["PreCompact"]) == 1
        assert len(result["hooks"]["SessionEnd"]) == 1

    def test_deduplication_preserves_non_memcord(self):
        existing = {
            "hooks": {
                "PreCompact": [
                    {"type": "agent", "description": "other: hook", "prompt": "x"},
                    {"type": "agent", "description": "memcord: old hook", "prompt": "old"},
                ],
            }
        }
        new_hooks = self._sample_hooks()

        result = merge_hooks(existing, new_hooks)

        pre_compact = result["hooks"]["PreCompact"]
        assert len(pre_compact) == 2
        descriptions = [h["description"] for h in pre_compact]
        assert "other: hook" in descriptions
        assert "memcord: auto-save progress before context compaction" in descriptions
        # Old memcord hook should be replaced
        assert "memcord: old hook" not in descriptions

    def test_no_hooks_in_new_returns_existing(self):
        existing = {"permissions": {"allow": []}}
        result = merge_hooks(existing, {})
        assert result == existing

    def test_preserves_existing_hook_events_not_in_new(self):
        existing = {
            "hooks": {
                "SomeOtherEvent": [
                    {"type": "command", "description": "custom hook", "command": "echo hi"}
                ]
            }
        }
        new_hooks = self._sample_hooks()

        result = merge_hooks(existing, new_hooks)

        assert "SomeOtherEvent" in result["hooks"]
        assert len(result["hooks"]["SomeOtherEvent"]) == 1
