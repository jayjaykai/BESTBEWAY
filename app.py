from controller.hot_keywords_controller import save_hot_keywords_controller
from model.mysql import delete_7days_articles_data
from view.main_view import app
from model.cache import Cache
from model.getdataintoES import main as update_data
from apscheduler.schedulers.background import BackgroundScheduler
import os
from dotenv import load_dotenv, set_key

load_dotenv()

scheduler = BackgroundScheduler(timezone="Asia/Taipei")

# Read queries from environment variables
queries_list = [
    os.getenv("QUERIES_GROUP_1").split(","),
    os.getenv("QUERIES_GROUP_2").split(","),
    os.getenv("QUERIES_GROUP_3").split(","),
    os.getenv("QUERIES_GROUP_4").split(","),
    os.getenv("QUERIES_GROUP_5").split(","),
    os.getenv("QUERIES_GROUP_6").split(",")
]

print("queries_list: ", queries_list)
start_hour = int(os.getenv("SCHEDULE_STARTHOUR"))
between_hour = int(os.getenv("SCHEDULE_BETWEENHOUR"))
start_minute = int(os.getenv("SCHEDULE_STARTMIN"))
schedule_day = os.getenv("SCHEDULE_DAY")

# 每周更新商品資料
for i, queries in enumerate(queries_list):
    set_key('.env', 'QUERIES_GROUP_6', "")
    hour = start_hour + between_hour * i
    job_day = schedule_day

    # 檢查是否跨日
    if hour >= 24:
        hour = hour % 24
        job_day = str((int(schedule_day) + 1) % 7)

    print(f"APScheduler_1-{i} for crawling product data Starts at {hour}:{start_minute} on {job_day}")
    scheduler.add_job(
        update_data,
        'cron',
        day_of_week=job_day,
        hour=hour,
        minute=start_minute,
        args=[queries]
    )

# 每日刪除七日前 articles data
print(f"APScheduler_2 Deleting Job Start at {os.getenv('DELETE_SCHEDULE_HOUR')}:{os.getenv('DELETE_SCHEDULE_MINUTE')}")
scheduler.add_job(
    delete_7days_articles_data, 
    'cron', 
    day_of_week=os.getenv("DELETE_SCHEDULE_DAY"),
    hour=int(os.getenv("DELETE_SCHEDULE_HOUR")),
    minute=int(os.getenv("DELETE_SCHEDULE_MINUTE"))
)

# 每日更新熱搜文章關鍵字到RDS
print(f"APScheduler_3 Updating Hotkey Job Start at {os.getenv('UPDATE_HOTKEY_SCHEDULE_HOUR')}:{os.getenv('UPDATE_HOTKEY_SCHEDULE_MINUTE')}")
scheduler.add_job(
    save_hot_keywords_controller, 
    'cron', 
    day_of_week=os.getenv("UPDATE_HOTKEY_SCHEDULE_DAY"),
    hour=int(os.getenv("UPDATE_HOTKEY_SCHEDULE_HOUR")),
    minute=int(os.getenv("UPDATE_HOTKEY_SCHEDULE_MINUTE"))
)

scheduler.start()

@app.on_event("startup")
async def startup_event():
    print("Starting up FastAPI and APScheduler...")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# Redis
Cache.redis_client = Cache.create_redis_client() 