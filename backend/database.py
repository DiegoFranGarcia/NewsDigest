from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    summary = Column(Text)
    source = Column(String)
    published_at = Column(DateTime)
    cluster_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Text)
    category = Column(Text)

class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String)
    rating = Column(Integer)

def init_db():
    Base.metadata.create_all(engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()