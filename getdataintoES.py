from datetime import datetime
import re
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv
import random
import time
import concurrent.futures
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gc
from model.elasticsearch_client import get_elasticsearch_client

load_dotenv()

def ensure_es_client_initialized():
    es = get_elasticsearch_client("Local")
    if es is None:
        raise Exception("Failed to initialize Elasticsearch client.")
    return es
# es = None
# # 初始化 Elasticsearch 客户端
# try:
#     es = Elasticsearch(
#         ["http://localhost:9200/"],
#         basic_auth=(os.getenv("ELASTICSEARCH_USERNAME"), os.getenv("ELASTICSEARCH_PASSWORD"))
#     )
#     if not es.ping():
#         raise exceptions.ConnectionError("Elasticsearch server is not reachable")
# except exceptions.ConnectionError as e:
#     print(f"Error connecting to Elasticsearch: {e}")
# except Exception as e:
#     print(f"Unexpected error: {e}")

# index_name = "products"
# try:
#     # 拿掉一開始把Elastic database 全部的資料刪除，改在爬取資料前刪除該query的資料
#     # es.indices.delete(index=index_name, ignore=[400, 404])
#     # print("Testing and deleting data at first!")
#     if not es.indices.exists(index=index_name):
#         es.indices.create(index=index_name, body={
#             "mappings": {
#                 "properties": {
#                     "query": {"type": "text"},
#                     "title": {"type": "text"},
#                     "link": {"type": "text"},
#                     "price": {"type": "text"},
#                     "seller": {"type": "text"},
#                     "image": {"type": "text"},
#                     "timestamp": {"type": "date"}
#                 }
#             }
#         })
# except exceptions.ConnectionError as e:
#     print(f"Error connecting to Elasticsearch: {e}")
# except exceptions.RequestError as e:
#     print(f"Error creating index: {e}")

class Generator:
    @staticmethod
    def striphtml(data):
        p = re.compile(r'<.*?>')
        return p.sub('', data)

    @staticmethod
    def removeDuplicates(List):
        return list(set(List))

    @staticmethod
    def split2Words(str):
        newList = []
        for i in range(len(str) - 1):
            newList.append(str[i:i + 2])
        return newList

    @staticmethod
    def split3Words(str):
        subList = []
        for i in range(len(str) - 2):
            subList.append(str[i:i + 3])
        return subList

    @staticmethod
    def splitString(str):
        str = Generator.striphtml(str)
        ChiList = re.sub(u"([^\u4e00-\u9fa5])", " ", str).split(" ")
        ChiList = Generator.removeDuplicates(ChiList)
        ChiList = list(filter(None, ChiList))
        newList = []
        for item in ChiList:
            if len(item) > 4:
                newList = newList + Generator.split2Words(item)
                newList = newList + Generator.split3Words(item)
        newList = Generator.removeDuplicates(newList)
        ChiList = ChiList + newList
        ChiStr = ' '.join(ChiList)
        return ChiStr.split()

def split_basic_words(str):
    ChiList = re.sub(u"([^\u4e00-\u9fa5])", " ", str).split(" ")
    ChiList = Generator.removeDuplicates(ChiList)
    ChiList = list(filter(None, ChiList))
    newList = []
    for item in ChiList:
        if len(item) > 3:
            newList = newList + Generator.split2Words(item)
    newList = Generator.removeDuplicates(newList)
    ChiList = ChiList + newList
    return ChiList

def calculate_matching_rate(query, title):
    query_words = split_basic_words(query)
    title_words = Generator.splitString(title)
    query_set = set(query_words)
    title_set = set(title_words)
    matching_count = sum(1 for word in query_set if word in title_set)
    matching_rate = matching_count / len(query_set) if len(query_set) > 0 else 0
    return matching_rate

