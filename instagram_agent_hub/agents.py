"""The 5 specialist Instagram agents the orchestrator delegates to."""

from __future__ import annotations

from .base import LocalTool, SubAgent, as_json

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 8},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5},
]


# ---------------------------------------------------------------------------
# Local tool for the growth analyst: exact engagement maths instead of guessing.
# ---------------------------------------------------------------------------

def calculate_engagement_metrics(posts: list[dict], followers: int) -> str:
    rows = []
    for p in posts:
        interactions = p["likes"] + p["comments"] + p["saves"] + p["shares"]
        reach = p["reach"] or 1
        rows.append(
            {
                "post": p["post_id"],
                "interactions": interactions,
                "engagement_rate_by_followers_pct": round(100 * interactions / max(followers, 1), 2),
                "engagement_rate_by_reach_pct": round(100 * interactions / reach, 2),
                "save_rate_pct": round(100 * p["saves"] / reach, 2),
                "share_rate_pct": round(100 * p["shares"] / reach, 2),
                "comment_rate_pct": round(100 * p["comments"] / reach, 2),
            }
        )
    n = len(rows) or 1
    summary = {
        "posts_analyzed": len(rows),
        "followers": followers,
        "avg_engagement_rate_by_followers_pct": round(sum(r["engagement_rate_by_followers_pct"] for r in rows) / n, 2),
        "avg_engagement_rate_by_reach_pct": round(sum(r["engagement_rate_by_reach_pct"] for r in rows) / n, 2),
        "best_post": max(rows, key=lambda r: r["engagement_rate_by_reach_pct"])["post"] if rows else None,
        "worst_post": min(rows, key=lambda r: r["engagement_rate_by_reach_pct"])["post"] if rows else None,
    }
    return as_json({"summary": summary, "per_post": rows})


ENGAGEMENT_TOOL = LocalTool(
    name="calculate_engagement_metrics",
    description=(
        "Compute exact engagement rate (by followers and by reach), save rate, share rate and "
        "comment rate for a list of Instagram posts. Always use this instead of doing the maths yourself."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "followers": {"type": "integer", "description": "Account follower count."},
            "posts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string"},
                        "likes": {"type": "integer"},
                        "comments": {"type": "integer"},
                        "saves": {"type": "integer"},
                        "shares": {"type": "integer"},
                        "reach": {"type": "integer"},
                    },
                    "required": ["post_id", "likes", "comments", "saves", "shares", "reach"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["followers", "posts"],
        "additionalProperties": False,
    },
    fn=calculate_engagement_metrics,
)


# ---------------------------------------------------------------------------
# The five specialists
# ---------------------------------------------------------------------------

trend_researcher = SubAgent(
    name="trend_researcher",
    role="Finds current Instagram trends, trending audio/formats, niche hashtags and competitor tactics using live web search.",
    system=(
        "You are an Instagram trend researcher. Use web search to find what is working on Instagram "
        "right now for the given niche: trending Reels formats and audio, content themes, hashtags "
        "(mix of broad, mid-size and niche), and what top competitors post. Prefer sources from the last "
        "60 days and name them. Output a concise brief with sections: Trends, Formats & Audio, "
        "Hashtag Candidates, Competitor Insights, Opportunities."
    ),
    server_tools=WEB_TOOLS,
)

content_creator = SubAgent(
    name="content_creator",
    role="Writes post concepts, scroll-stopping hooks, captions, Reel scripts, carousel slide copy and visual briefs.",
    system=(
        "You are an Instagram content creator and copywriter. Turn the brief into ready-to-post content: "
        "a strong 1-line hook for the first 2 seconds / first caption line, the full caption with a "
        "clear call to action (save, share, comment prompt), a Reel shot-by-shot script or carousel "
        "slide-by-slide copy, on-screen text, and a visual brief for the designer. Match the brand voice "
        "given in context. When asked for options, give 2-3 variants labelled A/B/C for testing."
    ),
)

posting_strategist = SubAgent(
    name="posting_strategist",
    role="Plans hashtag sets, Instagram SEO keywords, alt text, best posting times, and the content calendar.",
    system=(
        "You are an Instagram posting and discoverability strategist. For the content given, produce: "
        "a hashtag set of 5-15 tags split into broad / mid / niche, keyword-rich caption and profile "
        "SEO suggestions, alt text, recommended posting day and time windows for the audience's time "
        "zone (state your assumptions), cross-posting to Stories, and a weekly content calendar mixing "
        "Reels, carousels and Stories. Be specific and actionable."
    ),
)

engagement_manager = SubAgent(
    name="engagement_manager",
    role="Runs post-publish marketing: first-hour engagement plan, comment replies, DM scripts, Story promotion, collabs and outreach.",
    system=(
        "You are an Instagram community and engagement manager. Focus on what happens AFTER a post is "
        "published: a first-60-minutes engagement checklist, reply templates for common comment types "
        "(that invite further replies), DM scripts for leads and collaborators, Story sequences that push "
        "traffic to the post (polls, quizzes, question boxes, link stickers), collab/creator outreach "
        "ideas, and community rituals that build repeat interactions. Keep replies human and on-brand; "
        "never suggest buying followers, engagement pods or spam tactics that break Instagram's terms."
    ),
)

growth_analyst = SubAgent(
    name="growth_analyst",
    role="Analyses post metrics (engagement rate, saves, shares, reach) and produces a plan to scale interactions and new followers.",
    system=(
        "You are an Instagram growth analyst. When metrics are provided, ALWAYS call "
        "calculate_engagement_metrics first and base your analysis on its numbers. Explain what is "
        "driving or holding back engagement, compare to typical benchmarks (say they are approximate), "
        "and give a scaling plan: what to double down on, 2-3 A/B tests to run, posting frequency, and "
        "target KPIs for the next 30 days. If no metrics are provided, say which metrics to collect from "
        "Instagram Insights and give a measurement plan."
    ),
    local_tools=[ENGAGEMENT_TOOL],
)

ALL_AGENTS = [trend_researcher, content_creator, posting_strategist, engagement_manager, growth_analyst]
