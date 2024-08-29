from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from controller.article_controller import search_articles_controller
from controller.product_controller import ProdSearchResult, search_product_controller
from controller.suggestions_controller import search_suggestions_controller
from controller.hot_keywords_controller import get_hot_keywords_controller
from model.google_search_api import SearchResponse
from pydantic import BaseModel
from typing import List

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def index(request: Request):
    return FileResponse("./static/index.html", media_type="text/html")

@app.get("/api/article", response_model=SearchResponse)
async def search(query: str, start: int = 1, pages: int = 1):
    try:
        response = await search_articles_controller(query, start, pages)
        return response
    except HTTPException as e:
        raise e

@app.get("/api/product", response_model=List[ProdSearchResult])
async def search_product(query: str, from_: int = 0, size: int = 50, current_page: int = 0, max_pages: int = 0):
    try:
        results = await search_product_controller(query, from_, size, current_page, max_pages)
        return results
    except HTTPException as e:
        raise e
    
@app.get("/api/search_suggestions", response_model=List[str])
def search_suggestions(query: str = Query(...)):
    try:
        suggestions = search_suggestions_controller(query)
        return suggestions
    except HTTPException as e:
        raise e

@app.get("/api/hot_keywords")
async def get_hot_keywords():
    return await get_hot_keywords_controller()