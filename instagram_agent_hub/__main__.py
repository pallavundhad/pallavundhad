"""Command-line entry point.

    python -m instagram_agent_hub                       # chat with the main agent
    python -m instagram_agent_hub "Make a reel like https://www.instagram.com/reel/XXXX/ for my bakery"
    python -m instagram_agent_hub analyze <reel URL or video.mp4>   # Agent 1 only -> Word file
    python -m instagram_agent_hub monitor <media_id>                # Agent 4: 3-hour monitor
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import sys

from .hub import InstagramHub
from .monitor import monitor_reel
from .reel_analyzer import REPORTS, analyze_reel


def chat(first_message: str | None) -> None:
    hub = InstagramHub()

    def run(message: str) -> None:
        answer = hub.ask(message)
        print("\n" + answer + "\n")
        REPORTS.mkdir(parents=True, exist_ok=True)
        path = REPORTS / f"report-{datetime.datetime.now():%Y%m%d-%H%M%S}.md"
        path.write_text(hub.report_markdown(answer))
        print(f"[saved {path}]")
        if hub.pending_monitor:
            media_id, hub.pending_monitor = hub.pending_monitor, None
            final = monitor_reel(media_id)
            hub.messages.append({"role": "user", "content": f"[3-hour monitor finished for {media_id}]\n{final}"})
            print("\n" + hub.ask("Summarise the 3-hour result and what I should do next.") + "\n")

    if first_message:
        run(first_message)
        if not sys.stdin.isatty():
            return
    print("Instagram Agent Hub - tell the main agent what you want (Ctrl+C to quit).")
    while True:
        try:
            message = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message:
            run(message)


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "analyze":
        p = argparse.ArgumentParser(prog="instagram_agent_hub analyze")
        p.add_argument("source", help="Reel URL or local video file")
        p.add_argument("--notes", default="")
        a = p.parse_args(argv[1:])
        result = analyze_reel(a.source, a.notes)
        print(f"Word file: {result['word_file']}")
        print(f"Hook: {result['analysis']['hook']['spoken'] or result['analysis']['hook']['on_screen_text']}")
    elif argv and argv[0] == "monitor":
        p = argparse.ArgumentParser(prog="instagram_agent_hub monitor")
        p.add_argument("media_id")
        p.add_argument("--checkpoints", default="30,60,120,180", help="Minutes after posting, comma-separated")
        a = p.parse_args(argv[1:])
        monitor_reel(a.media_id, [int(x) for x in a.checkpoints.split(",")])
    else:
        chat(" ".join(argv) or None)


if __name__ == "__main__":
    main()
