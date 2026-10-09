"""Command-line entry point.

    python -m instagram_agent_hub "Launch a Reel for my vegan bakery in Pune"
    python -m instagram_agent_hub --metrics examples/metrics.json "Grow engagement for my fitness page"
    python -m instagram_agent_hub            # interactive chat with the hub
"""

from __future__ import annotations

import argparse
import datetime
import pathlib

from .hub import InstagramHub


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram Agent Hub")
    parser.add_argument("goal", nargs="?", help="What you want the team to do. Omit for interactive mode.")
    parser.add_argument("--metrics", type=pathlib.Path, help="JSON file with follower count and post metrics.")
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("reports"), help="Folder for saved reports.")
    args = parser.parse_args()

    hub = InstagramHub()

    def run(message: str) -> None:
        if args.metrics:
            message += f"\n\nMy recent Instagram metrics (JSON):\n{args.metrics.read_text()}"
        answer = hub.ask(message)
        print("\n" + answer + "\n")
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / f"report-{datetime.datetime.now():%Y%m%d-%H%M%S}.md"
        path.write_text(hub.report_markdown(answer))
        print(f"[saved {path}]")

    if args.goal:
        run(args.goal)
        return

    print("Instagram Agent Hub - type your goal (Ctrl+C to quit).")
    while True:
        try:
            message = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message:
            run(message)
            args.metrics = None  # attach metrics to the first message only


if __name__ == "__main__":
    main()
