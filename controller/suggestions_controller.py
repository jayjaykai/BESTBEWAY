from fastapi import HTTPException
from model.mysql import get_session, get_suggestions
from model.cache import Cache
import unicodedata
import json

def normalize_query(query: str) -> str:
    # 移除所有注音符號（Unicode 範圍 0x3100-0x312F 和 0x31A0-0x31BF）
    normalized_query = unicodedata.normalize('NFKD', query)
    cleaned_query = ''.join(
        c for c in normalized_query if not (
            0x3100 <= ord(c) <= 0x312F or 
            0x31A0 <= ord(c) <= 0x31BF or 
            unicodedata.combining(c)
        )
    )
    cleaned_query = ''.join(c for c in cleaned_query if c.isalnum())
    cleaned_query = cleaned_query.lower()
    print(f"Normalized Query: '{cleaned_query}'")
    return cleaned_query

def search_suggestions_controller(query: str) -> list:
    session = get_session()
    try:
        normalized_query = normalize_query(query)
        if not normalized_query:
            print("Normalized Query is empty, skipping MySQL query.")
            return []
        
        cache_key = f"suggestionsCache#{normalized_query}"
        print(f"Cache Key: {cache_key}")

        cached_result = Cache.redis_client.get(cache_key) if Cache.redis_client else None
        if cached_result:
            if isinstance(cached_result, bytes):
                cached_result = cached_result.decode('utf-8')
            print(f"Use suggestionsCache {query} Cache!")
            return cached_result.split(',')

        print("Get suggestions from MySQL DB...")
        suggestions = get_suggestions(session, query)
        filtered_suggestions = [s for s in suggestions if query in s]

        if Cache.redis_client:
            print("Write Suggestions Cache!")
            Cache.redis_client.set(cache_key, ','.join(filtered_suggestions), ex=300)

        return filtered_suggestions

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()