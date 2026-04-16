import feedparser
import hashlib
import json
from datetime import datetime, timezone
from kafka import KafkaProducer
from dotenv import load_dotenv
import os
import time
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

FEEDS = [
    # CNN
    {"url": "http://rss.cnn.com/rss/cnn_topstories.rss", "source": "CNN"},
    {"url": "http://rss.cnn.com/rss/cnn_world.rss", "source": "CNN"},
    {"url": "http://rss.cnn.com/rss/cnn_tech.rss", "source": "CNN"},

    # Fox News
    {"url": "https://moxie.foxnews.com/google-publisher/latest.xml", "source": "Fox News"},
    {"url": "https://moxie.foxnews.com/google-publisher/politics.xml", "source": "Fox News"},

    # ABC News
    {"url": "https://abcnews.go.com/abcnews/topstories", "source": "ABC News"},
    {"url": "https://abcnews.go.com/abcnews/politicsheadlines", "source": "ABC News"},

    # CBS News
    {"url": "https://www.cbsnews.com/latest/rss/main", "source": "CBS News"},
    {"url": "https://www.cbsnews.com/latest/rss/politics", "source": "CBS News"},

    # CNBC
    {"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "source": "CNBC"},
    {"url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "source": "CNBC"},

    # NY Post
    {"url": "https://nypost.com/feed/", "source": "NY Post"},

    # The Hill
    {"url": "https://thehill.com/feed/", "source": "The Hill"},

    # Politico
    {"url": "https://rss.politico.com/politics-news.xml", "source": "Politico"},

    # Ars Technica
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "source": "Ars Technica"},

    # Scientific American
    {"url": "https://www.scientificamerican.com/feed/", "source": "Scientific American"},
]

def create_producer():
    return KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

def parse_date(entry):
    try:
        return datetime(*entry.published_parsed[:6]).isoformat()
    except:
        return datetime.now(timezone.utc).isoformat()

def parse_standard(entry, source):
    return {
        "title": entry.get("title", "").strip(),
        "url": entry.get("link", "").strip(),
        "summary": entry.get("summary", "").strip(),
        "source": source,
        "published_at": parse_date(entry),
    }

def parse_reddit(entry, source):
    title = entry.get("title", "").strip()
    # Reddit summary contains HTML, grab just the linked URL if possible
    url = entry.get("link", "").strip()
    summary = entry.get("summary", "")
    # Strip HTML tags from reddit summary
    import re
    summary = re.sub(r"<[^>]+>", "", summary).strip()
    summary = summary[:500] if len(summary) > 500 else summary
    return {
        "title": title,
        "url": url,
        "summary": summary,
        "source": source,
        "published_at": parse_date(entry),
    }

def scrape_feeds(producer):
    total_sent = 0
    for feed_info in FEEDS:
        source = feed_info["source"]
        feed_type = feed_info.get("type", "standard")
        print(f"Scraping {source} ({feed_info['url'].split('/')[2]})...")

        try:
            feed = feedparser.parse(
                feed_info["url"],
                request_headers={
                    "User-Agent": "Mozilla/5.0 (compatible; NewsDigest/1.0)",
                    "Accept": "application/rss+xml, application/xml, text/xml"
                }
            )

            if not feed.entries:
                print(f"  No entries found, skipping")
                continue

            for entry in feed.entries:
                if feed_type == "reddit":
                    article_data = parse_reddit(entry, source)
                else:
                    article_data = parse_standard(entry, source)

                if not article_data["title"] or not article_data["url"]:
                    continue

                article_id = hashlib.md5(article_data["url"].encode()).hexdigest()
                article_data["id"] = article_id

                producer.send("articles", value=article_data)
                total_sent += 1
                print(f"  → {article_data['title'][:60]}")

            time.sleep(1)

        except Exception as e:
            print(f"  Error scraping {source}: {e}")
            continue

    producer.flush()
    print(f"\nDone! Sent {total_sent} articles to Kafka.")

if __name__ == "__main__":
    producer = create_producer()
    scrape_feeds(producer)