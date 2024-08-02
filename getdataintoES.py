from datetime import datetime
import re
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv
from pyppeteer import launch
import random
import time
import concurrent.futures
import asyncio

load_dotenv()

# 初始化 Elasticsearch 客户端
try:
    es = Elasticsearch(
        ["http://localhost:9200/"],
        basic_auth=(os.getenv("ES_USER"), os.getenv("ES_PASSWORD"))
    )
    if not es.ping():
        raise exceptions.ConnectionError("Elasticsearch server is not reachable")
except exceptions.ConnectionError as e:
    print(f"Error connecting to Elasticsearch: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

index_name = "products"
try:
    # 拿掉一開始把Elastic database 全部的資料刪除，改在爬取資料前刪除該query的資料
    # es.indices.delete(index=index_name, ignore=[400, 404])
    # print("Testing and deleting data at first!")
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body={
            "mappings": {
                "properties": {
                    "query": {"type": "text"},
                    "title": {"type": "text"},
                    "link": {"type": "text"},
                    "price": {"type": "text"},
                    "seller": {"type": "text"},
                    "image": {"type": "text"},
                    "timestamp": {"type": "date"}
                }
            }
        })
except exceptions.ConnectionError as e:
    print(f"Error connecting to Elasticsearch: {e}")
except exceptions.RequestError as e:
    print(f"Error creating index: {e}")

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
            newList = newList + Generator.split3Words(item)
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

async def fetch_content(url, headers):
    try:
        browser = await launch(
            headless=True, 
            executablePath=os.getenv("PYPPETEER_EXECUTABLE_PATH"),
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage', 
                '--window-position=-10000,-10000',
                '--window-size=1,1'
                #  f'--proxy-server={proxy}'
            ],
            ignoreHTTPSErrors=True
        )
        page = await browser.newPage()
        await page.setUserAgent(headers['User-Agent'])
        
        # 模擬人為操作
        await page.evaluateOnNewDocument('''() => {
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
        }''')
        
        await page.goto(url, {'waitUntil': 'networkidle2'})
        await asyncio.sleep(random.randint(1, 5))
        content = await page.content()
        await browser.close()
        return content
    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None

async def search_products(query, current_page=1, size=60, max_page=15):
    items = []
    base_url = "https://www.google.com"
    headers_list = [
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0'
        }
    ]
    try:
        # 執行爬蟲前，先將原先在Elastic database 的資料移除
        es.delete_by_query(index=index_name, body={
            "query": {
                "match_phrase": {
                    "query": query
                }
            }
        })

        for page in range(current_page, max_page + 1):
            print(page)
            search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}&start={(page - 1) * size}&tbs=vw:g"
            headers = random.choice(headers_list)
            # proxy = random.choice(proxies)
            print(search_url)

            content = await fetch_content(search_url, headers)
            if content is None:
                continue

            soup = BeautifulSoup(content, 'html.parser')
            # print("After BeautifulSoup, soup: ", soup)
            new_items = []
            for item in soup.find_all('h3', class_='tAxDx'):
                title = item.get_text()
                link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'
                # print("title:", title)
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
                if matching_rate >= 0.2:
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
            time.sleep(random.uniform(10, 15))
    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None
    
    for item in items:
        try:
            es.index(index=index_name, id=item['title'], body=item)
        except Exception as e:
            print(f"Error indexing to Elasticsearch: {e}")

    return items

# 單程序
# queries = ["溫奶器", "安撫奶嘴", "嬰兒監視器", "兒童安全座椅", "嬰兒床", "嬰兒益生菌", "寶乖亞", "固齒器", "吸鼻器", "奶瓶消毒鍋", "防脹氣奶瓶"]
queries = ["固齒器", "吸鼻器"]
async def main():
    start_time = datetime.now()
    print(f"開始執行時間: {start_time}")
    for query in queries:
        results = await search_products(query)
        print(f"Query '{query}' count: ", len(results))

    end_time = datetime.now()
    print(f"結束時間: {end_time}")
    print(f"總執行時間: {end_time - start_time}")

asyncio.run(main())

# # 多執行續(有bug)
# async def handle_queries(queries):
#     loop = asyncio.get_event_loop()
#     with concurrent.futures.ThreadPoolExecutor() as pool:
#         futures = [loop.run_in_executor(pool, asyncio.run, search_products(query)) for query in queries]
#         results = await asyncio.gather(*futures)
#         return results

# async def main():
#     queries0_3 = ["嬰兒益生菌", "嬰兒腸絞痛", "嬰兒推車", "奶瓶消毒鍋", "防脹氣奶瓶"]
#     queries4_6 = ["固齒器", "兒童安全座椅", "嬰兒床", "吸鼻器", "安撫奶嘴", "嬰兒監視器"]

#     results_0_3 = await handle_queries(queries0_3)
#     results_4_6 = await handle_queries(queries4_6)

#     print("Results for queries0_3: ", results_0_3)
#     print("Results for queries4_6: ", results_4_6)

# asyncio.run(main())