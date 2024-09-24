from datetime import datetime, time
import random
import re
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gc
from model.elasticsearch_client import get_elasticsearch_client
# from pyppeteer import launch

load_dotenv()
# 初始化 Elasticsearch 客户端
# Elastic Search
def ensure_es_client_initialized():
    es = get_elasticsearch_client()
    if es is None:
        raise Exception("Failed to initialize Elasticsearch client.")
    return es
# es_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
# es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
# es_username = os.getenv("ELASTICSEARCH_USERNAME")
# es_password = os.getenv("ELASTICSEARCH_PASSWORD")

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
        
        EngList = re.sub(u"([^\u0030-\u007a])", " ", str).split(" ")
        EngList = Generator.removeDuplicates(EngList)
        EngList = list(filter(None, EngList))
        EngStr = ' '.join(EngList)

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

        words = {
            "English": EngStr,
            "Chinese": ChiStr
        }
        return words

def split_basic_words(str):
    ChiList = re.sub(u"([^\u4e00-\u9fa5])", " ", str).split(" ")
    ChiList = Generator.removeDuplicates(ChiList)
    ChiList = list(filter(None, ChiList))
    newList = []
    for item in ChiList:
        if len(item) >= 3:
            newList = newList + Generator.split3Words(item)
       
    newList = Generator.removeDuplicates(newList)
    ChiList = ChiList + newList
    return ChiList

def calculate_matching_rate(query, title):
    query_words = split_basic_words(query)
    # query_words = Generator.splitString(query)
    title_words = Generator.splitString(title)
    
    query_set = set(query_words)
    # query_set = set(query_words["Chinese"].split())
    title_set = set(title_words["Chinese"].split())
    
    matching_count = sum(1 for word in query_set if word in title_set)
    
    matching_rate = matching_count / len(query_set) if len(query_set) > 0 else 0
    
    # print("title: ", title)
    # print("query_set: ", query_set)
    # print("title_set: ", title_set)
    # print("matching_rate: ", matching_rate)
    
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

async def search_es_products(query, from_=0, size=50):
    items = []
    try:
        es = ensure_es_client_initialized()
        index_name = "products"
        print(query)
        print(f"Querying Elasticsearch with from_={from_}")
        # 獲取符合查詢條件的總資料數量
        count_response = es.count(index=index_name, body={
            # "query": {
            #     "multi_match": {
            #         "query": query,
            #         "fields": ["title", "query"],
            #         "type": "phrase"
            #     }
            # }
            "query": {
                "match_phrase": {
                    "title": query
                }
            }
        })
        total_hits = count_response['count']
        print(f"Total hits: {total_hits}")

        # 如果 from_ 大於總數量，直接返回空結果
        if from_ > total_hits:
            # items.append("NO_ES")
            return items, total_hits 
        
        es_response = es.search(index=index_name, body={
            "query": {
                "function_score": {
                    "query": {
                        "match_phrase": {
                            "title": query
                        }
                    },
                    "script_score": {
                        "script": {
                            "source": """
                                // 使用 doc['title'] 來獲取每個文檔的 title 字段
                                String title = doc['title'].value;
                                double score = 0;

                                // 計算 title 的前 N 個字母的相似度
                                int N = 15; 
                                if (title.length() > N) {
                                    title = title.substring(0, N);
                                }

                                // 計算每個字符的Unicode值總和作為相似度分數
                                for (int i = 0; i < title.length(); i++) {
                                    score += title.charAt(i);
                                }

                                return score;
                            """
                        }
                    },
                    "boost_mode": "replace"
                }
            },
            "size": size,
            "from": from_
        })

        if es_response['hits']['hits']:
            hits = es_response['hits']['hits']
            for hit in hits:
                items.append(hit["_source"])

    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
    return items, total_hits

## 先把可以讓user進一步再去搜尋的爬蟲抓資料拿掉
# async def fetch_google_products(query, size=50, current_page=0, max_pages=5):
#     print("Start fetch_google_products")
#     items = []
#     base_url = "https://www.google.com"
#     headers_list = [
#         {
#             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
#         },
#         {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
#         },
#         {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0'
#         }
#     ]

#     print("current_page:", current_page)
#     print("max_pages:", max_pages)
#     if current_page>=max_pages:
#         return []

#     search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}&start={current_page * size}&tbs=vw:g"
#     headers = random.choice(headers_list)
#     print("search_url: ", search_url)

#     try:
#         content = await fetch_content(search_url, headers)
#     except Exception as e:
#         print(f"Error during HTTP request: {e}")
#         raise

#     soup = BeautifulSoup(content, 'html.parser')
#     # print("After BeautifulSoup, soup: ", soup)
#     new_items = []
#     for item in soup.find_all('h3', class_='tAxDx'):
#         title = item.get_text()
#         link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'

#         price = 'N/A'
#         price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
#         if price_tag:
#             price = price_tag.get_text()

#         seller = 'N/A'
#         seller_tag = item.find_next('div', class_='aULzUe IuHnof')
#         if seller_tag:
#             seller = seller_tag.get_text()

#         image_url = 'N/A'
#         arOc1c_div = item.find_previous('div', class_='ArOc1c')
#         if arOc1c_div:
#             image_tag = arOc1c_div.find('img')
#             if image_tag and 'src' in image_tag.attrs:
#                 image_url = image_tag['src']

#         matching_rate = calculate_matching_rate(query, title)
#         if matching_rate >0:
#             # print("query: ",query)
#             new_items.append({
#                 "query": query,
#                 "title": title,
#                 "link": base_url + link,
#                 "price": price,
#                 "seller": seller,
#                 "image": image_url,
#                 "timestamp": datetime.now().isoformat()
#             })
    
#     if new_items:
#         items.extend(new_items[:size])

#     # 將資料儲存到 Elasticsearch
#     print("items.len", len(items))
#     for item in items:
#         try:
#             es.index(index=index_name, id=item['title'], body=item)
#         except Exception as e:
#             print(f"Error indexing to Elasticsearch: {e}")

#     return items
   
async def search_products(query, from_=0, size=50, current_page=0, max_pages=5):
    print("from_ :", from_)
    items, total_items_count = await search_es_products(query, from_, size)
    print("ElasticSearch items length: ", total_items_count)
    ## 先把可以讓user進一步再去搜尋的爬蟲抓資料拿掉
    # if "NO_ES" in items:  # 特殊字符串判断
    #     print("Triggering fetch_google_products due to 'NO_ES' condition")
    #     items = await fetch_google_products(query, size, current_page, max_pages)
    # elif total_items_count < from_:  # 如果 Elasticsearch 沒有數據，則從 Google Shopping 爬取
    #     items = await fetch_google_products(query, size, current_page, max_pages)
    
    return {"items": items, "total_items_count": total_items_count}
    # return JSONResponse(content={"items": items, "total_items_count": total_items_count})