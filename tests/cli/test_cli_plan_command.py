"""Tests for the /plan CLI slash command."""

from unittest.mock import MagicMock, patch

from agent.skill_commands import scan_skill_commands
from cli import HermesCLI


def _make_cli():
    cli_obj = HermesCLI.__new__(HermesCLI)
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj.agent = None
    cli_obj.conversation_history = []
    cli_obj.session_id = "sess-123"
    cli_obj._pending_input = MagicMock()
    return cli_obj


def _make_plan_skill(skills_dir):
    skill_dir = skills_dir / "plan"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: plan
description: Plan mode skill.
---

# Plan

Use the current conversation context when no explicit instruction is provided.
Save plans under the active workspace's .hermes/plans directory.
"""
    )


def _make_self_evolve_skill(skills_dir):
    skill_dir = skills_dir / "czp-self-evolve"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: czp-self-evolve
description: Self-evolve skill.
slash_aliases: [czp-learn]
---

# Self evolve

Absorb the provided material, summarize what matters, and update long-term systems when justified.
"""
    )


class TestCLIPlanCommand:
    def test_plan_command_queues_plan_skill_message(self, tmp_path, monkeypatch):
        cli_obj = _make_cli()

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            _make_plan_skill(tmp_path)
            scan_skill_commands()
            result = cli_obj.process_command("/plan Add OAuth login")

        assert result is True
        cli_obj._pending_input.put.assert_called_once()
        queued = cli_obj._pending_input.put.call_args[0][0]
        assert "Plan mode skill" in queued
        assert "Add OAuth login" in queued
        assert ".hermes/plans" in queued
        assert str(tmp_path / "plans") not in queued
        assert "active workspace/backend cwd" in queued
        assert "Runtime note:" in queued

    def test_skill_alias_command_queues_canonical_skill_message(self, tmp_path):
        cli_obj = _make_cli()

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            _make_self_evolve_skill(tmp_path)
            scan_skill_commands()
            result = cli_obj.process_command("/czp-learn 学习这个链接")

        assert result is True
        cli_obj._pending_input.put.assert_called_once()
        queued = cli_obj._pending_input.put.call_args[0][0]
        assert "czp-self-evolve" in queued
        assert "学习这个链接" in queued

    def test_plan_without_args_uses_skill_context_guidance(self, tmp_path, monkeypatch):
        cli_obj = _make_cli()

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            _make_plan_skill(tmp_path)
            scan_skill_commands()
            cli_obj.process_command("/plan")

        queued = cli_obj._pending_input.put.call_args[0][0]
        assert "current conversation context" in queued
        assert ".hermes/plans/" in queued
        assert "conversation-plan.md" in queued
