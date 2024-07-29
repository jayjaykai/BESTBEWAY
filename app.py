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

@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")

@app.get("/api/article", response_model=List[SearchResult])
async def search(query: str, start: int = 1):
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID_PTT")
    
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

# @app.get("/product", response_model=List[ProdSearchResult])
# async def search_product(query: str):
#     try:
#         search_results = await search_products(query)
#         return search_results
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/product", response_model=List[ProdSearchResult])
async def search_product(query: str, from_: int = 0, size: int = 50, current_page: int = 0):
    try:
        search_results = await search_products(query, from_=from_, size=size, current_page=current_page)
        return search_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# @app.get("/product", response_model=List[ProdSearchResult])
# async def search_product(query: str):
#     try:
#         search_results = await search_products(query)
#         return search_results
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
