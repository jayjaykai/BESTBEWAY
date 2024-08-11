from datetime import datetime
import json
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
from elasticsearch import Elasticsearch, exceptions
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv, set_key
import asyncio
from google_shopping import search_products
from model.elasticsearch_client import get_elasticsearch_client
from model.mysql import get_session, get_articles_by_query, save_articles, initialize_database, close_database, Article
from model.cache import Cache
from google_search_api import search_articles, SearchResult, SearchResponse
from apscheduler.schedulers.background import BackgroundScheduler
from model.getdataintoES import main as update_data

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
load_dotenv()

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

# Schedule the tasks
for i, queries in enumerate(queries_list):
    set_key('.env', 'QUERIES_GROUP_6', "")
    scheduler.add_job(update_data, 'cron', day_of_week="mon-sun", hour=(0 + i) % 24, minute=35, args=[queries])

scheduler.start()
@app.on_event("startup")
async def startup_event():
    print("Starting up FastAPI and APScheduler...")

# @app.get("/")
# async def read_root():
#     return {"message": "FastAPI with APScheduler is running!"}

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# Redis
Cache.redis_client = Cache.create_redis_client() 

# Elastic Search
# 應用啟動時初始化 Elasticsearch
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
        
        db_articles = get_articles_by_query(session, query)
        if db_articles:
            results = [SearchResult(title=article.title, link=article.link, snippet=article.snippet) for article in db_articles]
            recommended_items = db_articles[0].recommended_items.split(",") if db_articles else []
            if Cache.is_redis_available():    
                print("Write Redis article Cache!")
                Cache.redis_client.set(cache_key, json.dumps({"search_results": [result.dict() for result in results], "recommended_items": recommended_items}), ex=600)
        else:
            results, recommended_items = await search_articles(query, start, pages)
            save_articles(session, results, query, recommended_items)
            print("Write Redis article Cache!")
            Cache.redis_client.set(cache_key, json.dumps({"search_results": [result.dict() for result in results], "recommended_items": recommended_items}), ex=600)

        return SearchResponse(search_results=results, recommended_items=recommended_items)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# @app.get("/api/product", response_model=List[ProdSearchResult])
# async def search_product(query: str, from_: int = 0, size: int = 50, current_page: int = 0, max_pages: int = 0):
#     try:      
#         search_results = await search_products(query, from_=from_, size=size, current_page=current_page, max_pages=max_pages)
#         print("search_results: ", search_results)
#         return search_results
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

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