#!/usr/bin/env python3
"""
Newcastle United Transfer News Bot
-----------------------------------
Pulls RSS feeds from football news sources, filters for Newcastle
transfer-related stories, and emails you a digest of anything new.

SETUP
1. pip install feedparser
2. Fill in the CONFIG section below (or set the equivalent env vars).
3. Run it: python nufc_transfer_bot.py
4. Schedule it (see bottom of this file for cron / GitHub Actions notes).

It keeps a small local file (seen_links.json) so it never emails you
the same story twice.
"""

import os
import re
import json
import smtplib
import feedparser
from email.mime.text import MIMEText
from pathlib import Path

# ============ CONFIG ============
# Fill these in, or set as environment variables of the same name.

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "youraddress@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "your-app-password")  # use an app password, not your real password
EMAIL_TO = os.environ.get("EMAIL_TO", "youraddress@gmail.com")

# Where "seen" story links are remembered between runs
SEEN_FILE = Path(__file__).parent / "seen_links.json"

# RSS feeds to check. Add/remove freely.
FEEDS = [
    "https://www.bbc.co.uk/sport/football/teams/newcastle-united/rss.xml",
    "https://www.skysports.com/rss/12040",              # Sky Sports football news (filtered below)
    "https://www.chroniclelive.co.uk/all-about/newcastle-united-fc?service=rss",
    "https://www.nufc.co.uk/feed/",
    "https://www.reddit.com/r/NUFC/.rss",
]

# Keywords that suggest a transfer story (case-insensitive)
TRANSFER_KEYWORDS = [
    "transfer", "sign", "signing", "signed", "bid", "medical",
    "loan", "linked", "fee", "release clause", "target", "swoop",
    "agree terms", "here we go", "deal", "close to", "in talks",
    "asking price", "scout", "interest in",
]

# Only needed for feeds (like Sky's general football feed) that aren't
# Newcastle-specific — we require "Newcastle" or "NUFC" in the text too.
REQUIRE_CLUB_MENTION_FEEDS = [
    "skysports.com",
]


def is_relevant(entry, feed_url):
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()

    has_transfer_word = any(kw in text for kw in TRANSFER_KEYWORDS)
    if not has_transfer_word:
        return False

    if any(domain in feed_url for domain in REQUIRE_CLUB_MENTION_FEEDS):
        if "newcastle" not in text and "nufc" not in text:
            return False

    return True


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    # Keep the file from growing forever — cap at last 500 links
    trimmed = list(seen)[-500:]
    SEEN_FILE.write_text(json.dumps(trimmed))


def clean_summary(summary, max_len=220):
    text = re.sub("<[^<]+?>", "", summary or "")  # strip HTML tags
    text = text.strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def collect_new_stories():
    seen = load_seen()
    new_stories = []

    for feed_url in FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"Failed to fetch {feed_url}: {e}")
            continue

        for entry in parsed.entries:
            link = entry.get("link", "")
            if not link or link in seen:
                continue
            if not is_relevant(entry, feed_url):
                continue

            new_stories.append({
                "title": entry.get("title", "(no title)"),
                "link": link,
                "summary": clean_summary(entry.get("summary", "")),
                "source": parsed.feed.get("title", feed_url),
            })
            seen.add(link)

    save_seen(seen)
    return new_stories


def build_email_body(stories):
    lines = [f"{len(stories)} new Newcastle transfer story/stories:\n"]
    for s in stories:
        lines.append(f"• {s['title']} ({s['source']})")
        if s["summary"]:
            lines.append(f"  {s['summary']}")
        lines.append(f"  {s['link']}\n")
    return "\n".join(lines)


def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())


def main():
    stories = collect_new_stories()
    if not stories:
        print("No new transfer stories found.")
        return

    body = build_email_body(stories)
    send_email(f"NUFC Transfer News: {len(stories)} new update(s)", body)
    print(f"Sent email with {len(stories)} new stories.")


if __name__ == "__main__":
    main()

# ============ SCHEDULING NOTES ============
# Set up to run 3x/day: morning, lunch, evening (UK time).
#
# Option A — cron (on your own machine / a server):
#   crontab -e
#   0 7 * * *  /usr/bin/python3 /path/to/nufc_transfer_bot.py   # 7am
#   0 12 * * * /usr/bin/python3 /path/to/nufc_transfer_bot.py   # 12pm
#   0 18 * * * /usr/bin/python3 /path/to/nufc_transfer_bot.py   # 6pm
#   (cron uses your machine's local timezone by default)
#
# Option B — GitHub Actions (free, runs even if your computer is off):
#   Create .github/workflows/nufc_bot.yml in a repo containing this script:
#
#   name: NUFC Transfer Bot
#   on:
#     schedule:
#       # GitHub Actions cron is UTC. UK is UTC+0 (winter) / UTC+1 (summer/BST).
#       # These times target roughly 7am / 12pm / 6pm UK time year-round by
#       # using two entries per slot (one for GMT, one for BST) — GitHub will
#       # just skip the "wrong" one having no effect, or simplest: pick UTC
#       # times and accept a 1hr drift during BST, adjust to taste.
#       - cron: '0 7 * * *'    # ~7am GMT / 8am BST
#       - cron: '0 12 * * *'   # ~12pm GMT / 1pm BST
#       - cron: '0 18 * * *'   # ~6pm GMT / 7pm BST
#     workflow_dispatch: {}
#   jobs:
#     run-bot:
#       runs-on: ubuntu-latest
#       steps:
#         - uses: actions/checkout@v4
#         - uses: actions/setup-python@v5
#           with: { python-version: '3.11' }
#         - run: pip install feedparser
#         - run: python nufc_transfer_bot.py
#           env:
#             SMTP_USER: ${{ secrets.SMTP_USER }}
#             SMTP_PASS: ${{ secrets.SMTP_PASS }}
#             EMAIL_TO: ${{ secrets.EMAIL_TO }}
#
#   (Store SMTP_USER/SMTP_PASS/EMAIL_TO as GitHub repo secrets — never
#   commit real credentials to the file. Also commit seen_links.json
#   after each run, or the bot will re-notify on every run — GitHub
#   Actions' filesystem doesn't persist between runs by default, so
#   you'd want to add a step that caches/commits that file back.)
