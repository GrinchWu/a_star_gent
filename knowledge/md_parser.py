"""Markdown文档解析器"""
import re
from typing import List, Dict

def parse_markdown(md_path: str) -> List[Dict]:
    """解析Markdown文档，提取文本和图片"""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = []
    current_section = {'title': '', 'text': '', 'images': []}

    for line in content.split('\n'):
        # 标题
        if line.startswith('#'):
            if current_section['text'] or current_section['images']:
                sections.append(current_section)
            current_section = {'title': line.lstrip('#').strip(), 'text': '', 'images': []}
        # 图片
        elif '![' in line:
            imgs = re.findall(r'!\[.*?\]\((.*?)\)', line)
            current_section['images'].extend(imgs)
        # 文本
        else:
            current_section['text'] += line + '\n'

    if current_section['text'] or current_section['images']:
        sections.append(current_section)

    return sections
