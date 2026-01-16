"""知识存储Agent - 存储到向量数据库并支持RAG检索"""
import os
import json
from agents.base_agent import BaseAgent
from tools.llm_tools import get_embedding
import config

class KnowledgeStoreAgent(BaseAgent):
    def __init__(self):
        super().__init__("KnowledgeStoreAgent")
        self.db = None

    def _init_db(self):
        if self.db is None:
            import chromadb
            os.makedirs(config.CHROMA_DB_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
            self.db = client.get_or_create_collection(
                name="knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )

    def run(self, knowledge: dict, app_name: str) -> dict:
        self._init_db()
        self.log(f"开始存储 {app_name} 的知识到向量数据库")

        chapters = knowledge.get('chapters', [])
        stored_count = 0

        for i, chapter in enumerate(chapters):
            title = chapter.get('title', f'章节{i+1}')
            content = chapter.get('content', '')

            if not content.strip():
                continue

            # 分块存储(每块约500字)
            chunks = self._split_content(content, 500)
            for j, chunk in enumerate(chunks):
                doc_id = f"{app_name}_{i}_{j}"
                try:
                    embedding = get_embedding(chunk)
                    self.db.upsert(
                        ids=[doc_id],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{
                            'app_name': app_name,
                            'chapter': title,
                            'chunk_index': j
                        }]
                    )
                    stored_count += 1
                except Exception as e:
                    self.log(f"存储失败 {doc_id}: {e}")

        # 保存知识结构到文件
        os.makedirs(config.KNOWLEDGE_BASE_DIR, exist_ok=True)
        structure_path = os.path.join(config.KNOWLEDGE_BASE_DIR, f"{app_name}_structure.json")
        with open(structure_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2)

        self.log(f"存储完成，共 {stored_count} 个文档块")
        return {'status': 'success', 'stored_count': stored_count}

    def _split_content(self, content: str, chunk_size: int) -> list:
        chunks = []
        paragraphs = content.split('\n\n')
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < chunk_size:
                current += p + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = p + "\n\n"
        if current:
            chunks.append(current.strip())
        return chunks if chunks else [content]

    def search(self, query: str, app_name: str = None, top_k: int = 5) -> list:
        """RAG检索"""
        self._init_db()
        query_embedding = get_embedding(query)

        where_filter = {"app_name": app_name} if app_name else None
        results = self.db.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        return [{
            'content': doc,
            'metadata': meta,
            'distance': dist
        } for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )]
