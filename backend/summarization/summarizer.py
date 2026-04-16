import sys
import os
import anthropic
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Article, Cluster, engine

load_dotenv()

SessionLocal = sessionmaker(bind=engine)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def get_unsummarized_clusters(db):
    return db.query(Cluster).filter(Cluster.summary == None).all()

def get_cluster_articles(db, cluster_id):
    return db.query(Article).filter(Article.cluster_id == cluster_id).all()

def summarize_cluster(articles):
    if len(articles) == 1:
        return articles[0].summary or articles[0].title

    articles_text = "\n\n".join([
        f"Article {i+1} ({a.source}):\nTitle: {a.title}\nSummary: {a.summary}"
        for i, a in enumerate(articles)
    ])

    prompt = f"""You are a news editor. Below are {len(articles)} news articles that cover related topics.

{articles_text}

Instructions:
- If these articles are all about the same specific news event, write a single clean 3-4 sentence summary combining the key information from all sources.
- If the articles are about more than one distinct news event, write a summary of only the single most important story. Do not mention the other stories at all.
- Be factual, neutral, and concise.
- Do not mention the sources by name.
- Do not use markdown headers or bullet points. Plain text only.
- Never explain that articles are unrelated. Always just write a clean summary of the best story.

Summary:"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text.strip()

def run_summarization():
    db = SessionLocal()
    try:
        clusters = get_unsummarized_clusters(db)
        print(f"Found {len(clusters)} clusters to summarize\n")

        for cluster in clusters:
            articles = get_cluster_articles(db, cluster.id)
            print(f"Summarizing cluster {cluster.id} ({len(articles)} articles)...")

            summary = summarize_cluster(articles)
            cluster.summary = summary
            db.commit()

            print(f"  → {summary[:120]}...\n")

        print("All clusters summarized!")
    finally:
        db.close()

if __name__ == "__main__":
    run_summarization()