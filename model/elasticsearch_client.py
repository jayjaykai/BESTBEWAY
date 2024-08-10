from elasticsearch import Elasticsearch, exceptions
import os
from dotenv import load_dotenv

def get_elasticsearch_client(host="client"):
    load_dotenv()

    es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
    es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
    es_username = os.getenv("ELASTICSEARCH_USERNAME")
    es_password = os.getenv("ELASTICSEARCH_PASSWORD")

    es_url = f"http://{es_host}:{es_port}/"
    es = None
    if es is None:
        try:
            if host=="Local":
                es_host = os.getenv("ELASTICSEARCH_LOCALHOST", "localhost")
                es_url = f"http://{es_host}:{es_port}/"

            print("ES_URL: ", es_url)
            print("username: ", es_username)
            print("password: ", es_password)
            es = Elasticsearch(
                [es_url],
                basic_auth=(es_username, es_password) if es_username and es_password else None
            )
            if not es.ping():
                raise exceptions.ConnectionError("Elasticsearch server is not reachable")
            print("Successfully connected to Elasticsearch")

            # 檢查並建立 products 索引
            index_name = "products"
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
                print(f"Index '{index_name}' created successfully.")
            else:
                print(f"Index '{index_name}' already exists.")

        except exceptions.ConnectionError as e:
            print(f"Error connecting to Elasticsearch: {e}")
        except exceptions.RequestError as e:
            print(f"Error creating index: {e}")
    return es
