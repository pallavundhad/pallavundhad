"""Shared building blocks: the Claude client, model settings, and the SubAgent loop."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

MODEL = os.environ.get("HUB_MODEL", "claude-opus-5-5")
ORCHESTRATOR_EFFORT = os.environ.get("HUB_ORCHESTRATOR_EFFORT", "high")
SUBAGENT_EFFORT = os.environ.get("HUB_SUBAGENT_EFFORT", "medium")
MAX_TOKENS = 16000

# On a safety-classifier refusal, the API re-runs the request on Anthropic's
# recommended fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

client = anthropic.Anthropic()


def text_of(content: list[Any]) -> str:
    """Join the text blocks of a response."""
    return "\n".join(b.text for b in content if b.type == "text").strip()


@dataclass
class LocalTool:
    """A tool that runs on this machine (as opposed to a server tool like web search)."""

    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., str]

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "strict": True,
        }


@dataclass
class SubAgent:
    """One specialist agent with its own system prompt, tools, and agentic loop."""

    name: str
    role: str  # one-line summary shown to the orchestrator
    system: str
    server_tools: list[dict[str, Any]] = field(default_factory=list)
    local_tools: list[LocalTool] = field(default_factory=list)
    max_turns: int = 12

    def _tools(self) -> list[dict[str, Any]]:
        return self.server_tools + [t.definition() for t in self.local_tools]

    def _run_local_tool(self, name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
        tool = next((t for t in self.local_tools if t.name == name), None)
        if tool is None:
            return f"Unknown tool: {name}", True
        try:
            return tool.fn(**tool_input), False
        except Exception as e:  # report tool failures back to the model
            return f"{type(e).__name__}: {e}", True

    def run(self, task: str, context: str = "") -> str:
        """Run the agent on a task until it produces a final answer."""
        prompt = task if not context else f"{task}\n\n<context>\n{context}\n</context>"
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        tools = self._tools()

        for _ in range(self.max_turns):
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=self.system,
                messages=messages,
                output_config={"effort": SUBAGENT_EFFORT},
                betas=[FALLBACK_BETA],
                fallbacks="default",
                **({"tools": tools} if tools else {}),
            )

            if response.stop_reason == "refusal":
                return f"[{self.name}] declined this task."
            if response.stop_reason in ("end_turn", "stop_sequence"):
                return text_of(response.content)
            if response.stop_reason == "max_tokens":
                return text_of(response.content) + "\n\n[output truncated]"

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                # A long server-tool turn (e.g. web search) paused; resend to continue.
                continue

            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                output, is_error = self._run_local_tool(block.name, block.input)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                        "is_error": is_error,
                    }
                )
            messages.append({"role": "user", "content": results})

        return f"[{self.name}] stopped after {self.max_turns} turns without finishing."


def as_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
