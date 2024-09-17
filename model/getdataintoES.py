from datetime import datetime
import re
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv, set_key
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
from model.cache import Cache

load_dotenv()

user_agents = [
    'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
]

def ensure_es_client_initialized():
    es = get_elasticsearch_client("Local")
    if es is None:
        raise Exception("Failed to initialize Elasticsearch client.")
    return es

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
        chrome_options.add_argument("--lang=zh-TW")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--window-size=3840,2160")
        chrome_options.add_argument(f"user-agent={headers['User-Agent']}")
        chrome_options.add_argument(f"referer={headers['Referer']}")

        # ChromeDriver 路径
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        print("Using ChromeDriver from:", chromedriver_path)

        # 建立 Driver 物件實體，用程式操作瀏覽器運作
        driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
        # hide WebDriver
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                })
            """
        })
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div')))
        # # 滾動頁面加載更多資料
        # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(5, 10))
        content = driver.page_source
        # print("content: ", content)
        # 將檔案儲存到 /tmp/ 下
        # file_path = "/tmp/original_html.html"
        # with open(file_path, 'w', encoding='utf-8') as file:
        #     file.write(content)
        # print(f"original_html.html content saved to {file_path}")

        driver.quit()
        return content
    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None
    finally:
        gc.collect()

def search_products(query, current_page=1, size=60, max_page=8):
    items = []
    es = ensure_es_client_initialized()
    index_name = "products"
    base_url = "https://www.google.com"
    # ua = UserAgent()

    try:
        # Elastic database 資料移除
        es.delete_by_query(index=index_name, body={
            "query": {
                "match_phrase": {
                    "query": query
                }
            }
        })

        query_with_baby = f"{query} 嬰兒"
        for page in range(current_page, max_page + 1):
            retry_count = 0
            max_retries = 8

            while retry_count <= max_retries:
                print(page)
                # user_agent = ua.random
                user_agent = random.choice(user_agents)
                search_url = f"{base_url}/search?tbm=shop&hl=zh-TW&lr=lang_zh-TW&cr=countryTW&gl=tw&q={query_with_baby}&start={(page - 1) * size}&tbs=vw:g"
                headers = {
                    'User-Agent': user_agent,
                    'Referer': base_url
                }
                print(search_url)

                content = fetch_content(search_url, headers)
                if content is None:
                    retry_count += 1
                    continue

                soup = BeautifulSoup(content, 'html.parser')

                # 將檔案儲存到 /tmp/ 下
                # pretty_html = soup.prettify()
                # file_path = "/tmp/pretty_html.html"

                # with open(file_path, 'a', encoding='utf-8') as file:
                #     file.write(pretty_html)
                #     file.write("\n\n")
                # print(f"HTML content saved to {file_path}")

                time.sleep(random.uniform(5, 10))
                new_items = []

                # 初始化 title 和 link
                # title = 'No title'
                # link = 'No link'
                # price = 'N/A'
                # seller = 'N/A'
                # image_url = 'N/A'

                if soup.find_all('h3', class_='tAxDx'):
                    for item in soup.find_all('h3', class_='tAxDx'):
                        title = item.get_text() if item.get_text() else 'No title'
                        link = item.find_parent('a')['href'] if item.find_parent('a') else 'No link'

                        price_tag = item.find_next('span', class_='a8Pemb OFFNJ')
                        if price_tag:
                            price = price_tag.get_text()

                        seller_tag = item.find_next('div', class_='aULzUe IuHnof')
                        if seller_tag:
                            seller = seller_tag.get_text()

                        arOc1c_div = item.find_previous('div', class_='ArOc1c')
                        if arOc1c_div:
                            image_tag = arOc1c_div.find('img')
                            if image_tag and 'src' in image_tag.attrs:
                                image_url = image_tag['src']

                        print("----------")
                        print(f"Title: {title}")
                        print(f"Link: {link}")
                        print(f"Price: {price}")
                        print(f"Seller: {seller}")
                        print(f"Image URL: {image_url}")
                        print("----------")

                        if title != 'No title' and link != 'No link':
                            matching_rate = calculate_matching_rate(query, title)
                            print(f"matching_rate: {matching_rate} query: {query} title: {title}")
                            if matching_rate > 0:
                                new_items.append({
                                    "query": query,
                                    "title": title,
                                    "link": base_url + link,
                                    "price": price,
                                    "seller": seller,
                                    "image": image_url,
                                    "timestamp": datetime.now()
                                })

                    items.extend(new_items[:size])
                    break
                
                elif soup.find_all('div', class_='xcR77'):
                    for item in soup.find_all('div', class_='xcR77'):
                        # print("HTML content of item:")
                        # print(item.prettify())

                        title_tag = item.find('div', class_='rgHvZc')
                        title = title_tag.get_text() if title_tag else 'No title'

                        link_tag = title_tag.find('a', href=True) if title_tag else None
                        link = link_tag['href'] if link_tag else 'No link'

                        price_tag = item.find('span', class_='HRLxBb')
                        price = price_tag.get_text() if price_tag else 'N/A'

                        seller_tag = item.find('div', class_='dD8iuc')
                        if seller_tag:
                            seller_text = seller_tag.get_text()
                            seller = seller_text.split('，商家：')[-1].strip() if '，商家：' in seller_text else seller_text.strip()
                        else:
                            seller = 'N/A'

                        image_tag = item.find('img')
                        image_url = image_tag['src'] if image_tag else 'N/A'
                        print("----------")
                        print(f"Title: {title}")
                        print(f"Link: {link}")
                        print(f"Price: {price}")
                        print(f"Seller: {seller}")
                        print(f"Image URL: {image_url}")
                        print("----------")

                        if title != 'No title' and link != 'No link':
                            matching_rate = calculate_matching_rate(query, title)
                            print(f"matching_rate: {matching_rate} query: {query} title: {title}")
                            if matching_rate > 0:
                                new_items.append({
                                    "query": query,
                                    "title": title,
                                    "link": base_url + link,
                                    "price": price,
                                    "seller": seller,
                                    "image": image_url,
                                    "timestamp": datetime.now()
                                })

                    items.extend(new_items[:size])
                    break

                else:
                    new_items.append("Wait Next Run")
                    print("No known structure found in the HTML content.")
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"Max retries reached for page {page}, moving to next page.")
                        break
                    else:
                        print(f"Retrying page {page} (Attempt {retry_count}/{max_retries})")
                        time.sleep(random.uniform(10, 20))
                        continue  # retry
                
            if not new_items:  # 如果當前頁面沒有任何匹配的商品，跳出for loop不再執行
                break

        for item in items:
            try:
                es.index(index=index_name, id=item['title'], body=item)
            except Exception as e:
                print(f"Error indexing to Elasticsearch: {e}")

    except Exception as e:
        print(f"Error during HTTP request: {e}")
        return None

    print("len(items): ", len(items))
    return items if items else None

def update_failed_queries(query):
    # 加載 .env 檔案
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

    failed_queries = os.getenv("QUERIES_GROUP_6", "")
    if failed_queries:
        failed_queries_list = failed_queries.split(',')
    else:
        failed_queries_list = []
    
    if query not in failed_queries_list:
        failed_queries_list.append(query)
        updated_failed_queries = ','.join(failed_queries_list)
        print("Current working directory:", os.getcwd())
        set_key(os.path.join(os.path.dirname(__file__), '../.env'), 'QUERIES_GROUP_6', updated_failed_queries)
        # set_key('../.env', 'QUERIES_GROUP_6', updated_failed_queries)
        
def main(queries):
    start_time = datetime.now()
    print(f"開始執行時間: {start_time}")
    # 如果 QUERIES_GROUP_6 是空值，不需要補槍
    if queries == [""] and os.getenv("QUERIES_GROUP_6") == "":
        print("QUERIES_GROUP_6 is empty, skipping execution.")
        return
    
    for query in queries:
        attempts = 0
        max_attempts = 3
        results = []

        while attempts <= max_attempts:
            results = search_products(query) or []
            if len(results) > 0:
                break
            attempts += 1
            print(f"Query '{query}' attempt {attempts} failed at time {datetime.now()}, retrying...")
            time.sleep(random.uniform(15, 30))  # 重試前等待一段時間

        print(f"Query '{query}' count: ", len(results))
        # 刪除 query 的所有 Redis 快取
        Cache.delete_all_cache_for_product_query(query)

        if len(results) == 0:
            update_failed_queries(query) # 爬蟲失敗紀錄到新的陣列去，下次再補槍
        time.sleep(random.uniform(5, 10))

    end_time = datetime.now()
    print(f"結束時間: {end_time}")
    print(f"總執行時間: {end_time - start_time}")

if __name__ == "__main__":
    main()
