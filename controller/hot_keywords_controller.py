from fastapi import HTTPException
from model.cache import Cache
from model.mysql import get_session, save_hot_keywords_to_db, get_hot_keywords_from_db

async def get_hot_keywords_controller():
    try:
        # 前10個熱門關鍵字及其分數
        hot_keywords = Cache.get_top_keywords(limit=10)
        keywords_with_scores = [{"keyword": keyword, "score": score} for keyword, score in hot_keywords]
        
        if not keywords_with_scores:
            print("Redis cache is empty. Fetching from RDS...")
            session = get_session()
            db_keywords = get_hot_keywords_from_db(session)
            keywords_with_scores = [{"keyword": keyword.keyword, "score": keyword.score} for keyword in db_keywords]
            # 將資料寫入 Redis
            Cache.write_hot_keywords_to_redis(keywords_with_scores)
   
        return {"hot_keywords": keywords_with_scores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def save_hot_keywords_controller():
    session = get_session()
    try:
        # 從 Redis 獲取前10個熱門關鍵字及其分數
        hot_keywords = Cache.get_top_keywords(limit=10)
        keywords_with_scores = [{"keyword": keyword, "score": score} for keyword, score in hot_keywords]

        if not keywords_with_scores:
            print("No hot keywords to save.")
            return
        
        # 將熱門關鍵字和分數寫入 MySQL
        success = save_hot_keywords_to_db(session, keywords_with_scores)
        if success:
            print("Hot keywords saved to RDS successfully.")
        else:
            print("Failed to save hot keywords to RDS.")

    except Exception as e:
        print(f"Error occurred while saving hot keywords to DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to save hot keywords to database.")