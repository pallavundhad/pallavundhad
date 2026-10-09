# Instagram Agent Hub

One **main agent** (the orchestrator) connected to **5 specialist agents** that work together on Instagram content creation, post-publish marketing, and scaling interactions and engagement rate.

```
                         ┌──────────────────────┐
           your goal ──▶ │  Main agent (hub)    │ ──▶ integrated action plan + report
                         │  plans, delegates,   │
                         │  reviews, merges     │
                         └──────────┬───────────┘
      ┌──────────────┬──────────────┼───────────────┬────────────────┐
      ▼              ▼              ▼               ▼                ▼
 trend_researcher content_creator posting_strategist engagement_manager growth_analyst
 (live web search) (hooks, captions, (hashtags, SEO,  (first-hour plan,  (engagement-rate
                    Reel scripts)    times, calendar)  replies, DMs,      maths, A/B tests,
                                                       Stories, collabs)  30-day scaling)
```

| Agent | What it does | Tools |
|---|---|---|
| `trend_researcher` | Current trends, formats, audio, hashtags, competitor tactics | Web search, web fetch |
| `content_creator` | Hooks, captions with CTAs, Reel scripts, carousel copy, A/B/C variants | – |
| `posting_strategist` | Hashtag sets, Instagram SEO, alt text, best times, weekly calendar | – |
| `engagement_manager` | Post-publish marketing: first 60 min, comment replies, DMs, Story pushes, collabs | – |
| `growth_analyst` | Engagement rate, save and share rates, what's working, scaling plan and KPIs | `calculate_engagement_metrics` (exact maths) |

**How they work together:** the main agent decides which specialists it needs and calls them as tools. Independent jobs run **in parallel**, for example trend research and metrics analysis at the same time. Dependent jobs run in order: trends → content → posting → engagement → growth. The main agent passes each specialist the context it needs, including earlier agents' results, and sends weak work back with feedback. It then merges everything into one plan. Every delegated task and its result is logged and saved to `reports/`.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # or: ant auth login
```

## Run

```bash
# One-shot
python -m instagram_agent_hub "I run a home-bakery page in Pune (4k followers). Plan this week's Reels and how to boost engagement after posting."

# Include your Instagram Insights numbers (see examples/metrics.json for the format)
python -m instagram_agent_hub --metrics examples/metrics.json "Why is my engagement dropping and how do I scale?"

# Interactive chat with the hub (keeps the conversation)
python -m instagram_agent_hub
```

From Python:

```python
from instagram_agent_hub import InstagramHub

hub = InstagramHub()
plan = hub.ask("Create a carousel about 5 desk stretches for my physio clinic and a post-publish plan.")
print(plan)
print(hub.report_markdown(plan))
```

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `HUB_MODEL` | `claude-opus-5-5` | Model used by all agents |
| `HUB_ORCHESTRATOR_EFFORT` | `high` | Reasoning effort of the main agent |
| `HUB_SUBAGENT_EFFORT` | `medium` | Reasoning effort of the specialists (`low` is cheaper) |

Requests opt into server-side refusal fallbacks (`fallbacks: "default"`). If a safety classifier declines a request, the API retries it on Anthropic's recommended fallback model.

## Add or change an agent

Agents are defined in `agents.py` as `SubAgent(name, role, system, server_tools, local_tools)`. Add one to `ALL_AGENTS` and the hub picks it up as a new tool automatically. To give an agent a real capability, for example posting through the Instagram Graph API, add a `LocalTool` with a Python function.
