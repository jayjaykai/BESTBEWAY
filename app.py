from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
import asyncio
from elasticsearch import Elasticsearch
from google_shopping import search_products

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
load_dotenv()

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

class ProdSearchResult(BaseModel):
    title: str
    link: str
    price: str
    seller: str
    image: str
    timestamp: datetime

class ArticleContent(BaseModel):
    title: str
    link: str
    content: str    

@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")

@app.get("/api/article", response_model=List[SearchResult])
async def search(query: str, start: int = 1):
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID_Parenting")
 
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={query}&start={start}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Search API request failed")
    search_results = response.json().get("items", [])
    results = [
        SearchResult(title=item["title"], link=item["link"], snippet=item["snippet"]) 
        for item in search_results
    ]
    return results

@app.get("/api/product", response_model=List[ProdSearchResult])
async def search_product(query: str, from_: int = 0, size: int = 50, current_page: int = 0, max_pages: int = 0):
    try:
        search_results = await search_products(query, from_=from_, size=size, current_page=current_page, max_pages=max_pages)
        return search_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 寫在另一個爬蟲程式    
# def fetch_article_content(url):
#     response = requests.get(url)
#     if response.status_code == 200:
#         soup = BeautifulSoup(response.content, 'html.parser')
#         # 假设文章内容在<div>标签内，具体的选择器根据实际网页结构进行调整
#         content_div = soup.find('div', {'class': 'article-content'})
#         if content_div:
#             return content_div.get_text()
#     return None

# @app.get("/api/full_articles", response_model=List[ArticleContent])
# async def get_full_articles(query: str, start: int = 1):
#     search_results = await search(query, start)
#     full_articles = []
#     for result in search_results:
#         content = fetch_article_content(result.link)
#         if content:
#             full_articles.append(ArticleContent(title=result.title, link=result.link, content=content))
#     return full_articles    
