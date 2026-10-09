"""Agents 2-4. (Agent 1, the Reel Analyzer, is a pipeline in reel_analyzer.py.)"""

from __future__ import annotations

from typing import Any, Callable

from . import instagram_api as ig
from .base import LocalTool, SubAgent, as_json

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 8},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5},
]


def _obj(props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _safe(fn: Callable[..., Any]) -> Callable[..., str]:
    """Wrap an Instagram call so declines and missing setup come back as plain text."""
    def run(**kwargs: Any) -> str:
        if not ig.configured():
            return "Instagram account not connected (set IG_USER_ID and IG_ACCESS_TOKEN)."
        try:
            result = fn(**kwargs)
        except ig.NotApproved as e:
            return f"NOT DONE - {e} Do not retry; continue without it."
        return result if isinstance(result, str) else as_json(result)
    return run


def _baseline(limit: int = 12) -> dict[str, Any]:
    reels = ig.get_recent_reels(limit)
    n = len(reels) or 1
    return {
        "reels_counted": len(reels),
        "avg_likes": round(sum(r.get("like_count", 0) for r in reels) / n, 1),
        "avg_comments": round(sum(r.get("comments_count", 0) for r in reels) / n, 1),
        "note": "Lifetime averages of recent reels - a reel at 3 h is normally well below these.",
    }


MONITOR_TOOLS = [
    LocalTool("get_reel_metrics", "Live views, reach, likes, comments, shares, saves for a reel.",
              _obj({"media_id": {"type": "string"}}), _safe(ig.get_reel_metrics)),
    LocalTool("get_recent_comments", "Latest comments on a reel (id, text, username).",
              _obj({"media_id": {"type": "string"}}), _safe(lambda media_id: ig.get_comments(media_id))),
    LocalTool("get_account_baseline", "Average likes/comments of the account's recent reels, to judge what 'viral' means for this account.",
              _obj({}), _safe(_baseline)),
    LocalTool("reply_to_comment",
              "Reply to a comment on the reel. The user is asked to approve every reply before it is posted.",
              _obj({"comment_id": {"type": "string"}, "comment_text": {"type": "string"}, "message": {"type": "string"}}),
              _safe(ig.reply_to_comment)),
    LocalTool("hide_comment", "Hide a spam or abusive comment. The user is asked to approve first.",
              _obj({"comment_id": {"type": "string"}, "comment_text": {"type": "string"}, "reason": {"type": "string"}}),
              _safe(ig.hide_comment)),
]


# ---------------------------------------------------------------------------
# Agent 2 - Content Writer
# ---------------------------------------------------------------------------

content_writer = SubAgent(
    name="content_writer",
    role="Writes reel scripts, captions and hashtags, and gives shot-by-shot guidance on how the reel should look.",
    system=(
        "You are an Instagram Reels scriptwriter and creative director. For the brief (and any reel "
        "breakdown you are given as reference) produce:\n"
        "1. 3 hook options for the first 2 seconds (spoken line + on-screen text).\n"
        "2. A full script with timestamps: what is said, on-screen text, and the shot for each beat.\n"
        "3. How the reel should look: framing, camera angles, lighting, setting, outfit/props, "
        "transitions, editing pace, text style and placement, music/trending-audio direction, ideal length, "
        "and cover-frame idea.\n"
        "4. 2-3 caption options (first line is a hook, clear CTA: save / share / comment keyword).\n"
        "5. Hashtags: 8-15 split into broad / mid / niche.\n"
        "Match the creator's language (e.g. Hinglish) and brand voice. Write so it can be shot today."
    ),
)


# ---------------------------------------------------------------------------
# Agent 3 - Viral Strategist
# ---------------------------------------------------------------------------

viral_strategist = SubAgent(
    name="viral_strategist",
    role="Plans how to make the reel go viral: likes, comments, shares, saves and new followers, before and after posting.",
    system=(
        "You are an Instagram growth and virality strategist. Use web search to check what is working on "
        "Reels right now in this niche. Give a concrete plan for the reel:\n"
        "- Before posting: hook/retention fixes, length, trending audio, cover, best time to post (state the "
        "time zone you assume), collab-post partners, keyword-rich caption.\n"
        "- First 60 minutes after posting: Story shares with stickers, replying to every comment with a "
        "question, pinning a comment, DM sharing to close audience, engaging with 10-15 niche accounts.\n"
        "- Triggers for each metric: comment prompts, save-worthy value, share triggers, follow reason "
        "(series / part 2 / profile CTA).\n"
        "- Targets: what views/likes/comments/shares at 1 h and 3 h would count as viral for this account size.\n"
        "Only white-hat tactics: never suggest buying followers or likes, engagement pods, follow/unfollow, "
        "or anything against Instagram's terms."
    ),
    server_tools=WEB_TOOLS,
)


# ---------------------------------------------------------------------------
# Agent 4 - Performance Monitor (first 3 hours)
# ---------------------------------------------------------------------------

performance_monitor = SubAgent(
    name="performance_monitor",
    role="Checks a published reel's performance in its first 3 hours, judges if it's going viral, and takes or recommends action.",
    system=(
        "You are an Instagram performance monitor watching a reel in its first 3 hours. You get the metrics "
        "history at each checkpoint. Steps:\n"
        "1. Call get_account_baseline (once) and get_reel_metrics / get_recent_comments as needed.\n"
        "2. Judge the trend: VIRAL, ON TRACK, SLOW or FLOPPING. Base it on view/reach velocity between "
        "checkpoints, shares and saves per view, and comments, relative to the account's baseline and size. "
        "Show the numbers behind the verdict.\n"
        "3. Act. You may reply to genuine comments (keep replies short, human, ending with a question to "
        "boost the thread) and hide spam - the user approves each one. Everything else is a recommendation "
        "for the user, e.g.: share to Story with a poll/question sticker, pin a comment, send to close "
        "friends/broadcast channel, collab invite, boost with ads, post a follow-up or 'part 2', or at the 3-hour "
        "mark if it clearly flopped: archive and re-post with a new hook/cover/time.\n"
        "Never delete, archive or re-post yourself - those are the user's call.\n"
        "End with: VERDICT, KEY NUMBERS, ACTIONS TAKEN, ACTIONS FOR YOU (prioritised), NEXT CHECK FOCUS."
    ),
    local_tools=MONITOR_TOOLS,
)

ALL_AGENTS = [content_writer, viral_strategist, performance_monitor]
