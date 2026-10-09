"""Runs Agent 4 (performance monitor) at checkpoints across a reel's first 3 hours."""

from __future__ import annotations

import datetime
import json
import pathlib
import time
from typing import Any, Callable

from . import instagram_api as ig
from .agents import performance_monitor
from .reel_analyzer import REPORTS

CHECKPOINTS_MIN = [30, 60, 120, 180]


def _manual_metrics() -> dict[str, Any]:
    """When the account isn't connected, ask the user to read numbers from Insights."""
    print("\nOpen the reel's Insights and enter the current numbers (blank = 0).")
    out = {}
    for key in ["views", "reach", "likes", "comments", "shares", "saved"]:
        raw = input(f"  {key}: ").strip()
        out[key] = int(raw) if raw.isdigit() else 0
    return out


def _derived(m: dict[str, Any]) -> dict[str, Any]:
    views = m.get("views") or m.get("reach") or 0
    if not views:
        return {}
    pct = lambda k: round(100 * (m.get(k) or 0) / views, 2)  # noqa: E731
    interactions = sum((m.get(k) or 0) for k in ("likes", "comments", "shares", "saved"))
    return {
        "engagement_rate_pct": round(100 * interactions / views, 2),
        "like_rate_pct": pct("likes"),
        "comment_rate_pct": pct("comments"),
        "share_rate_pct": pct("shares"),
        "save_rate_pct": pct("saved"),
    }


def monitor_reel(
    media_id: str,
    checkpoints_min: list[int] = CHECKPOINTS_MIN,
    on_event: Callable[[str], None] = print,
) -> str:
    connected = ig.configured()
    if connected:
        ts = ig.get_media(media_id)["timestamp"]  # e.g. 2026-10-09T10:15:00+0000
        published = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    else:
        on_event("Instagram not connected - running in manual mode (you type the numbers).")
        published = datetime.datetime.now(datetime.timezone.utc)

    log_path = REPORTS / f"monitor-{media_id}-{published:%Y%m%d-%H%M}.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"# 3-hour monitor for reel {media_id}\n\nPublished: {published.isoformat()}\n")
    history: list[dict[str, Any]] = []
    report = ""

    for i, minute in enumerate(checkpoints_min):
        due = published + datetime.timedelta(minutes=minute)
        wait = (due - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        if wait > 0:
            on_event(f"[monitor] next check at {minute} min ({due.astimezone():%H:%M}), waiting {int(wait // 60)} min...")
            time.sleep(wait)

        metrics = ig.get_reel_metrics(media_id) if connected else _manual_metrics()
        age = (datetime.datetime.now(datetime.timezone.utc) - published).total_seconds() / 60
        history.append({"minutes_since_post": round(age), **metrics, **_derived(metrics)})
        final = i == len(checkpoints_min) - 1

        task = (
            f"Checkpoint {i + 1}/{len(checkpoints_min)} for reel {media_id}, {round(age)} minutes after posting. "
            + ("This is the FINAL 3-hour check: give the final viral / not-viral verdict and the action plan."
               if final else "Judge the trend so far and act on what can be improved now.")
            + ("" if connected else " The account is not connected, so only use the numbers given; skip tools.")
        )
        on_event(f"[monitor] checkpoint {minute} min: {json.dumps(metrics)}")
        report = performance_monitor.run(task, context="Metrics history:\n" + json.dumps(history, indent=2))
        on_event(f"\n{report}\n")
        with log_path.open("a") as f:
            f.write(f"\n## {minute} min check\n\n```json\n{json.dumps(history[-1], indent=2)}\n```\n\n{report}\n")

    on_event(f"[monitor saved {log_path}]")
    return report
