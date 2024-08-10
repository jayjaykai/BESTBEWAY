from model.elasticsearch_client import get_elasticsearch_client

# 初始化 Elasticsearch 客戶端
es = get_elasticsearch_client("Local")

# 要插入的產品資料
product_data = {
    "query": "奶粉",
    "title": "奶粉",
    "link": "https://example.com/milk-powder",
    "price": "500",
    "seller": "奶粉賣家",
    "image": "https://example.com/image.jpg",
    "timestamp": "2024-08-10T00:00:00Z"
}

def insert_product_to_es(product_data):
    try:
        # 插入資料到 'products' 索引
        es.index(index="products", body=product_data)
        print("Document inserted successfully.")
    except Exception as e:
        print(f"Error inserting document: {e}")

# 執行插入操作
insert_product_to_es(product_data)
