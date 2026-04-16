import sys
import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import sqlalchemy as sa

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Article, Cluster, engine

load_dotenv()

SessionLocal = sessionmaker(bind=engine)
model = SentenceTransformer("all-MiniLM-L6-v2")

CATEGORIES = [
    "Politics", "Technology", "Finance",
    "Health", "Sports", "World", "Entertainment", "Science"
]

CATEGORY_KEYWORDS = {
    "Politics": ["trump", "biden", "congress", "senate", "democrat", "republican", "election", "president", "white house", "vote", "political", "government", "law", "court", "supreme", "dhs", "iran", "immigration"],
    "Technology": ["ai", "artificial intelligence", "tech", "software", "apple", "google", "meta", "microsoft", "openai", "robot", "chip", "data", "cyber", "hack", "startup", "silicon"],
    "Finance": ["stock", "market", "economy", "fed", "interest rate", "inflation", "bank", "investment", "crypto", "nasdaq", "s&p", "finance", "oil", "trade", "gdp", "recession"],
    "Health": ["health", "covid", "vaccine", "cancer", "drug", "fda", "hospital", "mental health", "disease", "virus", "medical", "doctor", "study", "obesity", "diabetes"],
    "Sports": ["nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball", "baseball", "tennis", "olympic", "athlete", "game", "championship", "coach", "player", "team"],
    "World": ["ukraine", "russia", "china", "europe", "africa", "middle east", "war", "military", "nato", "israel", "gaza", "climate", "global", "international", "united nations"],
    "Entertainment": ["movie", "film", "music", "celebrity", "netflix", "hollywood", "award", "actor", "singer", "tv", "show", "album", "concert", "streaming", "disney"],
    "Science": ["science", "space", "nasa", "research", "climate", "environment", "biology", "physics", "study", "discovery", "planet", "species", "quantum", "gene"]
}

def assign_category(summary):
    if not summary:
        return "World"
    summary_lower = summary.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for kw in keywords if kw in summary_lower)
    return max(scores, key=scores.get)

def cleanup_old_data(db, hours=48):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    old_articles = db.query(Article).filter(Article.created_at < cutoff).all()
    old_cluster_ids = set(a.cluster_id for a in old_articles if a.cluster_id)

    for article in old_articles:
        db.delete(article)

    for cluster_id in old_cluster_ids:
        remaining = db.query(Article).filter(Article.cluster_id == cluster_id).count()
        if remaining == 0:
            cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
            if cluster:
                db.delete(cluster)

    db.commit()
    print(f"Cleaned up {len(old_articles)} old articles and {len(old_cluster_ids)} old clusters")

def get_recent_unclustered_articles(db, hours=48):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.query(Article).filter(
        Article.cluster_id == None,
        Article.created_at >= cutoff
    ).all()

def generate_embeddings(articles):
    texts = [f"{a.title}. {a.summary}" for a in articles]
    print(f"Generating embeddings for {len(texts)} articles...")
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings

def cluster_articles(embeddings, distance_threshold=0.8):
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average"
    )
    return clustering.fit_predict(embeddings)

def save_clusters(db, articles, labels, embeddings):
    unique_labels = set(labels)
    print(f"\nFound {len(unique_labels)} clusters from {len(articles)} articles")

    for label in unique_labels:
        cluster = Cluster(created_at=datetime.now(timezone.utc))
        db.add(cluster)
        db.flush()

        indices = [i for i, l in enumerate(labels) if l == label]
        clustered_articles = [articles[i] for i in indices]
        cluster_embeddings = [embeddings[i] for i in indices]

        avg_embedding = np.mean(cluster_embeddings, axis=0).tolist()
        cluster.embedding = json.dumps(avg_embedding)

        for article in clustered_articles:
            article.cluster_id = cluster.id

        print(f"  Cluster {cluster.id}: {len(clustered_articles)} articles")
        for a in clustered_articles[:2]:
            print(f"    - {a.title[:60]}")

    db.commit()
    print("\nClusters saved!")

def assign_categories(db):
    clusters = db.query(Cluster).filter(Cluster.category == None).all()
    for cluster in clusters:
        cluster.category = assign_category(cluster.summary)
    db.commit()
    print(f"Assigned categories to {len(clusters)} clusters")

def run_clustering():
    db = SessionLocal()
    try:
        print("Cleaning up old data...")
        cleanup_old_data(db, hours=48)

        articles = get_recent_unclustered_articles(db, hours=48)
        if not articles:
            print("No new articles to cluster.")
            return

        embeddings = generate_embeddings(articles)
        labels = cluster_articles(embeddings)
        save_clusters(db, articles, labels, embeddings)
    finally:
        db.close()

if __name__ == "__main__":
    run_clustering()