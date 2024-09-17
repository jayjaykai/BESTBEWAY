from fastapi import HTTPException
from model.mysql import get_session, get_articles_by_query, save_articles
from model.cache import Cache
from model.google_search_api import search_articles, SearchResponse, SearchResult
import json
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

async def search_articles_controller(query: str, start: int = 1, pages: int = 1) -> SearchResponse:
    session = get_session()
    try:
        cache_key = f"articleCache#{query}_keyword"
        cached_data = Cache.redis_client.get(cache_key) if Cache.is_redis_available() else None
        
        # 增加關鍵字的熱門度
        if query!= "寶寶常見問題":
            Cache.increment_keyword_score(query)
        
        if cached_data:
            print(f"Use Redis article Cache_{query}!")
            return json.loads(cached_data)
        
        print("Get data from MySQL DB...")
        db_articles = get_articles_by_query(session, query)
        if db_articles:
            results = [SearchResult(title=article['title'], link=article['link'], snippet=article['snippet']) for article in db_articles]
            recommended_items = db_articles[0]['recommended_items'].split(",") if db_articles else []
            
            if Cache.is_redis_available():
                print("Write Redis article Cache!")
                Cache.redis_client.set(cache_key, json.dumps({"search_results": [result.dict() for result in results], "recommended_items": recommended_items}), ex=86400)
            
            session.close()
        else:
            results, recommended_items = await search_articles(query, start, pages)
            executor.submit(save_articles, session, results, query, recommended_items)
            
            if Cache.is_redis_available():
                print("Write Redis article Cache!")
                Cache.redis_client.set(cache_key, json.dumps({"search_results": [result.dict() for result in results], "recommended_items": recommended_items}), ex=86400)

        print("Return data!")
        return SearchResponse(search_results=results, recommended_items=recommended_items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))