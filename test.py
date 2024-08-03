from datetime import datetime
import re
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv
import random
import time
import asyncio
from fake_useragent import UserAgent
import undetected_chromedriver as uc

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

ua = UserAgent()

def fetch_content(url, driver):
    try:
        user_agent = ua.random
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
        driver.get(url)
        time.sleep(random.uniform(5, 10))  # 增加随机延迟
        content = driver.page_source
        return content
    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None

def search_products(query):
    items = []
    retries = 3
    for _ in range(retries):
        driver = uc.Chrome()
        search_url = f"https://www.google.com/search?tbm=shop&hl=zh-TW&q={query}"
        content = fetch_content(search_url, driver)
        driver.quit()
        if content:
            break
        time.sleep(random.uniform(10, 20))  # 在重试前增加随机延迟

    if content is None:
        return items

    soup = BeautifulSoup(content, 'html.parser')
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
        items.append({
            "query": query,
            "title": title,
            "link": "https://www.google.com" + link,
            "price": price,
            "seller": seller,
            "image": image_url,
            "timestamp": datetime.now()
        })
    return items

def main():
    queries = ["嬰兒監視器", "溫奶器"]
    start_time = datetime.now()
    print(f"開始執行時間: {start_time}")

    for query in queries:
        results = search_products(query)
        print(f"Query '{query}' count: ", len(results))
        for item in results:
            print(item)

    end_time = datetime.now()
    print(f"結束時間: {end_time}")
    print(f"總執行時間: {end_time - start_time}")

if __name__ == "__main__":
    main()