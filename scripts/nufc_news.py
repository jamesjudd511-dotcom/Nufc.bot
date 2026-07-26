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

def build_html_body():
    html = [f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Newcastle United Update</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 700px; margin: 20px auto; padding: 0 15px; }}
h1 {{ font-size: 20px; }}
h2 {{ font-size: 16px; color: #333; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
a {{ color: #1a73e8; text-decoration: none; }}
li {{ margin-bottom: 12px; }}
</style>
</head>
<body>
<h1>Newcastle United Update — {datetime.now().strftime('%A %d %B %Y, %H:%M')}</h1>
"""]
    for section, url in FEEDS.items():
        html.append(f"<h2>{section}</h2><ul>")
        entries = fetch_articles(url)
        if not entries:
            html.append("<li>No stories found.</li>")
        for entry in entries:
            title = entry.title
            link = entry.link
            source = entry.get("source", {}).get("title", "")
            html.append(f'<li><a href="{link}">{title}</a><br><small>{source}</small></li>')
        html.append("</ul>")
    html.append("</body></html>")
    return "\n".join(html)


def save_html(html):
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def send_email(body):
    msg = MIMEText(body)
    msg["Subject"] = f"NUFC News – {datetime.now().strftime('%d %b %Y')}"
    msg["From"] = os.environ["EMAIL_ADDRESS"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_ADDRESS"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)


if __name__ == "__main__":
    text_body = build_email_body()
    send_email(text_body)

    html_body = build_html_body()
    save_html(html_body)

