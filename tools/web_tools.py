"""网页抓取工具"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def fetch_page(url: str) -> str:
    """获取网页HTML"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text

def extract_links(html: str, base_url: str, pattern: str = None) -> list:
    """提取页面链接"""
    soup = BeautifulSoup(html, 'lxml')
    links = []
    for a in soup.find_all('a', href=True):
        href = urljoin(base_url, a['href'])
        if pattern and not re.search(pattern, href, re.I):
            continue
        links.append({'url': href, 'text': a.get_text(strip=True)})
    return links

def extract_content(html: str, base_url: str) -> dict:
    """提取页面内容：文字、图片、视频"""
    soup = BeautifulSoup(html, 'lxml')
    # 移除脚本和样式
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    # 提取文字
    text = soup.get_text(separator='\n', strip=True)

    # 提取图片
    images = [urljoin(base_url, img['src']) for img in soup.find_all('img', src=True)]

    # 提取视频
    videos = []
    for video in soup.find_all('video'):
        src = video.get('src') or (video.find('source') and video.find('source').get('src'))
        if src:
            videos.append(urljoin(base_url, src))
    # iframe视频(YouTube等)
    for iframe in soup.find_all('iframe', src=True):
        if any(x in iframe['src'] for x in ['youtube', 'vimeo', 'bilibili']):
            videos.append(iframe['src'])

    return {'text': text, 'images': images, 'videos': videos}

def search_docs_in_site(base_url: str) -> list:
    """在网站内搜索文档链接"""
    try:
        html = fetch_page(base_url)
        links = extract_links(html, base_url, r'(doc|guide|tutorial|manual|help|learn|getting.?started)')
        return links[:20]
    except Exception as e:
        return []

def web_search(query: str) -> list:
    """使用搜索引擎搜索(简化版，实际需要接入搜索API)"""
    # 这里返回模拟结果，实际使用时需要接入Google/Bing API
    return [{'url': f'https://example.com/doc/{i}', 'title': f'{query} 文档 {i}'} for i in range(5)]
