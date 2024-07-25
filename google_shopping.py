from elasticsearch import Elasticsearch, exceptions
import httpx
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

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
                    "query": { "type": "text" },
                    "title": { "type": "text" },
                    "link": { "type": "text" },
                    "price": { "type": "text" },
                    "seller": { "type": "text" }
                }
            }
        })
except exceptions.ConnectionError as e:
    print(f"Error connecting to Elasticsearch: {e}")
except exceptions.RequestError as e:
    print(f"Error creating index: {e}")

async def search_products(query, from_=0, size=50, current_page=0, max_pages=5):
    if current_page >= max_pages:
        return []
    items = []
    try:
        # 检查 Elasticsearch 中是否已经有结果
        es_response = es.search(index=index_name, body={
            "query": {"match": {"query": query}},
            "size": size,
            "from": from_
        })
        hits = es_response['hits']['hits']
        items.extend([hit["_source"] for hit in hits])
        # print("len(hits):", len(hits))
        # print("size:", size)
        if items:
            # print("Use ES!")
            return items
    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")

    print(f"Start crawling data!")
    print("query: ",query)
    print("current_page: ",current_page)
    print("size: ",size)
    # 如果没有足够的结果，进行爬蟲
    base_url = "https://www.google.com"
    search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}&start={current_page * size}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("current_page:", current_page)
    print("max_pages:", max_pages)
    print("search_url: ",search_url)
    while search_url and current_page < max_pages:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, headers=headers)
                response.raise_for_status()
        except Exception as e:
            print(f"Error during HTTP request: {e}")
            raise

        soup = BeautifulSoup(response.text, 'html.parser')

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

            new_items.append({
                "query": query,
                "title": title,
                "link": base_url + link,
                "price": price,
                "seller": seller
            })

        # print("new_items", new_items)
        if len(new_items) > 0:
            items.extend(new_items[:size])
            next_page_tag = soup.select_one('a#pnnext')
            search_url = base_url + next_page_tag['href'] if next_page_tag else None
            current_page += 1
            break  # 仅获取一页的数据就退出循环
        else:
            break  # 如果没有更多数据了，则退出循环

    # 将新结果存储到 Elasticsearch
    for item in items:
        try:
            es.index(index=index_name, body=item)
        except Exception as e:
            print(f"Error indexing to Elasticsearch: {e}")

    return items
# async def search_products(query, from_=0, size=10, max_pages=5):
#     items = []
#     es_available = True

#     try:
#         # 检查 Elasticsearch 中是否已经有结果
#         while True:
#             es_response = es.search(index=index_name, body={
#                 "query": {"match": {"query": query}},
#                 "size": size,
#                 "from": from_
#             })
#             hits = es_response['hits']['hits']
#             if not hits:
#                 break
#             items.extend([hit["_source"] for hit in hits])
#             from_ += size
#         if items:
#             return items
#     except exceptions.ConnectionError as e:
#         print(f"Error searching Elasticsearch: {e}")
#         es_available = False
#     except Exception as e:
#         print(f"Unexpected error searching Elasticsearch: {e}")
#         es_available = False

#     # 如果没有结果，进行爬蟲
#     base_url = "https://www.google.com"
#     search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}"
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }

#     current_page = from_ // size
#     while search_url and current_page < max_pages:
#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.get(search_url, headers=headers)
#                 response.raise_for_status()
#         except Exception as e:
#             print(f"Error during HTTP request: {e}")
#             raise

#         soup = BeautifulSoup(response.text, 'html.parser')

#         for item in soup.find_all('h3', class_='tAxDx'):
#             title = item.get_text()
#             link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'
            
#             price = 'N/A'
#             price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
#             if price_tag:
#                 price = price_tag.get_text()
            
#             seller = 'N/A'
#             seller_tag = item.find_next('div', class_='aULzUe IuHnof')
#             if seller_tag:
#                 seller = seller_tag.get_text()

#             items.append({
#                 "query": query,
#                 "title": title,
#                 "link": base_url + link,
#                 "price": price,
#                 "seller": seller
#             })

#         next_page_tag = soup.select_one('a#pnnext')
#         search_url = base_url + next_page_tag['href'] if next_page_tag else None
#         current_page += 1

#     # 将新结果存储到 Elasticsearch
#     if es_available:
#         for item in items:
#             try:
#                 es.index(index=index_name, body=item)
#             except Exception as e:
#                 print(f"Error indexing to Elasticsearch: {e}")

#     return items

# #單純使用爬蟲抓資料，每搜尋一次都會抓一次 
# import re
# import httpx
# from bs4 import BeautifulSoup


# async def search_products(query, max_pages=5):
#     base_url = "https://www.google.com"
#     search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&q={query}"
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }

#     items = []
#     current_page = 0
#     while search_url and current_page < max_pages:
#         async with httpx.AsyncClient() as client:
#             response = await client.get(search_url, headers=headers)
#             response.raise_for_status()

#         soup = BeautifulSoup(response.text, 'html.parser')

#         for item in soup.find_all('h3', class_='tAxDx'):
#             title = item.get_text()  # 提取标题文本
#             link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'  # 提取链接

#             price = 'N/A'
#             price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
#             if price_tag:
#                 price = price_tag.get_text()

#             seller = 'N/A'
#             seller_tag = item.find_next('div', class_='aULzUe IuHnof')
#             if seller_tag:
#                 seller = seller_tag.get_text()    

#             items.append({
#                 "title": title,
#                 "link": base_url + link,
#                 "price": price,
#                 "seller": seller
#             })

#         # 查找分页链接
#         next_page_tag = soup.select_one('a#pnnext')
#         search_url = base_url + next_page_tag['href'] if next_page_tag else None
#         current_page += 1

#     # 打印提取到的商品信息
#     # print(items)
#     return items

# # async def search_products(query):
# #     url = f"https://www.google.com/search?tbm=shop&hl=zh-TW&q={query}"
# #     headers = {
# #         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
# #     }

# #     async with httpx.AsyncClient() as client:
# #         response = await client.get(url, headers=headers)
# #         response.raise_for_status()

# #     soup = BeautifulSoup(response.text, 'html.parser')
# #     # html_content = soup.prettify()
# #     # print(html_content)
# #     items = []

# #    # 查找所有包含商品信息的容器
# #     for item in soup.find_all('h3', class_='tAxDx'):
# #         title = item.get_text()  # 提取标题文本
# #         link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'  # 提取链接

# #         price = 'N/A'
# #         price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
# #         if price_tag:
# #             price = price_tag.get_text()

# #         seller = 'N/A'
# #         seller_tag = item.find_next('div', class_='aULzUe IuHnof')
# #         if seller_tag:
# #             seller = seller_tag.get_text()    

# #         items.append({
# #             "title": title,
# #             "link": "https://www.google.com"+link,
# #             "price": price,
# #             "seller": seller
# #         })

# #     # 打印提取到的商品信息
# #     print(items)
# #     return items