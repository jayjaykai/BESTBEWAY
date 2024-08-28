import asyncio
from itertools import cycle
import os
import httpx
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from fastapi import HTTPException
from dotenv import load_dotenv
import jieba
from fuzzywuzzy import process
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

class SearchResponse(BaseModel):
    search_results: List[SearchResult]
    recommended_items: List[str]

# 商品列表
product_queries = os.getenv('PRODUCT_QUERIES').split(',')

async def fetch_search_result(client: httpx.AsyncClient, api_key: str, search_engine_id: str, query: str, start: int) -> List[Dict[str, Any]]:
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={query}&start={start}"
    print(f"Fetch data from url: {url}")
    response = await client.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Search API request failed")
    return response.json().get("items", [])

async def fetch_all_results(api_key: str, query: str, start: int, num_pages: int, search_engine_ids: List[str]) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        tasks = []
        for search_engine_id in search_engine_ids:
            for i in range(num_pages):
                tasks.append(fetch_search_result(client, api_key, search_engine_id, query, start + i * 10))
        results = await asyncio.gather(*tasks)
    items = [item for sublist in results for item in sublist]
    return items

async def search_articles(query: str, start: int = 1, num_pages: int = 5) -> List[SearchResult]:
    print("Get data from Google API...")
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_ids = [
        os.getenv("SEARCH_ENGINE_ID_Parenting"),
        os.getenv("SEARCH_ENGINE_ID_Mababy"),
        os.getenv("SEARCH_ENGINE_ID_Mamaway")
    ]
    search_results = await fetch_all_results(api_key, query, start, num_pages, search_engine_ids)
    
    article_results = []
    all_words = []

    for item in search_results:
        snippet = item.get("snippet", "")
        htmlSnippet = item.get("htmlSnippet", "")
        og_description = ""
        pagemap = item.get("pagemap", {})
        if pagemap:
            metatags = pagemap.get("metatags", [])
            if metatags:
                og_description = metatags[0].get("og:description", "")
        
        combined_text = f"{snippet} {htmlSnippet} {og_description}" # {htmlSnippet} {og_description}
        words = jieba.lcut(combined_text)  # 將每頁的字串資料做分詞
        all_words.extend(words)

        result = SearchResult(
            title=item.get("title", ""),
            link=item.get("link", ""),
            snippet=snippet
        )
        article_results.append(result)

    # print("all_words: ", all_words)
    # 定義 threshold
    threshold = 90

    # 比較網頁字串和商品列表，找到匹配的商品
    matched_items = set()
    for query in product_queries:
        for word in all_words:
            if query in word and len(word) > 1:  # 確保做匹配的字串長度大於1
                # print("matched word add: ", word)
                matched_items.add(query)
                break
        else:  # 如果没有匹配成功，進行模糊匹配
            fuzzy_results = process.extract(query, all_words, limit=10)
            for result in fuzzy_results:
                if result[1] >= threshold and len(result[0]) > 1:  # 確保分詞字串長度大於1再做匹配
                    print("fuzzy_results: ", result)
                    # print("matched_items add: ", query)
                    matched_items.add(query)
                    break

    print("Matched items:", list(matched_items))

    return article_results, list(matched_items)