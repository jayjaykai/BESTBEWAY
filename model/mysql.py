import os
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from mysql.connector.pooling import MySQLConnectionPool
from dotenv import load_dotenv
from typing import Any, List, Dict
from google_search_api import SearchResult

load_dotenv()

Base = declarative_base()

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), index=True)
    link = Column(String(255))
    title = Column(String(255))
    snippet = Column(Text)
    recommended_items = Column(String(255))

class DBConfig:
    def __init__(self):
        self.pool = None
        self.engine = None
        self.SessionLocal = None

    def initialize_mysql_pool(self):
        pool_size_str = os.getenv("POOL_SIZE")
        pool_size = 5 if pool_size_str is None else int(pool_size_str)

        self.pool = MySQLConnectionPool(
            pool_name="myPool",
            pool_size=pool_size,
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=3306
        )

        self.engine = create_engine(f'mysql+mysqlconnector://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}/{os.getenv("DB_NAME")}')
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def close_connection_pool(self):
        if self.pool:
            self.pool.close()

    def get_session(self) -> Session:
        if self.pool is None:
            self.initialize_mysql_pool()
        return self.SessionLocal()

db = DBConfig()

def get_session():
    return db.get_session()

def initialize_database():
    db.initialize_mysql_pool()
    Base.metadata.create_all(bind=db.engine)

def close_database():
    db.close_connection_pool()

def get_articles_by_query(db_session: Session, query: str) -> List[Article]:
    return db_session.query(Article).filter(Article.query.ilike(f"%{query}%")).all()

def save_articles(db_session: Session, articles: List[SearchResult], query: str, recommended_items: List[str]):
    try:
        for article in articles:
            db_article = Article(
                query=query,
                link=article.link,
                title=article.title,
                snippet=article.snippet,
                recommended_items=",".join(recommended_items)
            )
            # print("db_article: ", db_article)
            db_session.add(db_article)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print("Failed to save articles:", str(e))
    finally:
        db_session.close()
