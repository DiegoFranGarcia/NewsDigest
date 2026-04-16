import sys
import os
import json
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Article, Cluster, UserFeedback, engine

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionLocal = sessionmaker(bind=engine)

@app.get("/")
def root():
    return {"message": "NewsDigest API is running"}

@app.get("/clusters")
def get_clusters():
    db = SessionLocal()
    try:
        clusters = db.query(Cluster).filter(Cluster.summary != None).all()
        preference_embedding = get_preference_embedding(db)

        result = []
        for cluster in clusters:
            articles = db.query(Article).filter(Article.cluster_id == cluster.id).all()
            
            score = 0.0
            if preference_embedding is not None and cluster.embedding:
                cluster_emb = json.loads(cluster.embedding)
                score = cosine_similarity(preference_embedding, cluster_emb)

            result.append({
                "id": cluster.id,
                "summary": cluster.summary,
                "article_count": len(articles),
                "sources": list(set(a.source for a in articles)),
                "score": score,
                "articles": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "url": a.url,
                        "source": a.source,
                        "published_at": str(a.published_at),
                    }
                    for a in articles
                ],
            })

        result.sort(key=lambda x: x["score"], reverse=True)
        return result
    finally:
        db.close()

@app.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: int):
    db = SessionLocal()
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        articles = db.query(Article).filter(Article.cluster_id == cluster_id).all()
        return {
            "id": cluster.id,
            "summary": cluster.summary,
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "url": a.url,
                    "source": a.source,
                    "published_at": str(a.published_at),
                }
                for a in articles
            ],
        }
    finally:
        db.close()

@app.post("/feedback")
def submit_feedback(payload: dict):
    db = SessionLocal()
    try:
        existing = db.query(UserFeedback).filter(
            UserFeedback.article_id == payload["article_id"]
        ).first()

        if existing:
            existing.rating = payload["rating"]
            db.commit()
            return {"message": "Feedback updated"}
        else:
            feedback = UserFeedback(
                article_id=payload["article_id"],
                rating=payload["rating"]
            )
            db.add(feedback)
            db.commit()
            return {"message": "Feedback saved"}
    finally:
        db.close()

def get_preference_embedding(db):
    liked_feedback = db.query(UserFeedback).filter(UserFeedback.rating == 1).all()
    if not liked_feedback:
        return None

    liked_article_ids = [f.article_id for f in liked_feedback]
    liked_cluster_ids = set()
    for article_id in liked_article_ids:
        article = db.query(Article).filter(Article.id == article_id).first()
        if article and article.cluster_id:
            liked_cluster_ids.add(article.cluster_id)

    if not liked_cluster_ids:
        return None

    liked_embeddings = []
    for cluster_id in liked_cluster_ids:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if cluster and cluster.embedding:
            liked_embeddings.append(json.loads(cluster.embedding))

    if not liked_embeddings:
        return None

    return np.mean(liked_embeddings, axis=0)

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

@app.get("/search")
def search_articles(q: str):
    db = SessionLocal()
    try:
        articles = db.query(Article).filter(
            Article.title.ilike(f"%{q}%")
        ).limit(20).all()
        return [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "cluster_id": a.cluster_id,
            }
            for a in articles
        ]
    finally:
        db.close()

@app.get("/my-ratings")
def get_my_ratings():
    db = SessionLocal()
    try:
        feedback = db.query(UserFeedback).all()
        return [{"article_id": f.article_id, "rating": f.rating} for f in feedback]
    finally:
        db.close()