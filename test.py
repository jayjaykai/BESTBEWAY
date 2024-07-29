# from fastapi import FastAPI, HTTPException
# import jieba
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity

# app = FastAPI()

# # 示例產品數據
# products = [
#     {"name": "益生菌", "description": "這是一種可以幫助腸絞痛的益生菌"},
#     {"name": "防脹氣奶瓶", "description": "這是一種適合有腸絞痛寶寶使用的防脹氣奶瓶"},
#     {"name": "嬰兒肚痛藥", "description": "這是一種可以緩解嬰兒肚痛的藥物"},
#     {"name": "舒緩滴劑", "description": "這是一種可以幫助嬰兒舒緩腸絞痛的滴劑"},
#     {"name": "抗過敏奶粉", "description": "這是一種適合對奶蛋白過敏寶寶的抗過敏奶粉"},
#     {"name": "安撫奶嘴", "description": "這是一種可以幫助寶寶舒緩情緒的安撫奶嘴"},
#     {"name": "防吐奶枕", "description": "這是一種可以幫助寶寶防止吐奶的枕頭"},
#     {"name": "便秘寶寶益生菌", "description": "這是一種專門針對便秘寶寶的益生菌"},
#     {"name": "新生兒舒緩膏", "description": "這是一種可以幫助新生兒舒緩腸絞痛的膏狀產品"},
#     {"name": "防脹氣奶嘴", "description": "這是一種適合有腸絞痛寶寶使用的防脹氣奶嘴"}
# ]

# # 將產品描述進行分詞
# for product in products:
#     product["tokenized_description"] = " ".join(jieba.cut(product["description"]))

# # 使用TF-IDF向量化
# vectorizer = TfidfVectorizer()
# all_descriptions = [product["tokenized_description"] for product in products]
# tfidf_matrix = vectorizer.fit_transform(all_descriptions)

# @app.get("/match_products/")
# def match_products(description: str):
#     try:
#         # 將新描述進行分詞
#         tokenized_description = " ".join(jieba.cut(description))
        
#         # 將新描述向量化並計算相似度
#         new_tfidf_vector = vectorizer.transform([tokenized_description])
#         similarity_matrix = cosine_similarity(new_tfidf_vector, tfidf_matrix)
        
#         # 找到所有相似的產品
#         similar_products = []
#         for idx, similarity in enumerate(similarity_matrix[0]):
#             if similarity > 0:  # 這裡可以調整閾值
#                 similar_products.append(products[idx])
        
#         return {"similar_products": similar_products}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))





import re

# 定義你的分類關鍵詞
categories = {
    "食品": ["奶粉", "米粉", "果泥", "蔬菜泥", "餅乾", "米餅", "果汁"],
    "護理用品": ["尿布", "濕紙巾", "洗髮水", "沐浴露", "潤膚乳", "爽身粉", "護臀膏", "指甲剪", "梳子", "刷子"],
    "喂養用品": ["奶瓶", "奶嘴", "吸奶器", "清潔刷", "消毒器", "保溫袋", "餐具", "圍兜"],
    "玩具": ["搖鈴", "咬牙器", "床玩具", "活動架", "益智玩具", "毛絨玩具", "音樂玩具"],
    "家居用品": ["床", "床墊", "護欄", "睡袋", "毯", "車", "安全座椅", "高腳椅", "搖椅", "揹帶"],
    "服裝": ["連身衣", "上衣", "褲子", "襪子", "帽子", "手套", "圍巾"],
    "健康用品": ["體溫計", "藥盒", "吸鼻器", "護耳套", "口腔清潔用品"],
    "出行用品": ["車", "揹帶", "包包", "防蚊罩", "防曬霜", "水壺"],
    "安全用品": ["安全門", "防撞條", "插座保護蓋", "安全鎖"]
}

# 分類函數
def classify_product(product_name):
    for category, keywords in categories.items():
        for keyword in keywords:
            if re.search(keyword, product_name, re.IGNORECASE):
                return category
    return "未分類"

# 測試數據
product_names = [
    "嬰兒奶粉1段",
    "嬰兒濕紙巾",
    "防脹氣奶瓶",
    "搖鈴玩具",
    "嬰兒床墊",
    "嬰兒連身衣",
    "嬰兒體溫計",
    "嬰兒車",
    "插座保護蓋",
    "寶乖亞"
]

# 分類產品
classified_products = {name: classify_product(name) for name in product_names}

# 打印結果
for product, category in classified_products.items():
    print(f"產品名稱: {product}, 分類: {category}")
