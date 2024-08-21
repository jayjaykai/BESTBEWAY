import os
from sqlalchemy import create_engine, Column, String, Integer, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import ForeignKey
from mysql.connector.pooling import MySQLConnectionPool
from dotenv import load_dotenv
from typing import Any, List, Dict
from google_search_api import SearchResult

load_dotenv()

Base = declarative_base()

class ArticlesRecommendedItems(Base):
    __tablename__ = "articles_recommended_items"

    id = Column(Integer, primary_key=True, index=True)
    recommended_items = Column(String(255), unique=True)  # recommended_items 防重入

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), index=True)
    link = Column(String(255))
    title = Column(String(255))
    snippet = Column(Text)
    recommended_items_id = Column(Integer, ForeignKey('articles_recommended_items.id'))

    # 加入資料防重入機制
    __table_args__ = (
        UniqueConstraint('query', 'link', name='_query_link_uc'),
    )

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
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=3306
        )

        self.engine = create_engine(f'mysql+mysqlconnector://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST", "localhost")}/{os.getenv("DB_NAME")}')
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

def get_articles_by_query(db_session: Session, query: str) -> List[Dict[str, Any]]:
    results = db_session.query(
        Article,
        ArticlesRecommendedItems.recommended_items
    ).join(
        ArticlesRecommendedItems,
        Article.recommended_items_id == ArticlesRecommendedItems.id
    ).filter(
        Article.query.ilike(f"%{query}%")
    ).all()

    # 將結果轉換為字典，以便更容易使用
    articles = []
    for article, recommended_items in results:
        articles.append({
            'link': article.link,
            'title': article.title,
            'snippet': article.snippet,
            'recommended_items': recommended_items
        })
    return articles

def save_articles(db_session: Session, articles: List[SearchResult], query: str, recommended_items: List[str]):
    print("Saving articles data into MySQL DB...")
    try:
        # check or insert recommended_items into the articles_recommended_items table
        recommended_items_str = ",".join(recommended_items)
        recommended_items_entry = db_session.query(ArticlesRecommendedItems).filter_by(recommended_items=recommended_items_str).first()

        if not recommended_items_entry:
            recommended_items_entry = ArticlesRecommendedItems(recommended_items=recommended_items_str)
            db_session.add(recommended_items_entry)
            db_session.flush()  # submit instead commit，to get id

        recommended_items_id = recommended_items_entry.id

        # insert articles data into the articles table
        for article in articles:
            db_article = Article(
                query=query,
                link=article.link,
                title=article.title,
                snippet=article.snippet,
                recommended_items_id=recommended_items_id
            )
            db_session.add(db_article)
        
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print("Failed to save articles:", str(e))
    finally:
        print(f"Saved articles data for query '{query}' into MySQL DB!")
        db_session.close()
