"""Small Instagram Graph API client (Instagram Business or Creator account).

Needs two environment variables:
    IG_USER_ID       your Instagram professional account ID
    IG_ACCESS_TOKEN  a long-lived token with instagram_basic, instagram_content_publish,
                     instagram_manage_comments and instagram_manage_insights permissions

Read-only calls (metrics, comments) run freely. Calls that change the account
(publish, delete, reply, hide) go through base.approve() first.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

from .base import approve

GRAPH = f"https://graph.facebook.com/{os.environ.get('IG_GRAPH_VERSION', 'v23.0')}"
REEL_METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions", "ig_reels_avg_watch_time"]


class NotApproved(Exception):
    pass


def configured() -> bool:
    return bool(os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN"))


def _call(method: str, path: str, **params: Any) -> dict[str, Any]:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{GRAPH}/{path}", params=params, timeout=60)
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram API error: {data.get('error', {}).get('message', r.text)}")
    return data


# ----------------------------- read-only ----------------------------------

def get_media(media_id: str) -> dict[str, Any]:
    return _call("GET", media_id, fields="id,caption,media_type,permalink,timestamp,like_count,comments_count")


def get_reel_metrics(media_id: str) -> dict[str, Any]:
    """Current counts for a reel. Metrics the API rejects are skipped one by one."""
    out: dict[str, Any] = {}
    metrics = list(REEL_METRICS)
    while metrics:
        try:
            data = _call("GET", f"{media_id}/insights", metric=",".join(metrics))
            break
        except RuntimeError as e:
            bad = next((m for m in metrics if m in str(e)), None)
            if bad is None:
                raise
            metrics.remove(bad)
    else:
        data = {"data": []}
    for item in data.get("data", []):
        values = item.get("values") or [{}]
        out[item["name"]] = item.get("total_value", {}).get("value", values[0].get("value"))
    media = get_media(media_id)
    out.setdefault("likes", media.get("like_count"))
    out.setdefault("comments", media.get("comments_count"))
    out["timestamp"] = media.get("timestamp")
    out["permalink"] = media.get("permalink")
    return out


def get_comments(media_id: str, limit: int = 30) -> list[dict[str, Any]]:
    return _call("GET", f"{media_id}/comments", fields="id,text,username,timestamp", limit=limit).get("data", [])


def get_recent_reels(limit: int = 12) -> list[dict[str, Any]]:
    media = _call(
        "GET", f"{os.environ['IG_USER_ID']}/media",
        fields="id,media_type,media_product_type,timestamp,like_count,comments_count", limit=limit * 2,
    ).get("data", [])
    return [m for m in media if m.get("media_product_type") == "REELS"][:limit]


# --------------------- account-changing (need approval) --------------------

def publish_reel(video_url: str, caption: str, share_to_feed: bool = True) -> dict[str, Any]:
    if not approve("Publish a new reel", f"Video: {video_url}\n\nCaption:\n{caption}"):
        raise NotApproved("User declined publishing.")
    user = os.environ["IG_USER_ID"]
    container = _call(
        "POST", f"{user}/media", media_type="REELS", video_url=video_url,
        caption=caption, share_to_feed=str(share_to_feed).lower(),
    )["id"]
    for _ in range(60):  # Instagram processes the video before it can be published
        status = _call("GET", container, fields="status_code")["status_code"]
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram could not process the video (status {status}).")
        time.sleep(10)
    else:
        raise RuntimeError("Video still processing after 10 minutes.")
    media_id = _call("POST", f"{user}/media_publish", creation_id=container)["id"]
    return {"media_id": media_id, **get_media(media_id)}


def delete_media(media_id: str, reason: str) -> str:
    media = get_media(media_id)
    if not approve(
        "DELETE a post from your account (cannot be undone)",
        f"Post: {media.get('permalink')}\nCaption: {(media.get('caption') or '')[:200]}\nReason: {reason}",
    ):
        raise NotApproved("User declined deleting.")
    _call("DELETE", media_id)
    return f"Deleted {media_id}."


def reply_to_comment(comment_id: str, comment_text: str, message: str) -> str:
    if not approve("Reply to a comment", f"Comment: {comment_text}\n\nYour reply: {message}"):
        raise NotApproved("User declined this reply.")
    return _call("POST", f"{comment_id}/replies", message=message)["id"]


def hide_comment(comment_id: str, comment_text: str, reason: str) -> str:
    if not approve("Hide a comment", f"Comment: {comment_text}\nReason: {reason}"):
        raise NotApproved("User declined hiding.")
    _call("POST", comment_id, hide="true")
    return f"Hid comment {comment_id}."
