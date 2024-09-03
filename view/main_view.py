from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from controller.article_controller import search_articles_controller
from controller.product_controller import ProdSearchResult, search_product_controller
from controller.suggestions_controller import search_suggestions_controller
from controller.hot_keywords_controller import get_hot_keywords_controller, save_hot_keywords_controller
from model.google_search_api import SearchResponse
from pydantic import BaseModel
from typing import List

app = FastAPI(title="APIs for BestBeWay")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def index(request: Request):
    return FileResponse("./static/index.html", media_type="text/html")

@app.get("/api/article", response_model=SearchResponse, tags=["查詢推薦文章"])
async def search(query: str, start: int = 1, pages: int = 1):
    try:
        response = await search_articles_controller(query, start, pages)
        return response
    except HTTPException as e:
        raise e

@app.get("/api/product", response_model=List[ProdSearchResult], tags=["查詢推薦商品"])
async def search_product(query: str, from_: int = 0, size: int = 50, current_page: int = 0, max_pages: int = 0):
    try:
        results = await search_product_controller(query, from_, size, current_page, max_pages)
        return results
    except HTTPException as e:
        raise e
    
@app.get("/api/search_suggestions", response_model=List[str], tags=["搜尋出現相關關鍵字內容"])
def search_suggestions(query: str = Query(...)):
    try:
        suggestions = search_suggestions_controller(query)
        return suggestions
    except HTTPException as e:
        raise e

@app.get("/api/hot_keywords", tags=["取得前十筆熱搜關鍵字"])
async def get_hot_keywords():
    try:
        # await save_hot_keywords_controller()
        return await get_hot_keywords_controller()
    except HTTPException as e:
        raise e