from fastapi import HTTPException
from model.cache import Cache

async def get_hot_keywords_controller():
    try:
        # 前10個熱門關鍵字及其分數
        hot_keywords = Cache.get_top_keywords(limit=10)
        keywords_with_scores = [{"keyword": keyword, "score": score} for keyword, score in hot_keywords]
        
        return {"hot_keywords": keywords_with_scores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
