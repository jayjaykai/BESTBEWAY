import asyncio
import os
import time
from sqlalchemy import create_engine, Column, String, Integer, Text, UniqueConstraint, delete, desc, func, text, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import ForeignKey
# from sqlalchemy.future import select
from mysql.connector.pooling import MySQLConnectionPool
from dotenv import load_dotenv
from typing import Any, List, Dict
from model.google_search_api import SearchResult
from model.cache import Cache
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager

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


class AsyncDBConfig:
    def __init__(self):
        self.engine = None
        self.AsyncSessionLocal = None

    def initialize_mysql_pool(self):
        pool_size = int(os.getenv("POOL_SIZE", 32))
        self.engine = create_async_engine(
            f'mysql+asyncmy://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST", "localhost")}/{os.getenv("DB_NAME")}',
            pool_size=pool_size,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self.AsyncSessionLocal = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=AsyncSession
        )

db = AsyncDBConfig()
db.initialize_mysql_pool()

@asynccontextmanager
async def get_session():
    async with db.AsyncSessionLocal() as session:
        yield session

async def get_articles_by_query(db_session: AsyncSession, query: str) -> List[Dict[str, Any]]:
    stmt = (
        select(Article, ArticlesRecommendedItems.recommended_items)
        .join(ArticlesRecommendedItems, Article.recommended_items_id == ArticlesRecommendedItems.id)
        .filter(Article.query.ilike(f"%{query}%"))
    )
    results = await db_session.execute(stmt)
    articles = []
    for article, recommended_items in results.fetchall():
        articles.append({
            'link': article.link,
            'title': article.title,
            'snippet': article.snippet,
            'recommended_items': recommended_items
        })
    return articles

async def get_null_hotkeys_articles_by_query(db_session: AsyncSession) -> List[Dict[str, Any]]:
    subquery = (
        select(HotKeywords.keyword, HotKeywords.score)
        .order_by(HotKeywords.score.desc())
        .limit(10)
        .subquery()
    )

    stmt = (
        select(subquery.c.keyword)
        .outerjoin(Article, Article.query == subquery.c.keyword)
        .where(Article.query == None)
    )

    results = await db_session.execute(stmt)
    return [{'keyword': row.keyword} for row in results.fetchall()]


async def save_articles(articles: List[SearchResult], query: str, recommended_items: List[str]):
    print("Saving articles data into MySQL DB...")
    async with get_session() as db_session:  # 產生不同session處理
        try:
            recommended_items_str = ",".join(recommended_items)
            recommended_items_entry = await db_session.execute(
                select(ArticlesRecommendedItems)
                .filter(ArticlesRecommendedItems.recommended_items == recommended_items_str)
                .with_for_update()
            )
            recommended_items_entry = recommended_items_entry.scalar_one_or_none()

            if not recommended_items_entry:
                recommended_items_entry = ArticlesRecommendedItems(recommended_items=recommended_items_str, query=query)
                db_session.add(recommended_items_entry)
                await db_session.flush()
            
            recommended_items_id = recommended_items_entry.id

            for article in articles:
                existing_article = await db_session.execute(
                    select(Article)
                    .filter(Article.query == query, Article.link == article.link)
                    .with_for_update()
                )
                existing_article = existing_article.scalar_one_or_none()

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

            await db_session.commit()

        except IntegrityError:
            await db_session.rollback()
            print(f"IntegrityError: Duplicate entry found for query '{query}' or link already exists.")
        
        except Exception as e:
            await db_session.rollback()
            print(f"Failed to save articles: {str(e)}")

        finally:
            print(f"Saved articles data for query '{query}' into MySQL DB!")

async def get_suggestions(db_session: AsyncSession, search_query: str) -> List[str]:
    stmt = select(ArticlesRecommendedItems.query).where(
        ArticlesRecommendedItems.query.ilike(f"%{search_query}%")
    )
    
    results = await db_session.execute(stmt)
    
    # suggestions = [row.query for row in results.scalars().all()]
    suggestions = results.scalars().all()
    return suggestions

async def delete_7days_articles_data(retries=3, delay=5):
    for attempt in range(retries):
        db_session = None
        try:
            async with get_session() as db_session:

                # 設定刪除7天前的資料
                seven_days_ago = func.now() - text('INTERVAL 7 DAY')

                articles_to_delete = await db_session.execute(
                    select(Article).where(Article.created_at < seven_days_ago)
                )
                articles_to_delete = articles_to_delete.scalars().all()

                # 獲取要刪除的推薦商品 ID
                recommended_items_ids_to_delete = [
                    article.recommended_items_id for article in articles_to_delete
                    if article.recommended_items_id is not None
                ]

                # 刪除 Articles 中的資料
                result_articles = await db_session.execute(
                    delete(Article).where(Article.created_at < seven_days_ago)
                    .execution_options(synchronize_session=False)
                )

                # 刪除 ArticlesRecommendedItems 中的資料
                result_recommended_items = 0
                if recommended_items_ids_to_delete:
                    result_recommended_items = await db_session.execute(
                        delete(ArticlesRecommendedItems).where(
                            ArticlesRecommendedItems.id.in_(recommended_items_ids_to_delete)
                        ).execution_options(synchronize_session=False)
                    )

                await db_session.commit()
                print(f"Deleted {result_articles.rowcount} rows from Articles table.")
                print(f"Deleted {result_recommended_items} rows from ArticlesRecommendedItems table.")

                # 清除快取
                deleted_queries = set()
                for article in articles_to_delete:
                    article_query = article.query             
                    if article_query not in deleted_queries:
                        Cache.delete_all_cache_for_article_query(article_query)
                        deleted_queries.add(article_query)

                break

        except OperationalError as op_err:
            print(f"OperationalError: {op_err}. Attempt {attempt + 1} of {retries}")
            if db_session:
                await db_session.rollback()
            await asyncio.sleep(delay)

        except Exception as e:
            if db_session:
                await db_session.rollback()
            print(f"Error occurred while deleting data: {e}")
            break

        finally:
            if db_session:
                await db_session.close()

    else:
        print("Failed to delete data after several attempts.")

async def get_hot_keywords_from_db(db_session: AsyncSession):
    try:
        result = await db_session.execute(
            select(HotKeywords)
            .order_by(desc(HotKeywords.score))
            .limit(10)
        )
        keywords = result.scalars().all()  # 使用 scalars().all() 來處理多個記錄
        return keywords

    except Exception as e:
        print(f"Error occurred while fetching data from RDS: {e}")

async def save_hot_keywords_to_db(db_session: AsyncSession, keywords_with_scores):
    try:
        for item in keywords_with_scores:
            keyword = item["keyword"]
            score = item["score"]

            existing_entry = await db_session.execute(
                select(HotKeywords).filter_by(keyword=keyword)
            )
            existing_entry = existing_entry.scalar_one_or_none()

            if existing_entry:
                existing_entry.score = score
            else:
                new_entry = HotKeywords(keyword=keyword, score=score)
                db_session.add(new_entry)

        await db_session.commit()
        return True

    except Exception as e:
        await db_session.rollback()
        print(f"Error occurred while saving data: {e}")
        return False