def fetch_content(url, headers):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={headers['User-Agent']}")
        chrome_options.add_argument(f"referer={headers['Referer']}")
        # 設定 Chrome Driver 的執行黨路徑
        chrome_options.chrome_executable_path=os.getenv("CHROMEDRIVER_PATH")
        # 建立 Driver 物件實體，用程式操作瀏覽器運作
        driver = webdriver.Chrome(options=chrome_options)
        
        driver.get(url)      
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div')))

        time.sleep(random.uniform(5, 10))
        content = driver.page_source
        driver.quit()
        return content
    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None
    finally:
        gc.collect()

def search_products(query, current_page=1, size=60, max_page=10):
    items = []
    es = ensure_es_client_initialized()
    index_name = "products"
    base_url = "https://www.google.com"
    ua = UserAgent()
    user_agent = ua.random
    try:
        ## 執行爬蟲前，先將原先在Elastic database 的資料移除
        es.delete_by_query(index=index_name, body={
            "query": {
                "match_phrase": {
                    "query": query
                }
            }
        })

        query_with_baby = f"{query} 嬰兒"
        for page in range(current_page, max_page + 1):
            print(page)
            search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query_with_baby}&start={(page - 1) * size}&tbs=vw:g"
            headers = {
                'User-Agent': user_agent,
                'Referer': base_url
            }
            print(search_url)

            content = fetch_content(search_url, headers)
            if content is None:
                continue

            soup = BeautifulSoup(content, 'html.parser')
            time.sleep(random.uniform(5, 10))
            new_items = []
            for item in soup.find_all('h3', class_='tAxDx'):
                title = item.get_text()
                link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'
                price = 'N/A'
                price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
                if price_tag:
                    price = price_tag.get_text()
                seller = 'N/A'
                seller_tag = item.find_next('div', class_='aULzUe IuHnof')
                if seller_tag:
                    seller = seller_tag.get_text()
                image_url = 'N/A'
                arOc1c_div = item.find_previous('div', class_='ArOc1c')
                if arOc1c_div:
                    image_tag = arOc1c_div.find('img')
                    if image_tag and 'src' in image_tag.attrs:
                        image_url = image_tag['src']
                matching_rate = calculate_matching_rate(query, title)
                if matching_rate >0:
                    new_items.append({
                        "query": query,
                        "title": title,
                        "link": base_url + link,
                        "price": price,
                        "seller": seller,
                        "image": image_url,
                        "timestamp": datetime.now()
                    })
            if new_items:
                items.extend(new_items[:size])
            else:
                break

            for item in items:
                try:
                    es.index(index=index_name, id=item['title'], body=item)
                except Exception as e:
                    print(f"Error indexing to Elasticsearch: {e}")

    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None
    
    return items

# 單程序
# queries0_3 = ["奶粉", "溫奶器", "奶瓶消毒鍋", "安撫奶嘴", "監視器", "汽車安全座椅", "床", "屁屁膏"]
# queries4_6 = ["防脹氣奶瓶", "益生菌", "寶乖亞", "固齒器", "吸鼻器", "衣服", "背帶", "洗髮沐浴"]
# queries7_9 = ["副食品", "餐椅", "玩具", "安全護欄", "口水巾"]
# queries10_12 = ["學步鞋子", "益智積木", "馬桶"]
# queries_symptom = ["黃疸", "腸絞痛", "皮膚炎", "白噪音", "護膚膏", "乳液", "濕紙巾"]
queries = ["奶粉"]
def main():
    start_time = datetime.now()
    print(f"開始執行時間: {start_time}")
    
    for query in queries:
        attempts = 0
        max_attempts = 5
        results = []

        while attempts < max_attempts:
            results = search_products(query)
            if len(results) > 0:
                break
            attempts += 1
            print(f"Query '{query}' attempt {attempts} failed, retrying...")
            time.sleep(random.uniform(10, 20))  # 重試前等待一段時間

        print(f"Query '{query}' count: ", len(results))
        time.sleep(random.uniform(5, 10))

    end_time = datetime.now()
    print(f"結束時間: {end_time}")
    print(f"總執行時間: {end_time - start_time}")

if __name__ == "__main__":
    main()