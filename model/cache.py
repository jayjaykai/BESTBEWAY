import os
from dotenv import load_dotenv
import redis

load_dotenv()


class Cache():
    def __init__(self):
        self.max = 10
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
        
    def update_top_searches(self, attraction_id):
        if self.is_redis_available():
            new_searches = self.redis_client.lrange("new_searches", 0, -1)
            attraction_id_str = str(attraction_id)
            # print(f"Initial new_searches: {new_searches}")
            
            if attraction_id_str in new_searches:
                new_searches.remove(attraction_id_str)
                # print(f"Removed {attraction_id_str} from new_searches: {new_searches}")
            
            # 將當前搜尋的景點 ID 插入到列表的最前面
            new_searches.insert(0, attraction_id_str)
            new_searches = new_searches[:self.max]
            # print(f"new_searches to max {self.max}: {new_searches}")
            # 更新 Redis 中的列表
            self.redis_client.delete("new_searches")
            self.redis_client.rpush("new_searches", *new_searches)
            # print(f"Updated new_searches in Redis: {new_searches}")
    
    def get_top_searches(self):
        if self.is_redis_available():
            return self.redis_client.lrange("new_searches", 0, self.max-1)
        return []
        
Cache = Cache()