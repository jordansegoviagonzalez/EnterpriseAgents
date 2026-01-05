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
        self._approvals = self._root / "approvals.jsonl"
        self._packet = self._root / "run_packet.json"

        self._started_at = utc_now_iso()
        self._finish_meta: dict[str, Any] = {}

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