import json

import pytest

from enterpriseagents.audit.logger import AuditLogger
from enterpriseagents.core.models import ToolCall
from enterpriseagents.policy.policy import PolicyEngine


@pytest.fixture
def policy():
    return PolicyEngine()


def test_block_path_traversal(policy, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # Try to write outside workspace
    call = ToolCall(
        tool_name="write_file", args={"path": "../secret.txt", "content": "hack"}, call_id="1"
    )
    decision = policy.evaluate(call=call, workspace=str(workspace))
    assert not decision.allowed
    assert "Path traversal blocked" in decision.reason


@pytest.mark.parametrize(
    "path",
    [
        "secret.txt",
        "api_token.txt",
        "private.key",
        "password.txt",
        "credentials.json",
        "PRIVATE_KEY.pem",
        ".env",
        ".dev.vars",
    ],
)
def test_block_sensitive_file_writes(policy, tmp_path, path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    call = ToolCall(
        tool_name="write_file", args={"path": path, "content": "placeholder"}, call_id="2"
    )
    decision = policy.evaluate(call=call, workspace=str(workspace))

    assert not decision.allowed
    assert "sensitive file" in decision.reason


@pytest.mark.parametrize(
    "path",
    [
        "secret.txt",
        "api_token.txt",
        "private.key",
        "password.txt",
        "credentials.json",
        "PRIVATE_KEY.pem",
        ".env",
        ".dev.vars",
    ],
)
def test_block_sensitive_file_reads(policy, tmp_path, path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    call = ToolCall(tool_name="read_file", args={"path": path}, call_id="2")
    decision = policy.evaluate(call=call, workspace=str(workspace))

    assert not decision.allowed
    assert "sensitive file" in decision.reason


def test_sensitive_file_decision_record_contains_audit_fields(policy, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    call = ToolCall(
        tool_name="write_file",
        args={"path": "secret.txt", "content": "placeholder"},
        call_id="sensitive-write",
    )
    decision = policy.evaluate(call=call, workspace=str(workspace))
    record = decision.to_record(call)

    assert record["action_type"] == "write_file"
    assert record["target_path"] == "secret.txt"
    assert record["decision"] == "BLOCK"
    assert record["reason"]
    assert record["ts"]
    assert record["timestamp"]


def test_blocked_sensitive_file_access_is_logged_with_run_id(policy, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    audit = AuditLogger(runs_dir=tmp_path / "runs", run_id="security-run")

    call = ToolCall(
        tool_name="read_file",
        args={"path": "PRIVATE_KEY.pem"},
        call_id="sensitive-read",
    )
    decision = policy.evaluate(call=call, workspace=str(workspace))
    audit.approval(decision.to_record(call))

    records = [
        json.loads(line)
        for line in (tmp_path / "runs" / "security-run" / "policy_decisions.jsonl")
        .read_text()
        .splitlines()
    ]

    assert records == [
        {
            **records[0],
            "action_type": "read_file",
            "target_path": "PRIVATE_KEY.pem",
            "decision": "BLOCK",
            "run_id": "security-run",
        }
    ]


def test_block_dangerous_commands(policy, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # sudo
    call = ToolCall(tool_name="run_command", args={"command": "sudo rm -rf /"}, call_id="3")
    decision = policy.evaluate(call=call, workspace=str(workspace))
    assert not decision.allowed
    assert "Dangerous keyword 'sudo'" in decision.reason

    # rm -rf
    call = ToolCall(tool_name="run_command", args={"command": "rm -rf ."}, call_id="4")
    decision = policy.evaluate(call=call, workspace=str(workspace))
    assert not decision.allowed
    assert "Dangerous keyword 'rm -rf'" in decision.reason


def test_allowlist_command(policy, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # valid command
    call = ToolCall(tool_name="run_command", args={"command": "python3 --version"}, call_id="5")
    decision = policy.evaluate(call=call, workspace=str(workspace))
    assert decision.allowed
    assert decision.needs_approval
    assert "Allowlisted" in decision.reason


def test_unknown_command_blocked(policy, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # random command
    call = ToolCall(tool_name="run_command", args={"command": "make coffee"}, call_id="6")
    decision = policy.evaluate(call=call, workspace=str(workspace))
    assert not decision.allowed
    assert "not in security allowlist" in decision.reason
