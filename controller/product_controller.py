from fastapi import HTTPException
from model.cache import Cache
from model.google_shopping import search_products
from datetime import datetime
import json
from pydantic import BaseModel
from typing import List

class ProdSearchResult(BaseModel):
    title: str
    link: str
    price: str
    seller: str
    image: str
    timestamp: datetime

async def search_product_controller(query: str, from_: int = 0, size: int = 50, current_page: int = 0, max_pages: int = 0) -> List[ProdSearchResult]:
    try:
        cache_key = f"productCache#{current_page}_{query}_keyword"
        cached_results = Cache.redis_client.get(cache_key) if Cache.redis_client else None
        
        if cached_results:
            print(f"Use Redis Product {current_page}_{query} Cache!")
            return [ProdSearchResult(**result) for result in json.loads(cached_results)["items"]]

        # 使用 await 非同步函數
        search_results = await search_products(query, from_=from_, size=size, current_page=current_page, max_pages=max_pages)
        
        if Cache.redis_client:
            print("Write Redis Product Cache!")
            Cache.redis_client.set(cache_key, json.dumps(search_results), ex=86400)
        
        return [ProdSearchResult(**result) for result in search_results["items"]]
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
