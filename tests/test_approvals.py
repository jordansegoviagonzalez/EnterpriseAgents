import json
from dataclasses import dataclass, field

from enterpriseagents.audit.logger import AuditLogger
from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.core.run import RunCoordinator
from enterpriseagents.policy.approvals import ApprovalResult
from enterpriseagents.policy.policy import PolicyDecision, PolicyEngine


@dataclass
class RecordingTools:
    events: list[str] = field(default_factory=list)

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        self.events.append(f"execute:{call.call_id}")
        return ToolResult(call_id=call.call_id, ok=True, output="executed")


@dataclass
class RecordingApprover:
    approved: bool
    events: list[str]
    reason: str | None = None

    def request(self, *, call: ToolCall, policy_decision: PolicyDecision) -> ApprovalResult:
        self.events.append(f"approve:{call.call_id}")
        return ApprovalResult(approved=self.approved, reason=self.reason)


def make_coordinator(tmp_path, *, approver=None, tools=None):
    return RunCoordinator(
        run_id="approval-run",
        audit=AuditLogger(runs_dir=tmp_path / "runs", run_id="approval-run"),
        policy=PolicyEngine(),
        tools=tools or RecordingTools(),
        director=None,
        builder=None,
        reviewer=None,
        docs=None,
        router=None,
        memory=None,
        approver=approver,
    )


def approval_required_call() -> ToolCall:
    return ToolCall(
        tool_name="run_command",
        args={"command": "python3 --version"},
        call_id="approval-required",
    )


def policy_records(tmp_path) -> list[dict[str, object]]:
    path = tmp_path / "runs" / "approval-run" / "policy_decisions.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_require_approval_calls_approver_before_execution(tmp_path):
    events: list[str] = []
    tools = RecordingTools(events=events)
    approver = RecordingApprover(approved=True, events=events, reason="approved in test")
    coordinator = make_coordinator(tmp_path, approver=approver, tools=tools)

    ok = coordinator._execute_tool(approval_required_call(), str(tmp_path / "workspace"), False)

    assert ok is True
    assert events == ["approve:approval-required", "execute:approval-required"]


def test_approved_action_executes_and_logs_human_decision(tmp_path):
    tools = RecordingTools()
    approver = RecordingApprover(approved=True, events=[], reason="owner approved")
    coordinator = make_coordinator(tmp_path, approver=approver, tools=tools)

    ok = coordinator._execute_tool(approval_required_call(), str(tmp_path / "workspace"), False)

    assert ok is True
    assert tools.events == ["execute:approval-required"]
    records = policy_records(tmp_path)
    assert records[0]["decision"] == "REQUIRE_APPROVAL"
    assert records[1]["policy_decision"] == "REQUIRE_APPROVAL"
    assert records[1]["human_decision"] == "approved"
    assert records[1]["reason"] == "owner approved"
    assert records[1]["command"] == "python3 --version"
    assert records[1]["run_id"] == "approval-run"


def test_denied_action_does_not_execute_and_logs_human_decision(tmp_path):
    tools = RecordingTools()
    approver = RecordingApprover(approved=False, events=[], reason="owner denied")
    coordinator = make_coordinator(tmp_path, approver=approver, tools=tools)

    ok = coordinator._execute_tool(approval_required_call(), str(tmp_path / "workspace"), False)

    assert ok is False
    assert tools.events == []
    records = policy_records(tmp_path)
    assert records[0]["decision"] == "REQUIRE_APPROVAL"
    assert records[1]["human_decision"] == "denied"
    assert records[1]["reason"] == "owner denied"


def test_non_interactive_default_denies_approval_required_actions(tmp_path):
    tools = RecordingTools()
    coordinator = make_coordinator(tmp_path, tools=tools)

    ok = coordinator._execute_tool(approval_required_call(), str(tmp_path / "workspace"), False)

    assert ok is False
    assert tools.events == []
    records = policy_records(tmp_path)
    assert records[1]["human_decision"] == "denied"
    assert "Non-interactive mode denies" in str(records[1]["reason"])


def test_blocked_action_never_requests_approval_or_executes(tmp_path):
    events: list[str] = []
    tools = RecordingTools(events=events)
    approver = RecordingApprover(approved=True, events=events)
    coordinator = make_coordinator(tmp_path, approver=approver, tools=tools)
    call = ToolCall(
        tool_name="write_file", args={"path": "secret.txt", "content": "x"}, call_id="blocked"
    )

    ok = coordinator._execute_tool(call, str(tmp_path / "workspace"), False)

    assert ok is False
    assert events == []
    records = policy_records(tmp_path)
    assert len(records) == 1
    assert records[0]["decision"] == "BLOCK"
