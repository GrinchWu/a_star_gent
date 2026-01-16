"""知识库智能体系统 - 主入口"""
import argparse
import sys
sys.path.insert(0, 'd:/A_star_gent')

from agents.doc_search import DocSearchAgent
from agents.content_crawler import ContentCrawlerAgent
from agents.video_understand import VideoUnderstandAgent
from agents.knowledge_structure import KnowledgeStructureAgent
from agents.knowledge_store import KnowledgeStoreAgent

class KnowledgeBaseOrchestrator:
    """知识库智能体编排器 - 协调5个Agent完成知识库构建"""

    def __init__(self):
        self.doc_search = DocSearchAgent()
        self.content_crawler = ContentCrawlerAgent()
        self.video_understand = VideoUnderstandAgent()
        self.knowledge_structure = KnowledgeStructureAgent()
        self.knowledge_store = KnowledgeStoreAgent()

    def build_knowledge_base(self, base_url: str, app_name: str) -> dict:
        """构建知识库的完整流程"""
        print(f"\n{'='*50}")
        print(f"开始构建 {app_name} 的知识库")
        print(f"官网: {base_url}")
        print(f"{'='*50}\n")

        # 1. 搜索文档
        print("[1/5] 搜索文档...")
        search_result = self.doc_search.run(base_url, app_name)
        if search_result['status'] == 'failed' or not search_result.get('urls'):
            print("未找到文档，请检查URL或手动提供文档链接")
            return {'status': 'failed', 'error': 'no_docs_found'}

        doc_urls = search_result['urls']
        print(f"找到 {len(doc_urls)} 个文档链接")

        # 2. 抓取内容
        print("\n[2/5] 抓取页面内容...")
        crawl_result = self.content_crawler.run(doc_urls)
        pages = crawl_result.get('pages', [])

        # 3. 处理视频
        print("\n[3/5] 处理视频内容...")
        all_videos = []
        for page in pages:
            all_videos.extend(page.get('videos', []))

        video_summaries = []
        if all_videos:
            video_result = self.video_understand.run(all_videos[:5])  # 最多处理5个视频
            video_summaries = video_result.get('videos', [])
        else:
            print("未发现视频内容")

        # 4. 结构化知识
        print("\n[4/5] 结构化知识...")
        structure_result = self.knowledge_structure.run(pages, video_summaries, app_name)
        knowledge = structure_result.get('knowledge', {})

        # 5. 存储到知识库
        print("\n[5/5] 存储到知识库...")
        store_result = self.knowledge_store.run(knowledge, app_name)

        print(f"\n{'='*50}")
        print(f"知识库构建完成!")
        print(f"应用: {app_name}")
        print(f"章节数: {len(knowledge.get('chapters', []))}")
        print(f"存储文档块: {store_result.get('stored_count', 0)}")
        print(f"{'='*50}\n")

        return {'status': 'success', 'app_name': app_name, 'knowledge': knowledge}

    def search(self, query: str, app_name: str = None, top_k: int = 5) -> list:
        """RAG检索"""
        return self.knowledge_store.search(query, app_name, top_k)


def main():
    parser = argparse.ArgumentParser(description='知识库智能体系统')
    subparsers = parser.add_subparsers(dest='command')

    # build命令
    build_parser = subparsers.add_parser('build', help='构建知识库')
    build_parser.add_argument('--url', required=True, help='应用官网URL')
    build_parser.add_argument('--app_name', required=True, help='应用名称')

    # search命令
    search_parser = subparsers.add_parser('search', help='检索知识库')
    search_parser.add_argument('--query', required=True, help='检索问题')
    search_parser.add_argument('--app_name', help='应用名称(可选)')
    search_parser.add_argument('--top_k', type=int, default=5, help='返回结果数')

    args = parser.parse_args()
    orchestrator = KnowledgeBaseOrchestrator()

    if args.command == 'build':
        orchestrator.build_knowledge_base(args.url, args.app_name)
    elif args.command == 'search':
        results = orchestrator.search(args.query, args.app_name, args.top_k)
        print(f"\n检索结果 (共{len(results)}条):\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] 相关度: {1-r['distance']:.3f}")
            print(f"    章节: {r['metadata'].get('chapter', 'N/A')}")
            print(f"    内容: {r['content'][:200]}...")
            print()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
