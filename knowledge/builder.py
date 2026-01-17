"""知识库构建器"""
import os
from knowledge.md_parser import parse_markdown
from knowledge.vl_processor import VLProcessor
from knowledge.vector_store import VectorStore

class KnowledgeBuilder:
    def __init__(self):
        self.vector_store = VectorStore()

    def build(self, md_path: str, app_name: str):
        """从Markdown构建知识库"""
        print(f"解析文档: {md_path}")
        sections = parse_markdown(md_path)
        print(f"找到 {len(sections)} 个章节")

        md_dir = os.path.dirname(os.path.abspath(md_path))
        self.vl_processor = VLProcessor(md_dir=md_dir)

        texts = []
        metadatas = []

        for i, section in enumerate(sections):
            print(f"处理章节 {i+1}/{len(sections)}: {section['title']}")

            if section['images']:
                summary = self.vl_processor.process_section(section)
            else:
                summary = section['text']

            if summary.strip():
                # 添加章节标题到内容中，便于检索
                full_content = f"# {section['title']}\n\n{summary}"
                texts.append(full_content)
                metadatas.append({
                    'app': app_name,
                    'title': section['title'],
                    'chapter': section['title'],
                    'section_id': i
                })

        print(f"存储 {len(texts)} 个文档块")
        self.vector_store.add(texts, metadatas)
        print("完成")

    def search(self, query: str, top_k: int = 5):
        """检索知识库"""
        return self.vector_store.search(query, top_k)
