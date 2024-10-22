import asyncio
from fastapi import HTTPException
from model.mysql import get_session, get_articles_by_query, save_articles, get_null_hotkeys_articles_by_query
from model.cache import Cache
from model.google_search_api import search_articles, SearchResponse, SearchResult
import json
from concurrent.futures import ThreadPoolExecutor

async def search_articles_controller(query: str, start: int = 1, pages: int = 1) -> SearchResponse:
    async with get_session() as session:
        try:
            cache_key = f"articleCache#{query}_keyword"
            cached_data = Cache.redis_client.get(cache_key) if Cache.is_redis_available() else None
            
            if query != "寶寶常見問題":
                Cache.increment_keyword_score(query)
            
            if cached_data:
                print(f"Use Redis article Cache_{query}!")
                return json.loads(cached_data)
            
            print("Get data from MySQL DB...")
            db_articles = await get_articles_by_query(session, query)
            if db_articles:
                results = [SearchResult(title=article['title'], link=article['link'], snippet=article['snippet']) for article in db_articles]
                recommended_items = db_articles[0]['recommended_items'].split(",") if db_articles else []
                
                if Cache.is_redis_available():
                    print("Write Redis article Cache!")
                    Cache.redis_client.set(cache_key, json.dumps({"search_results": [result.dict() for result in results], "recommended_items": recommended_items}), ex=86400)
            else:
                results, recommended_items = await search_articles(query, start, pages)
                asyncio.create_task(save_articles(results, query, recommended_items))
                
                if Cache.is_redis_available():
                    print("Write Redis article Cache!")
                    Cache.redis_client.set(cache_key, json.dumps({"search_results": [result.dict() for result in results], "recommended_items": recommended_items}), ex=86400)

            print("Return data!")
            return SearchResponse(search_results=results, recommended_items=recommended_items)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

async def save_hot_keywords_articles_controller():
    async with get_session() as session:
        try:
            print("Get null hot keywords articles from MySQL DB...")
            hot_keywords = await get_null_hotkeys_articles_by_query(session)

            for keyword in hot_keywords:
                keyword_str = keyword['keyword']
                print(f"Processing articles for keyword: {keyword_str}")
                await search_articles_controller(keyword_str)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in save_hot_keywords_articles: {str(e)}")