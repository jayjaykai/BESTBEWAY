from fastapi import FastAPI, HTTPException
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

# 示例產品數據
products = [
    {"name": "益生菌", "description": "這是一種可以幫助腸絞痛的益生菌"},
    {"name": "防脹氣奶瓶", "description": "這是一種適合有腸絞痛寶寶使用的防脹氣奶瓶"},
    {"name": "嬰兒肚痛藥", "description": "這是一種可以緩解嬰兒肚痛的藥物"},
    {"name": "舒緩滴劑", "description": "這是一種可以幫助嬰兒舒緩腸絞痛的滴劑"},
    {"name": "抗過敏奶粉", "description": "這是一種適合對奶蛋白過敏寶寶的抗過敏奶粉"},
    {"name": "安撫奶嘴", "description": "這是一種可以幫助寶寶舒緩情緒的安撫奶嘴"},
    {"name": "防吐奶枕", "description": "這是一種可以幫助寶寶防止吐奶的枕頭"},
    {"name": "便秘寶寶益生菌", "description": "這是一種專門針對便秘寶寶的益生菌"},
    {"name": "新生兒舒緩膏", "description": "這是一種可以幫助新生兒舒緩腸絞痛的膏狀產品"},
    {"name": "防脹氣奶嘴", "description": "這是一種適合有腸絞痛寶寶使用的防脹氣奶嘴"}
]

# 將產品描述進行分詞
for product in products:
    product["tokenized_description"] = " ".join(jieba.cut(product["description"]))

# 使用TF-IDF向量化
vectorizer = TfidfVectorizer()
all_descriptions = [product["tokenized_description"] for product in products]
tfidf_matrix = vectorizer.fit_transform(all_descriptions)

@app.get("/match_products/")
def match_products(description: str):
    try:
        # 將新描述進行分詞
        tokenized_description = " ".join(jieba.cut(description))
        
        # 將新描述向量化並計算相似度
        new_tfidf_vector = vectorizer.transform([tokenized_description])
        similarity_matrix = cosine_similarity(new_tfidf_vector, tfidf_matrix)
        
        # 找到所有相似的產品
        similar_products = []
        for idx, similarity in enumerate(similarity_matrix[0]):
            if similarity > 0:  # 這裡可以調整閾值
                similar_products.append(products[idx])
        
        return {"similar_products": similar_products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
