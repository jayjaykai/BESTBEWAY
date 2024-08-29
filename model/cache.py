import os
from dotenv import load_dotenv
import redis

load_dotenv()


class Cache():
    def __init__(self):
        self.redis_client = None

    def create_redis_client(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", None)

        try:
            client = redis.StrictRedis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
            client.ping()
            print("Redis client done!")
            return client
        except redis.ConnectionError:
            print("Redis is None!")
            return None

    def is_redis_available(self):
        # if self.redis_client is None:
        # self.redis_client = self.create_redis_client()
        if self.redis_client is None:
            return False
        try:
            self.redis_client.ping()
            return True
        except redis.ConnectionError:
            self.redis_client = None
            return False 
    
    def increment_keyword_score(self, keyword):
        if self.is_redis_available():
            # 使用 ZINCRBY 增加關鍵字的熱門度
            self.redis_client.zincrby('top_keywords', 1, keyword)
            new_score = self.redis_client.zscore('top_keywords', keyword)
            print(f"Incremented score for keyword '{keyword}'. New score: {new_score}")

    def get_top_keywords(self, limit=10):
        if self.is_redis_available():
            # 獲取前 n 個熱門關鍵字
            keywords = self.redis_client.zrevrange('top_keywords', 0, limit-1, withscores=True)
            print(f"Top {limit} keywords with scores: {keywords}")
            return keywords
        return []
        
Cache = Cache()