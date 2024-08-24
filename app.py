from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import unicodedata
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv, set_key
from google_shopping import search_products
from model.elasticsearch_client import get_elasticsearch_client
from model.mysql import get_session, get_articles_by_query, save_articles, get_suggestions, initialize_database, close_database, Article
from model.cache import Cache
from google_search_api import search_articles, SearchResult, SearchResponse
from apscheduler.schedulers.background import BackgroundScheduler
from model.getdataintoES import main as update_data

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
load_dotenv()

executor = ThreadPoolExecutor(max_workers=2)
# Create an APScheduler instance
scheduler = BackgroundScheduler(timezone="Asia/Taipei")

# Read queries from environment variables
queries_list = [
    os.getenv("QUERIES_GROUP_1").split(","),
    os.getenv("QUERIES_GROUP_2").split(","),
    os.getenv("QUERIES_GROUP_3").split(","),
    os.getenv("QUERIES_GROUP_4").split(","),
    os.getenv("QUERIES_GROUP_5").split(","),
    os.getenv("QUERIES_GROUP_6").split(",")
]

print("queries_list: ", queries_list)
print(f"APScheduler Start in every {os.getenv('SCHEDULE_DAY')}")
print(f"APScheduler Start at {os.getenv('SCHEDULE_STARTHOUR')}:{os.getenv('SCHEDULE_STARTMIN')}")
print(f"APScheduler Jobs between every {os.getenv('SCHEDULE_BETWEENHOUR') } hour(s)")

# Schedule the tasks
for i, queries in enumerate(queries_list):
    set_key('.env', 'QUERIES_GROUP_6', "")
    scheduler.add_job(update_data, 'cron', day_of_week=os.getenv("SCHEDULE_DAY"), hour=(int(os.getenv("SCHEDULE_STARTHOUR")) + int(os.getenv("SCHEDULE_BETWEENHOUR"))*i) % 24, minute=int(os.getenv("SCHEDULE_STARTMIN")), args=[queries])

scheduler.start()
@app.on_event("startup")
async def startup_event():
    print("Starting up FastAPI and APScheduler...")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# Redis
Cache.redis_client = Cache.create_redis_client() 

# Elastic Search
es = get_elasticsearch_client()

class ProdSearchResult(BaseModel):
    title: str
    link: str
    price: str
    seller: str
    image: str
    timestamp: datetime

@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")

@app.get("/api/article", response_model=SearchResponse)
async def search(query: str, start: int = 1, pages: int = 1):
    session = get_session()
    try:
        cache_key = f"articleCache#{query}_keyword"
        if Cache.is_redis_available():
            cached_data = Cache.redis_client.get(cache_key)
        if cached_data:
            print("Use Redis article Cache!")
            return JSONResponse(content=json.loads(cached_data))
        
        print("Get data from MySQL DB...")
        db_articles = get_articles_by_query(session, query)
        if db_articles:
            results = []
            for article in db_articles:
                result = SearchResult(
                    title=article['title'],
                    link=article['link'],
                    snippet=article['snippet']
                )
                results.append(result)

            recommended_items = db_articles[0]['recommended_items'].split(",") if db_articles else []
            if Cache.is_redis_available():    
                print("Write Redis article Cache!")
                Cache.redis_client.set(
                    cache_key, 
                    json.dumps({
                        "search_results": [result.dict() for result in results], 
                        "recommended_items": recommended_items
                    }), 
                    ex=600
                )
        else:
            results, recommended_items = await search_articles(query, start, pages)
            # 使用執行緒來非同步執行 save_articles
            executor.submit(save_articles, session, results, query, recommended_items)
            print("Write Redis article Cache!")
            Cache.redis_client.set(
                cache_key, 
                json.dumps({
                    "search_results": [result.dict() for result in results], 
                    "recommended_items": recommended_items
                }), 
                ex=600
            )
        print("Return data!")
        return SearchResponse(search_results=results, recommended_items=recommended_items)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/product", response_model=List[ProdSearchResult])
async def search_product(query: str, from_: int = 0, size: int = 50, current_page: int = 0, max_pages: int = 0):
    try:
        cache_key = f"productCache#{current_page}_{query}_keyword"
        cached_results = None
        
        if Cache.redis_client:
            cached_data = Cache.redis_client.get(cache_key)
            if cached_data:
                print(f"Use Redis Product {current_page}_{query} Cache!")
                cached_results = json.loads(cached_data)
                return [ProdSearchResult(**result) for result in cached_results["items"]]

        search_results = await search_products(query, from_=from_, size=size, current_page=current_page, max_pages=max_pages)
        # print("search_Product_results :", search_results)
        
        if Cache.redis_client:
            print("Write Redis Product Cache!")
            Cache.redis_client.set(cache_key, json.dumps(search_results), ex=600)
        
        return [ProdSearchResult(**result) for result in search_results["items"]]
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
     
def remove_zhuyin_symbols(query: str) -> str:
    # 移除所有注音符號（Unicode 範圍 0x3100-0x312F 和 0x31A0-0x31BF）
    normalized_query = unicodedata.normalize('NFKD', query)
    cleaned_query = ''.join(
        c for c in normalized_query if not (
            0x3100 <= ord(c) <= 0x312F or 
            0x31A0 <= ord(c) <= 0x31BF or 
            unicodedata.combining(c)
        )
    )
    return cleaned_query

def normalize_query(query: str) -> str:
    # 移除注音符號，將字串換成小寫，移除所有非字母數字
    cleaned_query = remove_zhuyin_symbols(query)
    # 保留字母和数字
    cleaned_query = ''.join(c for c in cleaned_query if c.isalnum())
    cleaned_query = cleaned_query.lower()
    print(f"Normalized Query: '{cleaned_query}'")
    return cleaned_query

@app.get("/api/search_suggestions", response_model=List[str])
async def search_suggestions(query: str = Query(...)):
    session = get_session()
    try:
        normalized_query = normalize_query(query)
        # 如果 normalized_query 是空字串，返回空陣列
        if not normalized_query:
            print("Normalized Query is empty, skipping MySQL query.")
            return []
        
        cache_key = f"suggestionsCache#{normalized_query}"

        print(f"Cache Key: {cache_key}")  # 印出 cache key value

        if Cache.redis_client:
            cached_result = Cache.redis_client.get(cache_key)
            if cached_result:
                # 確認解碼後為字串
                if isinstance(cached_result, bytes):
                    cached_result = cached_result.decode('utf-8')
                print(f"Use suggestionsCache {query} Cache!")
                return cached_result.split(',')

        print("Get suggestions from MySQL DB...")
        suggestions = get_suggestions(session, query)
        filtered_suggestions = []
        for s in suggestions:
            if query in s:
                filtered_suggestions.append(s)

        if Cache.redis_client:
            print("Write Suggestions Cache!")
            Cache.redis_client.set(cache_key, ','.join(filtered_suggestions), ex=300)
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return filtered_suggestions
