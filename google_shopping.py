from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv
from pyppeteer import launch

load_dotenv()
# 初始化 Elasticsearch 客户端
try:
    es = Elasticsearch(
        ["http://localhost:9200/"],
        basic_auth=(os.getenv("ES_USER"), os.getenv("ES_PASSWORD"))
    )
    # 尝试连接到 Elasticsearch，检查其是否可用
    if not es.ping():
        raise exceptions.ConnectionError("Elasticsearch server is not reachable")
except exceptions.ConnectionError as e:
    print(f"Error connecting to Elasticsearch: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

index_name = "products"
try:
    # 删除索引
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
                    "image": {"type": "text"}
                }
            }
        })
except exceptions.ConnectionError as e:
    print(f"Error connecting to Elasticsearch: {e}")
except exceptions.RequestError as e:
    print(f"Error creating index: {e}")

async def fetch_content(url, headers):
    browser = await launch(
        headless=True, 
        executablePath=os.getenv("PYPPETEER_EXECUTABLE_PATH"),
        args=['--no-sandbox', 
              '--disable-setuid-sandbox', 
              '--disable-dev-shm-usage', 
              '--window-position=0,0',
              '--window-size=1,1'
            ],
        ignoreHTTPSErrors=True
    )
    print(os.getenv("PYPPETEER_EXECUTABLE_PATH"))
    page = await browser.newPage()
    await page.setUserAgent(headers['User-Agent'])
    await page.goto(url, {'waitUntil': 'networkidle2'})
    content = await page.content()
    await browser.close()
    return content

async def search_products(query, from_=0, size=50, current_page=0, max_pages=5):
    if current_page >= max_pages:
        return []
    items = []
    try:
        # 確認 Elasticsearch 有資料
        es_response = es.search(index=index_name, body={
            "query": {"match": {"query": query}},
            "size": size,
            "from": from_
        })
        hits = es_response['hits']['hits']
        items.extend([hit["_source"] for hit in hits])
        if items:
            return items
    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")

    base_url = "https://www.google.com"
    search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}&start={current_page * size}&tbs=vw:g"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("current_page:", current_page)
    print("max_pages:", max_pages)
    print("search_url: ", search_url)

    while search_url and current_page < max_pages:
        try:
            content = await fetch_content(search_url, headers)
        except Exception as e:
            print(f"Error during HTTP request: {e}")
            raise

        soup = BeautifulSoup(content, 'html.parser')

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

            new_items.append({
                "query": query,
                "title": title,
                "link": base_url + link,
                "price": price,
                "seller": seller,
                "image": image_url
            })
        print(new_items[0])
        if len(new_items) > 0:
            items.extend(new_items[:size])
            next_page_tag = soup.select_one('a#pnnext')
            search_url = base_url + next_page_tag['href'] if next_page_tag else None
            current_page += 1
            break
        else:
            break

    # 將資料儲存到 Elasticsearch
    for item in items:
        try:
            es.index(index=index_name, body=item)
        except Exception as e:
            print(f"Error indexing to Elasticsearch: {e}")

    return items