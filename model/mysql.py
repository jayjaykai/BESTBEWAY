import os
import time
from sqlalchemy import create_engine, Column, String, Integer, Text, UniqueConstraint, desc, func, text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import ForeignKey
from mysql.connector.pooling import MySQLConnectionPool
from dotenv import load_dotenv
from typing import Any, List, Dict
from model.google_search_api import SearchResult
from model.cache import Cache
from sqlalchemy.exc import IntegrityError

load_dotenv()

Base = declarative_base()

class ArticlesRecommendedItems(Base):
    __tablename__ = "articles_recommended_items"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255))
    recommended_items = Column(String(255), unique=True)  # recommended_items 防重入

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), index=True)
    link = Column(String(255))
    title = Column(String(255))
    snippet = Column(Text)
    recommended_items_id = Column(Integer, ForeignKey('articles_recommended_items.id'))
    created_at = Column(DateTime, server_default=func.now())

    # 加入資料防重入機制
    __table_args__ = (
        UniqueConstraint('query', 'link', name='_query_link_uc'),
    )

class HotKeywords(Base):
    __tablename__ = "articles_hot_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False, unique=True)
    score = Column(Integer, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class DBConfig:
    def __init__(self):
        self.pool = None
        self.engine = None
        self.SessionLocal = None

    def initialize_mysql_pool(self):
        pool_size_str = os.getenv("POOL_SIZE")
        pool_size = 32 if pool_size_str is None else int(pool_size_str)

        self.engine = create_engine(
            f'mysql+mysqlconnector://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST", "localhost")}/{os.getenv("DB_NAME")}',
            pool_size=pool_size,
            max_overflow=10,
            pool_pre_ping=True
        )
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

    articles = []
    for article, recommended_items in results:
        articles.append({
            'link': article.link,
            'title': article.title,
            'snippet': article.snippet,
            'recommended_items': recommended_items
        })
    return articles

def get_null_hotkeys_articles_by_query(db_session: Session) -> List[Dict[str, Any]]:
    # subquery
    subquery = (
        db_session.query(HotKeywords.keyword, HotKeywords.score)
        .order_by(HotKeywords.score.desc())
        .limit(10)
        .subquery()
    )
    # main query
    results = (
        db_session.query(subquery.c.keyword)
        .outerjoin(Article, Article.query == subquery.c.keyword)
        .filter(Article.query == None)
        .all()
    )
    
    return [{'keyword': row.keyword} for row in results]

def save_articles(db_session: Session, articles: List[SearchResult], query: str, recommended_items: List[str]):
    print("Saving articles data into MySQL DB...")
    try:
        # check or insert recommended_items into the articles_recommended_items table
        recommended_items_str = ",".join(recommended_items)
        recommended_items_entry = db_session.query(ArticlesRecommendedItems).filter_by(recommended_items=recommended_items_str).with_for_update().first()

        if not recommended_items_entry:
            recommended_items_entry = ArticlesRecommendedItems(recommended_items=recommended_items_str, query=query)
            db_session.add(recommended_items_entry)
            db_session.flush()  # 提交但不 commit，來取得 ID

        recommended_items_id = recommended_items_entry.id

        # Insert articles data into the articles table
        for article in articles:
            existing_article = db_session.query(Article).filter_by(query=query, link=article.link).with_for_update().first()

            if existing_article:
                print(f"Article already exists for query '{query}' and link '{article.link}', skipping insertion.")
                continue

            db_article = Article(
                query=query,
                link=article.link,
                title=article.title,
                snippet=article.snippet,
                recommended_items_id=recommended_items_id
            )
            db_session.add(db_article)    
        db_session.commit()

    except IntegrityError as e:
        db_session.rollback()
        print(f"IntegrityError: Duplicate entry found for query '{query}' or link already exists.")

    except Exception as e:
        db_session.rollback()
        print("Failed to save articles:", str(e))

    finally:
        print(f"Saved articles data for query '{query}' into MySQL DB!")
        db_session.close()

def get_suggestions(db_session: Session, query: str):
    results = db_session.query(
        ArticlesRecommendedItems.query
    ).filter(
        ArticlesRecommendedItems.query.ilike(f"%{query}%")
    ).all()

    suggestions = []
    for r in results:
        suggestions.append(r.query)
    return suggestions

async def delete_7days_articles_data(retries=3, delay=5):
    for attempt in range(retries):
        db_session = None
        try:
            db_session = get_session()
            if db_session is None:
                raise OperationalError("Session not available", params=None, orig=None)

            # 設定刪除7天前的資料
            seven_days_ago = func.now() - text('INTERVAL 7 DAY')
            articles_to_delete = db_session.query(Article).filter(Article.created_at < seven_days_ago).all()
            recommended_items_ids_to_delete = [article.recommended_items_id for article in articles_to_delete if article.recommended_items_id is not None]

            # 刪除 articles 表中的資料
            result_articles = db_session.query(Article).filter(Article.created_at < seven_days_ago).delete(synchronize_session='fetch')

            # 刪除 articles_recommended_items 表中的資料
            result_recommended_items = 0
            if recommended_items_ids_to_delete:
                result_recommended_items = db_session.query(ArticlesRecommendedItems).filter(
                    ArticlesRecommendedItems.id.in_(recommended_items_ids_to_delete)
                ).delete(synchronize_session='fetch')

            db_session.commit()
            print(f"Deleted {result_articles} rows from Articles table.")
            print(f"Deleted {result_recommended_items} rows from ArticlesRecommendedItems table.")
            # 使用一個 set 來存放已經刪除過快取的 query，避免重複刪除
            deleted_queries = set()
            for article in articles_to_delete:
                article_query = article.query             
                # 如果該 query 尚未刪除過快取，執行快取刪除
                if article_query not in deleted_queries:
                    Cache.delete_all_cache_for_article_query(article_query)
                    deleted_queries.add(article_query)
                
            break

        except OperationalError as op_err:
            print(f"OperationalError: {op_err}. Attempt {attempt + 1} of {retries}")
            if db_session:
                db_session.rollback()
            time.sleep(delay)

        except Exception as e:
            if db_session:
                db_session.rollback()
            print(f"Error occurred while deleting data: {e}")
            break

        finally:
            if db_session:
                db_session.close()

    else:
        print("Failed to delete data after several attempts.")

def get_hot_keywords_from_db(db_session: Session):
    try:
        keywords = db_session.query(HotKeywords).order_by(desc(HotKeywords.score)).limit(10).all()
        return keywords
    except Exception as e:
        print(f"Error occurred while fetching data from RDS: {e}")
    finally:
        db_session.close()

def save_hot_keywords_to_db(db_session: Session, keywords_with_scores):
    try:
        for item in keywords_with_scores:
            keyword = item["keyword"]
            score = item["score"]

            # 檢查是否已存在該關鍵字
            existing_entry = db_session.query(HotKeywords).filter_by(keyword=keyword).first()

            if existing_entry:
                # 更新已有的關鍵字分數
                existing_entry.score = score
            else:
                # 插入新關鍵字及其分數
                new_entry = HotKeywords(keyword=keyword, score=score)
                db_session.add(new_entry)

        db_session.commit()
        return True

    except Exception as e:
        db_session.rollback()
        print(f"Error occurred while saving data: {e}")
        return False

    finally:
        db_session.close()