import feedparser
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime

FEEDS = {
    "General news": "https://news.google.com/rss/search?q=Newcastle+United&hl=en-GB&gl=GB&ceid=GB:en",
    "Transfer gossip": "https://news.google.com/rss/search?q=Newcastle+United+transfer+OR+gossip+OR+rumour&hl=en-GB&gl=GB&ceid=GB:en",
}

def fetch_articles(url, limit=8):
    feed = feedparser.parse(url)
    return feed.entries[:limit]

def build_email_body():
    lines = [f"Newcastle United Update — {datetime.now().strftime('%A %d %B %Y, %H:%M')}\n"]
    for section, url in FEEDS.items():
        lines.append(f"\n=== {section} ===\n")
        entries = fetch_articles(url)
        if not entries:
            lines.append("No stories found.\n")
        for entry in entries:
            title = entry.title
            link = entry.link
            source = entry.get("source", {}).get("title", "")
            lines.append(f"- {title} ({source})\n  {link}\n")
    return "\n".join(lines)

def body):
    msg = MIMEText(body)
    msg["Subject"] = f"NUFC News — {datetime.now().strftime('%d %b, %H:%M')}"
    msg["From"] = os.environ["EMAIL_ADDRESS"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_ADDRESS"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

if __name__ == "__main__":
    body = build_email_body()
    send_email(body)
    print("Email sent.")
