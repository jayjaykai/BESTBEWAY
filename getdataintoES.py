from datetime import datetime
import re
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv
from pyppeteer import launch
import random
import time

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
    es.indices.delete(index=index_name, ignore=[400, 404])
    print("Testing and deleting data at first!")
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
        if len(item) >= 3:
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
            ],
            ignoreHTTPSErrors=True
        )
        page = await browser.newPage()
        await page.setUserAgent(headers['User-Agent'])
        
        # 模擬人為操作
        await page.evaluateOnNewDocument('''() => {
            Object.defineProperty(navigator, 'webdriver', {
              get: () => false,
            });
        }''')
        
        await page.goto(url, {'waitUntil': 'networkidle2'})
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

    for page in range(current_page, max_page + 1):
        print(page)
        search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}&start={(page - 1) * size}&tbs=vw:g"
        headers = random.choice(headers_list)
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
        time.sleep(random.uniform(5, 10))

    for item in items:
        try:
            es.index(index=index_name, id=item['title'], body=item)
        except Exception as e:
            print(f"Error indexing to Elasticsearch: {e}")

    return items

import asyncio

queries = ["嬰兒益生菌", "嬰兒腸絞痛", "嬰兒推車", "奶瓶消毒鍋", "防脹氣奶瓶", "固齒器", "兒童安全座椅", "嬰兒床", "吸鼻器", "安撫奶嘴", "嬰兒監視器"]
# queries = ["嬰兒益生菌"]

async def main():
    for query in queries:
        results = await search_products(query)
        print(f"Query '{query}' count: ", len(results))

asyncio.run(main())

# from datetime import datetime
# import re
# from bs4 import BeautifulSoup
# from elasticsearch import Elasticsearch, exceptions
# import os
# from dotenv import load_dotenv
# from pyppeteer import launch
# import random
# import time

# load_dotenv()
# # 初始化 Elasticsearch 客户端
# try:
#     es = Elasticsearch(
#         ["http://localhost:9200/"],
#         basic_auth=(os.getenv("ES_USER"), os.getenv("ES_PASSWORD"))
#     )
#     # 連線到 Elasticsearch server
#     if not es.ping():
#         raise exceptions.ConnectionError("Elasticsearch server is not reachable")
# except exceptions.ConnectionError as e:
#     print(f"Error connecting to Elasticsearch: {e}")
# except Exception as e:
#     print(f"Unexpected error: {e}")

# index_name = "products"
# try:
#     # 測試删除索引
#     es.indices.delete(index=index_name, ignore=[400, 404])
#     print("Testing and deleting data at first!")
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

# class Generator:
#     @staticmethod
#     def striphtml(data):
#         p = re.compile(r'<.*?>')
#         return p.sub('', data)

#     @staticmethod
#     def removeDuplicates(List):
#         return list(set(List))

#     @staticmethod
#     def split2Words(str):
#         newList = []
#         for i in range(len(str) - 1):
#             newList.append(str[i:i + 2])
#         return newList

#     @staticmethod
#     def split3Words(str):
#         subList = []
#         for i in range(len(str) - 2):
#             subList.append(str[i:i + 3])
#         return subList

#     @staticmethod
#     def splitString(str):
#         str = Generator.striphtml(str)

#         ChiList = re.sub(u"([^\u4e00-\u9fa5])", " ", str).split(" ")
#         ChiList = Generator.removeDuplicates(ChiList)
#         ChiList = list(filter(None, ChiList))
#         newList = []
#         for item in ChiList:
#             if len(item) > 4:
#                 newList = newList + Generator.split2Words(item)
#                 newList = newList + Generator.split3Words(item)
#         newList = Generator.removeDuplicates(newList)
#         ChiList = ChiList + newList
#         ChiStr = ' '.join(ChiList)
#         return ChiStr.split()

# def split_basic_words(str):
#     ChiList = re.sub(u"([^\u4e00-\u9fa5])", " ", str).split(" ")
#     ChiList = Generator.removeDuplicates(ChiList)
#     ChiList = list(filter(None, ChiList))
#     # print("ChiList: ", ChiList)
#     newList = []
#     for item in ChiList:
#         if len(item) >= 3:
#             newList = newList + Generator.split3Words(item)
#     # print("newList", newList)        
#     newList = Generator.removeDuplicates(newList)
#     ChiList = ChiList + newList
#     return ChiList

