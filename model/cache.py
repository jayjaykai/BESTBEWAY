import os
from dotenv import load_dotenv
import redis
import jieba

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
            # 使用 ZINCRBY 增加關鍵字的熱搜數
            self.redis_client.zincrby('top_keywords', 1, keyword)
            new_score = self.redis_client.zscore('top_keywords', keyword)
            print(f"Incremented score for keyword '{keyword}'. New score: {new_score}")

    def get_top_keywords(self, limit=10):
        if self.is_redis_available():
            # 取得前10筆熱搜關鍵字
            keywords = self.redis_client.zrevrange('top_keywords', 0, limit-1, withscores=True)
            print(f"Top {limit} keywords with scores: {keywords}")
            return keywords
        return []
        
    def write_hot_keywords_to_redis(self, keywords_with_scores):
        try:
            if keywords_with_scores:
                print("Writing hot keywords to Redis...")
                for item in keywords_with_scores:
                    self.redis_client.zadd('top_keywords', {item['keyword']: item['score']})
        except Exception as e:
            print(f"Error occurred while writing data to Redis: {e}")

    def delete_all_cache_for_product_query(self, query):
        # 使用 jieba 分詞技術來處理多種相關關鍵字
        keywords = jieba.lcut_for_search(query)
        print(f"Use jieba keyword: {keywords}")
        
        if self.redis_client:
            for keyword in keywords:
                pattern = f"productCache#*{keyword}*"
                cursor = 0 
                cache_found = False

                while True:
                    cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=100)
                    
                    print(f"Cursor: {cursor}, Keys: {keys}")
                    
                    if keys:
                        self.redis_client.delete(*keys)
                        cache_found = True
                        print(f"Deleted Redis cache for keyword: {keyword}, keys: {keys}")
                    
                    if cursor == 0:
                        break
                
                if not cache_found:
                    print(f"No cache found for keyword: {keyword}")

    def delete_all_cache_for_article_query(self, query):
        # 組合articleCache#{query}_keyword
        pattern = f"articleCache#{query}_keyword"
        
        if self.redis_client:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                print(f"Deleted Redis cache for article query: {query}, keys: {keys}")
            else:
                print(f"No cache found for article query: {query}")            

Cache = Cache()