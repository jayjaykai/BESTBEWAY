import os
import httpx
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from fastapi import HTTPException
from dotenv import load_dotenv
import jieba
from fuzzywuzzy import process

load_dotenv()  # 载入环境变量

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

class SearchResponse(BaseModel):
    search_results: List[SearchResult]
    recommended_items: List[str]

# 商品列表
queries = [
    "奶粉", "溫奶器", "消毒鍋", "奶嘴", "監視器", "安全座椅", "床",
    "防脹氣奶瓶", "益生菌", "寶乖亞", "固齒器", "吸鼻器", "衣服", "背帶",
    "副食品", "餐椅", "玩具", "安全護欄", "口水巾",
    "鞋子", "益智積木", "馬桶", "護膚膏", "白噪音", "腸絞痛","屁屁膏","乳液"
]

async def fetch_search_results(api_key: str, search_engine_id: str, query: str, start: int) -> List[Dict[str, Any]]:
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={query}&start={start}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Search API request failed")
    return response.json().get("items", [])

async def search_articles(query: str, start: int = 1) -> Tuple[List[SearchResult], List[str]]:
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID_Parenting")
    search_results = await fetch_search_results(api_key, search_engine_id, query, start)
    
    article_results = []
    combined_texts = []
    for item in search_results:
        snippet = item.get("snippet", "")
        htmlSnippet = item.get("htmlSnippet", "")
        og_description = ""
        pagemap = item.get("pagemap", {})
        if pagemap:
            metatags = pagemap.get("metatags", [])
            if metatags:
                og_description = metatags[0].get("og:description", "")
        
        combined_text = f"{snippet} {htmlSnippet} {og_description}"
        combined_texts.append(combined_text)

        result = SearchResult(
            title=item.get("title", ""),
            link=item.get("link", ""),
            snippet=snippet
        )
        article_results.append(result)

    combined_texts = " ".join(combined_texts)
    print("combined_texts: ", combined_texts)
    # 使用jieba进行分词
    words = jieba.lcut(combined_texts)

    # 定义匹配阈值
    threshold = 90

     # 比較網頁字串和商品列表，找到匹配的商品
    matched_items = set()
    for query in queries:
        for word in words:
            if query in word and len(word) > 1:  # 確保做匹配的字串長度大於1
                matched_items.add(query)
                break
        else:  # 如果没有匹配成功，进行模糊匹配
            fuzzy_results = process.extract(query, words, limit=10)
            for result in fuzzy_results:
                if result[1] >= threshold and len(result[0]) > 1:  # 確保做匹配的字串長度大於1
                    matched_items.add(query)
                    break

    print("Matched items:", list(matched_items))

    return article_results, list(matched_items)
    

# import os
# import httpx
# from typing import List, Dict, Any
# from pydantic import BaseModel
# from fastapi import HTTPException
# from dotenv import load_dotenv
# import jieba
# from fuzzywuzzy import process

# load_dotenv()  # 载入环境变量
# class SearchResult(BaseModel):
#     title: str
#     link: str
#     snippet: str

# class SearchResponse(BaseModel):
#     search_results: List[SearchResult]
#     recommended_items: List[str]

# # 商品列表
# queries = [
#     "奶粉", "溫奶器", "消毒鍋", "奶嘴", "監視器", "安全座椅", "床",
#     "防脹氣奶瓶", "益生菌", "寶乖亞", "固齒器", "吸鼻器", "衣服", "背帶",
#     "副食品", "餐椅", "玩具", "安全護欄", "口水巾",
#     "學步鞋子", "益智積木", "馬桶"
# ]

# async def fetch_search_results(api_key: str, search_engine_id: str, query: str, start: int) -> List[Dict[str, Any]]:
#     url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={search_engine_id}&q={query}&start={start}"
#     async with httpx.AsyncClient() as client:
#         response = await client.get(url)
#     if response.status_code != 200:
#         raise HTTPException(status_code=response.status_code, detail="Search API request failed")
#     return response.json().get("items", [])

# async def search_articles(query: str, start: int = 1) -> List[SearchResult]:
#     api_key = os.getenv("GOOGLE_API_KEY")
#     search_engine_id = os.getenv("SEARCH_ENGINE_ID_Parenting")
#     search_results = await fetch_search_results(api_key, search_engine_id, query, start)
    
#     results = []
#     combined_texts = []
#     for item in search_results:
#         snippet = item.get("snippet", "")
#         htmlSnippet = item.get("htmlSnippet", "")
#         og_description = ""
#         pagemap = item.get("pagemap", {})
#         if pagemap:
#             metatags = pagemap.get("metatags", [])
#             if metatags:
#                 og_description = metatags[0].get("og:description", "")
        
#         combined_text = f"{snippet} {htmlSnippet} {og_description}"
#         combined_texts.append(combined_text)
#         result = SearchResult(
#             title=item.get("title", ""),
#             link=item.get("link", ""),
#             snippet=snippet
#         )
#         results.append(result)

#     combined_texts = " ".join(combined_texts)
#     # 使用jieba进行分词
#     words = jieba.lcut(combined_texts)

#     # 定义匹配阈值
#     threshold = 80

#     # 比较抓取到的文本和商品列表，找到匹配的商品
#     matched_items = set()
#     for query in queries:
#         # 先检查字符串包含
#         if any(query in word for word in words):
#             matched_items.add(query)
#             continue
        
#         # 再进行模糊匹配
#         results = process.extract(query, words, limit=10)
#         for result in results:
#             if result[1] >= threshold:
#                 matched_items.add(query)
#                 break

#     print("Matched items:", list(matched_items))
#     # print("Words:", words)

#     return results, list(matched_items)
