"""向量存储"""
import time
import chromadb
from openai import OpenAI
from knowledge.config import MODELSCOPE_API_KEY, MODELSCOPE_BASE_URL, EMBEDDING_MODEL

class VectorStore:
    def __init__(self, collection_name: str = "knowledge_base"):
        self.client = chromadb.PersistentClient(path="./data/chroma")
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embed_client = OpenAI(api_key=MODELSCOPE_API_KEY, base_url=MODELSCOPE_BASE_URL)

    def embed(self, text: str, retries: int = 3) -> list:
        """文本向量化，带重试"""
        for i in range(retries):
            try:
                response = self.embed_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
                return response.data[0].embedding
            except Exception as e:
                if i < retries - 1:
                    wait_time = (i + 1) * 2
                    print(f"Embedding失败，{wait_time}秒后重试... ({i+1}/{retries})")
                    time.sleep(wait_time)
                else:
                    raise

    def add(self, texts: list, metadatas: list):
        """添加文档"""
        embeddings = []
        for i, t in enumerate(texts):
            print(f"向量化 {i+1}/{len(texts)}")
            embeddings.append(self.embed(t))
            time.sleep(1)  # 避免速率限制

        ids = [f"doc_{i}" for i in range(len(texts))]
        self.collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, top_k: int = 5) -> list:
        """检索"""
        query_embedding = self.embed(query)
        results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
        return [{'content': doc, 'metadata': meta, 'distance': dist}
                for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0])]
