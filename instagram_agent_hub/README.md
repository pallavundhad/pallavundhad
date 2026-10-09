# Instagram Agent Hub

One **main agent** connected to **4 agents** that work together on Instagram Reels, from studying a reference reel to the first 3 hours after you post.

```
                          ┌───────────────────────────────┐
         you  ◀────────▶  │          MAIN AGENT           │
     (approve every       │ plans, delegates, merges.     │
      post / delete)      │ Only one allowed to post or   │
                          │ delete, and only after you    │
                          │ type "yes".                   │
                          └───────────────┬───────────────┘
        ┌───────────────────┬─────────────┴──────┬────────────────────────┐
        ▼                   ▼                    ▼                        ▼
 1. reel_analyzer     2. content_writer    3. viral_strategist    4. performance_monitor
 reel → speech,       script, captions,    likes, comments,       checks at 30/60/120/180 min,
 hook, captions,      hashtags, how the    shares, followers      viral or not, then acts
 draft captions       reel should look     plan (web search)      (replies need your OK)
 → WORD FILE
```

| # | Agent | What you get |
|---|---|---|
| 1 | **Reel Analyzer** | A **Word document (.docx)** with the hook (spoken, on-screen, visual, and why it works), how the speech is delivered (tone, pace, energy, techniques), the full timestamped transcript, every on-screen caption, the posted caption and hashtags, the beat-by-beat structure, 3 draft captions and 5 hook ideas |
| 2 | **Content Writer** | Hook options, a timestamped script, how the reel should look (framing, angles, lighting, transitions, text style, audio, length, cover), captions with a call to action, and hashtags split into broad, mid and niche |
| 3 | **Viral Strategist** | A plan for before posting, the first 60 minutes, and triggers for comments, saves, shares and follows, plus 1 h and 3 h targets for your account size. Only tactics allowed under Instagram's rules |
| 4 | **Performance Monitor** | Checks the reel 30, 60, 120 and 180 minutes after posting. Gives a verdict (VIRAL, ON TRACK, SLOW or FLOPPING) with the numbers behind it, replies to comments (you approve each one), and gives you a prioritised list of actions |

## Your approval is required, and it's enforced in code

Nothing is **posted, deleted, replied to or hidden** on your account unless you type `yes` at a prompt like this:

```
======================================================================
APPROVAL NEEDED: Publish a new reel
----------------------------------------------------------------------
Video: https://.../my-reel.mp4
Caption: ...
======================================================================
Type "yes" to allow, anything else to cancel:
```

The check is inside the functions that call Instagram (`instagram_api.py`), so no agent can skip it. If there's no terminal to ask in, the action is cancelled. Deleting, archiving or re-posting is never done by the monitor. It only recommends them to you.

## Setup

```bash
pip install -r requirements.txt          # also needs ffmpeg installed (apt/brew install ffmpeg)
export ANTHROPIC_API_KEY=sk-ant-...      # or: ant auth login
```

**To connect your Instagram account** (needed for publishing, deleting and live monitoring; analysing reels and writing content work without it):

1. Have an Instagram **Business or Creator** account linked to a Facebook Page.
2. Create an app at developers.facebook.com. Get a long-lived token with `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments` and `instagram_manage_insights`.
3. Set the following:
   ```bash
   export IG_USER_ID=1784...          # your Instagram professional account ID
   export IG_ACCESS_TOKEN=EAAG...
   ```

If you don't connect it, the monitor runs in **manual mode**: at each checkpoint it asks you to type the numbers from Insights.

**Analysing other people's reels from a URL:** Instagram usually requires a logged-in session. Export your browser cookies to a file and set `IG_COOKIES_FILE=cookies.txt`. Alternatively, save the reel and pass the `.mp4` file path, which always works. Use it for studying content, not re-uploading it.

## Run

```bash
# Chat with the main agent: it runs the whole flow
python -m instagram_agent_hub
you> Analyse https://www.instagram.com/reel/XXXX/ and write me a similar reel for my home bakery in Pune, in Hinglish

# One-shot
python -m instagram_agent_hub "Break down this reel: ~/Downloads/reel.mp4 and plan how to make mine go viral"

# Agent 1 only: reel → Word file
python -m instagram_agent_hub analyze https://www.instagram.com/reel/XXXX/
python -m instagram_agent_hub analyze ~/Downloads/reel.mp4

# Agent 4 only: 3-hour monitor for a reel you already posted
python -m instagram_agent_hub monitor 17912345678901234
```

Word files, monitor logs and reports are saved in `reports/`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `HUB_MODEL` | `claude-opus-5-5` | Model for all agents |
| `HUB_ORCHESTRATOR_EFFORT` / `HUB_SUBAGENT_EFFORT` | `high` / `medium` | Reasoning effort |
| `WHISPER_MODEL` | `small` | Speech-to-text model (`tiny`, `base`, `small`, `medium`, `large-v3`); bigger is more accurate, especially for Hindi or Hinglish |
| `HUB_REPORTS_DIR` | `reports` | Output folder |
| `IG_GRAPH_VERSION` | `v23.0` | Instagram Graph API version |

## Notes and limits

- Speech-to-text runs **locally** with faster-whisper. The model downloads the first time you run it.
- Claude reads 16 frames from each reel, sampled densely in the first 3 seconds to capture the hook. It reads on-screen text from those frames.
- Publishing needs the video at a **public URL** (an Instagram API requirement). If you're not connected, the main agent tells you to post manually.
- Instagram may not allow deleting posts through the API for every account type. If Meta rejects it, the agent tells you to delete it in the app.
- Every request also allows a server-side fallback: if Claude's safety filter declines a request, it's retried on another model.
