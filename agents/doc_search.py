"""文档搜索Agent - 在官网和搜索引擎中查找文档"""
from agents.base_agent import BaseAgent
from tools.web_tools import fetch_page, extract_links, search_docs_in_site
from tools.llm_tools import call_vl_model

class DocSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("DocSearchAgent")

    def run(self, base_url: str, app_name: str) -> dict:
        self.log(f"开始搜索 {app_name} 的文档，官网: {base_url}")

        # 1. 先在官网搜索文档链接
        doc_links = search_docs_in_site(base_url)

        if doc_links:
            self.log(f"在官网找到 {len(doc_links)} 个文档链接")
            # 用LLM筛选最相关的文档链接
            links_text = "\n".join([f"- {l['text']}: {l['url']}" for l in doc_links[:20]])
            messages = [{
                'role': 'user',
                'content': f"以下是{app_name}官网的链接，请选出最可能是使用文档/教程的链接(返回URL列表，每行一个):\n{links_text}"
            }]
            response = call_vl_model(messages)
            filtered_urls = [line.strip() for line in response.split('\n') if line.strip().startswith('http')]
            if filtered_urls:
                return {'status': 'success', 'source': 'official', 'urls': filtered_urls[:10]}

        # 2. 官网没找到，使用搜索引擎
        self.log("官网未找到文档，尝试搜索引擎...")
        search_results = self._web_search(f"{app_name} 使用文档 教程")
        if search_results:
            return {'status': 'success', 'source': 'search', 'urls': [r['url'] for r in search_results]}

        return {'status': 'failed', 'urls': []}

    def _web_search(self, query: str) -> list:
        """调用搜索引擎(需要实际接入搜索API)"""
        # 简化实现，实际需要接入Google/Bing API
        return []
