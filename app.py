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
print(f"APScheduler Start in every {os.getenv('SCHEDULE_DAY')}")
print(f"APScheduler Start at {os.getenv('SCHEDULE_STARTHOUR')}:{os.getenv('SCHEDULE_STARTMIN')}")
print(f"APScheduler Jobs between every {os.getenv('SCHEDULE_BETWEENHOUR') } hour(s)")
print(f"APScheduler Deleting Job Start at {os.getenv('DELETE_SCHEDULE_HOUR')}:{os.getenv('DELETE_SCHEDULE_MINUTE')}")
print(f"APScheduler Updating Hotkey Job Start at {os.getenv('UPDATE_HOTKEY_SCHEDULE_HOUR')}:{os.getenv('UPDATE_HOTKEY_SCHEDULE_MINUTE')}")

for i, queries in enumerate(queries_list):
    set_key('.env', 'QUERIES_GROUP_6', "")
    scheduler.add_job(
        update_data, 
        'cron', 
        day_of_week=os.getenv("SCHEDULE_DAY"), 
        hour=(int(os.getenv("SCHEDULE_STARTHOUR")) + int(os.getenv("SCHEDULE_BETWEENHOUR"))*i) % 24, 
        minute=int(os.getenv("SCHEDULE_STARTMIN")), 
        args=[queries]
    )

# 每日刪除七日前 articles data
scheduler.add_job(
    delete_7days_articles_data, 
    'cron', 
    day_of_week=os.getenv("DELETE_SCHEDULE_DAY"),
    hour=int(os.getenv("DELETE_SCHEDULE_HOUR")),
    minute=int(os.getenv("DELETE_SCHEDULE_MINUTE"))
)

# 每日更新熱搜文章關鍵字到RDS
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