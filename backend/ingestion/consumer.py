import json
from kafka import KafkaConsumer
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Article, engine

load_dotenv()

SessionLocal = sessionmaker(bind=engine)

def run_consumer():
    consumer = KafkaConsumer(
        "articles",
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="newsdigest-consumer"
    )

    print("Consumer started, waiting for articles...")
    db = SessionLocal()

    try:
        for message in consumer:
            article_data = message.value

            existing = db.query(Article).filter_by(url=article_data["url"]).first()
            if existing:
                print(f"  Skipping duplicate: {article_data['title'][:50]}")
                continue

            article = Article(
                id=article_data["id"],
                title=article_data["title"],
                url=article_data["url"],
                summary=article_data["summary"],
                source=article_data["source"],
                published_at=datetime.fromisoformat(article_data["published_at"]),
            )

            db.add(article)
            db.commit()
            print(f"  Saved: {article_data['title'][:60]}")

    except KeyboardInterrupt:
        print("\nConsumer stopped.")
    finally:
        db.close()

if __name__ == "__main__":
    run_consumer()