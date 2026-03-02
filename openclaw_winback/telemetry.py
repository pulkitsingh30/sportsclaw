"""Telemetry helper for recording workflow events."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
import pathlib
import time
from typing import Any, Dict

from openclaw_winback.models import WorkflowContext

DEFAULT_TELEMETRY_FILE = pathlib.Path("analytics/events.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_timer() -> float:
    return time.perf_counter()


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def record_event(
    context: WorkflowContext,
    event_name: str,
    user_id: str,
    channel: str,
    latency_ms: int | None = None,
    extra: Dict[str, Any] | None = None,
) -> None:
    telemetry_file = pathlib.Path(os.environ.get("WINBACK_TELEMETRY_FILE", str(DEFAULT_TELEMETRY_FILE)))
    telemetry_file.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "event_name": event_name,
        "timestamp_utc": _utc_now_iso(),
        "workflow_id": context.workflow_id,
        "session_id": context.session_id,
        "user_id": user_id,
        "channel": channel,
        "context": asdict(context),
    }
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if extra:
        payload.update(extra)
    with telemetry_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")
