from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from enterpriseagents.core.events import Event
from enterpriseagents.utils.time import utc_now_iso


class AuditLogger:
    """Maintains an immutable record of all workflow activities.

    This class is responsible for writing detailed execution logs to the disk. It captures events, tool invocations, results, and approval records in an append-only format, ensuring that every run produces a verifiable audit trail essential for enterprise compliance.
    """

    def __init__(self, runs_dir: Path, run_id: str) -> None:
        self._run_id = run_id
        self._root = runs_dir / run_id
        self._root.mkdir(parents=True, exist_ok=True)

        self._events = self._root / "events.jsonl"
        self._tool_calls = self._root / "tool_calls.jsonl"
        self._tool_results = self._root / "tool_results.jsonl"
        self._approvals = self._root / "policy_decisions.jsonl"
        self._packet = self._root / "metadata.json"
        
        self._plan_file = self._root / "plan.json"
        self._task_graph_file = self._root / "task_graph.json"
        self._test_results_file = self._root / "test_results.txt"
        self._evidence_file = self._root / "evidence_packet.md"

        self._tool_calls.touch()
        self._approvals.touch()
        self._test_results_file.touch()

        self._started_at = utc_now_iso()
        self._finish_meta: dict[str, Any] = {}

    def save_plan(self, plan_data: Any) -> None:
        data = plan_data.model_dump() if hasattr(plan_data, "model_dump") else plan_data
        self._plan_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save_task_graph(self, graph_data: Any) -> None:
        data = graph_data.model_dump() if hasattr(graph_data, "model_dump") else graph_data
        self._task_graph_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save_test_results(self, results: str) -> None:
        # Append or write? Let's just write/overwrite for now or append if multiple.
        with self._test_results_file.open("a", encoding="utf-8") as f:
            f.write(results + "\n")

    def save_evidence(self, markdown_content: str) -> None:
        self._evidence_file.write_text(markdown_content, encoding="utf-8")

    def event(self, ev: Event) -> None:
        # Pydantic change: use model_dump instead of asdict
        self._append(self._events, ev.model_dump())

    def tool_call(self, call: Any) -> None:
        # Supports both dict and Pydantic models for flexibility
        data = call.model_dump() if hasattr(call, "model_dump") else call
        self._append(self._tool_calls, data)

    def tool_result(self, call_id: str, *, ok: bool, output: str) -> None:
        self._append(self._tool_results, {"call_id": call_id, "ok": ok, "output": output, "ts": utc_now_iso()})

    def approval(self, record: dict[str, Any]) -> None:
        record.setdefault("run_id", self._run_id)
        self._append(self._approvals, record)

    def finish(self, **meta: Any) -> None:
        self._finish_meta.update(meta)
        packet = {
            "run_id": self._run_id,
            "started_at": self._started_at,
            "finished_at": utc_now_iso(),
            "meta": self._finish_meta,
            "files": {
                "events": str(self._events),
                "tool_calls": str(self._tool_calls),
                "tool_results": str(self._tool_results),
                "approvals": str(self._approvals),
            },
        }
        self._packet.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    def _append(self, path: Path, obj: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            # ensure_ascii=False supports UTF-8 characters (like emojis in LLM output)
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