# def calculate_matching_rate(query, title):
#     query_words = split_basic_words(query)
#     title_words = Generator.splitString(title)

#     query_set = set(query_words)
#     title_set = set(title_words)

#     matching_count = sum(1 for word in query_set if word in title_set)

#     matching_rate = matching_count / len(query_set) if len(query_set) > 0 else 0
#     # print("matching_rate: ", matching_rate)
#     return matching_rate

# async def fetch_content(url, headers, proxy):
#     browser = await launch(
#         headless=True, 
#         executablePath=os.getenv("PYPPETEER_EXECUTABLE_PATH"),
#         args=[
#             '--no-sandbox', 
#             '--disable-setuid-sandbox', 
#             '--disable-dev-shm-usage', 
#             '--window-position=-10000,-10000',
#             '--window-size=1,1',
#             f'--proxy-server={proxy}'
#         ],
#         ignoreHTTPSErrors=True
#     )
#     page = await browser.newPage()
#     await page.setUserAgent(headers['User-Agent'])
#     await page.goto(url, {'waitUntil': 'networkidle2'})
#     content = await page.content()
#     await browser.close()
#     return content

# async def search_products(query, current_page=1, size=60, max_page=15):
#     items = []
#     print(query)
#     proxies = ["http://proxy1.com", "http://proxy2.com", "http://proxy3.com"]
#     base_url = "https://www.google.com"
#     headers = {
#         'User-Agent': random.choice([
#             'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#             'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
#             'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
#         ])
#     }

#     for page in range(current_page, max_page + 1):
#         print(page)
#         search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}&start={(page - 1) * size}&tbs=vw:g"
#         proxy = random.choice(proxies)
#         print(search_url)

#         try:
#             content = await fetch_content(search_url, headers, proxy)
#         except Exception as e:
#             print(f"Error during HTTP request: {e}")
#             raise
#         print("content: ", content)
#         soup = BeautifulSoup(content, 'html.parser')
#         print("After BeautifulSoup, soup: ", soup)
#         new_items = []
#         for item in soup.find_all('h3', class_='tAxDx'):
#             title = item.get_text()
#             link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'
#             print("title:", title)
#             price = 'N/A'
#             price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
#             if price_tag:
#                 price = price_tag.get_text()

#             seller = 'N/A'
#             seller_tag = item.find_next('div', class_='aULzUe IuHnof')
#             if seller_tag:
#                 seller = seller_tag.get_text()

#             image_url = 'N/A'
#             arOc1c_div = item.find_previous('div', class_='ArOc1c')
#             if arOc1c_div:
#                 image_tag = arOc1c_div.find('img')
#                 if image_tag and 'src' in image_tag.attrs:
#                     image_url = image_tag['src']


#             matching_rate = calculate_matching_rate(query, title)
#             if matching_rate >0:
#                 new_items.append({
#                     "query": query,
#                     "title": title,
#                     "link": base_url + link,
#                     "price": price,
#                     "seller": seller,
#                     "image": image_url,
#                     "timestamp": datetime.now()
#                 })

#         if new_items:
#             items.extend(new_items[:size])
#         else:
#             break

#         time.sleep(random.uniform(1, 3))
#     # 將資料儲存到 Elasticsearch
#     print("items.len", len(items))
#     for item in items:
#         try:
#             es.index(index=index_name, id=item['title'], body=item)
#         except Exception as e:
#             print(f"Error indexing to Elasticsearch: {e}")

#     return items

# # Example usage
# import asyncio

# # queries = ["嬰兒益生菌", "嬰兒腸絞痛", "嬰兒推車", "奶瓶消毒鍋", "防脹氣奶瓶", "固齒器", "兒童安全座椅", "嬰兒床", "吸鼻器", "安撫奶嘴", "嬰兒監視器"]
# queries = ["嬰兒益生菌"]
# async def main():
#     for query in queries:
#         results = await search_products(query)
#         print(f"Query '{query}' count: ", len(results))

# asyncio.run(main())