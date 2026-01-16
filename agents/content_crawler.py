"""内容抓取Agent - 抓取网页内容"""
from agents.base_agent import BaseAgent
from tools.web_tools import fetch_page, extract_content, extract_links
from urllib.parse import urlparse

class ContentCrawlerAgent(BaseAgent):
    def __init__(self):
        super().__init__("ContentCrawlerAgent")

    def run(self, urls: list, max_depth: int = 2) -> dict:
        self.log(f"开始抓取 {len(urls)} 个页面")
        all_content = []
        visited = set()

        for url in urls:
            self._crawl(url, all_content, visited, depth=0, max_depth=max_depth)

        self.log(f"共抓取 {len(all_content)} 个页面内容")
        return {'status': 'success', 'pages': all_content}

    def _crawl(self, url: str, results: list, visited: set, depth: int, max_depth: int):
        if url in visited or depth > max_depth:
            return
        visited.add(url)

        try:
            html = fetch_page(url)
            content = extract_content(html, url)
            content['url'] = url
            content['depth'] = depth
            results.append(content)
            self.log(f"抓取成功: {url}")

            # 递归抓取子链接
            if depth < max_depth:
                links = extract_links(html, url, r'(doc|guide|tutorial|api|reference)')
                base_domain = urlparse(url).netloc
                for link in links[:5]:
                    if urlparse(link['url']).netloc == base_domain:
                        self._crawl(link['url'], results, visited, depth + 1, max_depth)
        except Exception as e:
            self.log(f"抓取失败 {url}: {e}")
