"""The main (orchestrator) agent: plans the work and delegates to the 5 specialists."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from .agents import ALL_AGENTS
from .base import FALLBACK_BETA, MAX_TOKENS, MODEL, ORCHESTRATOR_EFFORT, SubAgent, client, text_of

ORCHESTRATOR_SYSTEM = """You are the lead Instagram strategist and the hub of a team of 5 specialist agents.
Your job is to take the user's goal and drive it end to end: content creation, posting, post-publish
marketing, and scaling interactions and engagement rate.

How to work:
1. Break the goal into sub-tasks and delegate each to the right specialist with a call to its tool.
2. Run independent sub-tasks in parallel (several tool calls in one turn). Run dependent ones in order:
   usually trend research -> content creation -> posting strategy -> engagement plan -> growth analysis.
3. Give every specialist the context it needs (niche, audience, brand voice, earlier agents' output,
   metrics). The specialists cannot see this conversation, only what you pass them.
4. Review what comes back. If something is weak or inconsistent, send it back with specific feedback.
5. Finish with one integrated action plan: ready-to-post content, posting plan, first-hour engagement
   checklist, and the 30-day growth plan with KPIs. Don't paste each agent's output verbatim; merge it.

Never recommend buying followers, engagement pods, or other tactics that break Instagram's terms."""

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {"type": "string", "description": "Exactly what this specialist should produce."},
        "context": {
            "type": "string",
            "description": "Everything it needs to know: niche, audience, brand voice, other agents' results, metrics.",
        },
    },
    "required": ["task", "context"],
    "additionalProperties": False,
}


class InstagramHub:
    """A main agent connected to 5 specialist agents."""

    def __init__(
        self,
        agents: list[SubAgent] = ALL_AGENTS,
        on_event: Callable[[str], None] = print,
        max_turns: int = 20,
    ):
        self.agents = {a.name: a for a in agents}
        self.on_event = on_event
        self.max_turns = max_turns
        self.messages: list[dict[str, Any]] = []
        self.board: list[dict[str, str]] = []  # every delegated task and its result
        self.tools = [
            {
                "name": a.name,
                "description": f"Delegate to the {a.name} agent. {a.role}",
                "input_schema": TOOL_SCHEMA,
                "strict": True,
            }
            for a in agents
        ]

    def _delegate(self, block: Any) -> dict[str, Any]:
        agent = self.agents.get(block.name)
        if agent is None:
            return {"type": "tool_result", "tool_use_id": block.id, "content": f"No agent named {block.name}", "is_error": True}
        self.on_event(f"  -> {agent.name}: {block.input['task'][:100]}")
        try:
            result = agent.run(block.input["task"], block.input.get("context", ""))
            is_error = False
        except Exception as e:  # surface API/network errors to the orchestrator
            result, is_error = f"{agent.name} failed: {type(e).__name__}: {e}", True
        self.on_event(f"  <- {agent.name} done ({len(result)} chars)")
        self.board.append({"agent": agent.name, "task": block.input["task"], "result": result})
        return {"type": "tool_result", "tool_use_id": block.id, "content": result, "is_error": is_error}

    def ask(self, user_message: str) -> str:
        """Send a message to the hub. Conversation history is kept between calls."""
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(self.max_turns):
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=ORCHESTRATOR_SYSTEM,
                tools=self.tools,
                messages=self.messages,
                output_config={"effort": ORCHESTRATOR_EFFORT},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "The orchestrator declined this request."
            if response.stop_reason != "tool_use":
                return text_of(response.content)

            calls = [b for b in response.content if b.type == "tool_use"]
            plan = text_of(response.content)
            if plan:
                self.on_event(f"[hub] {plan[:300]}")
            # Independent delegations run in parallel; all results go back in one message.
            with ThreadPoolExecutor(max_workers=len(calls)) as pool:
                results = list(pool.map(self._delegate, calls))
            self.messages.append({"role": "user", "content": results})

        return f"Stopped after {self.max_turns} orchestration turns."

    def report_markdown(self, final_plan: str) -> str:
        parts = ["# Instagram Agent Hub Report", "", "## Final plan", "", final_plan, "", "## Agent work log", ""]
        for item in self.board:
            parts += [f"### {item['agent']}", "", f"**Task:** {item['task']}", "", item["result"], ""]
        return "\n".join(parts)
