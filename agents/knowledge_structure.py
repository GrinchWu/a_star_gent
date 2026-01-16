"""知识结构化Agent - 将内容组织成章节结构"""
from agents.base_agent import BaseAgent
from tools.llm_tools import call_vl_model, analyze_image

class KnowledgeStructureAgent(BaseAgent):
    def __init__(self):
        super().__init__("KnowledgeStructureAgent")

    def run(self, pages: list, video_summaries: list, app_name: str) -> dict:
        self.log(f"开始结构化 {app_name} 的知识")

        # 1. 处理图片内容
        for page in pages:
            if page.get('images'):
                page['image_descriptions'] = []
                for img_url in page['images'][:5]:  # 每页最多处理5张图
                    try:
                        desc = analyze_image(img_url, "描述这张图片展示的内容，如果是操作截图请描述操作步骤")
                        page['image_descriptions'].append({'url': img_url, 'description': desc})
                    except:
                        pass

        # 2. 整合所有内容
        all_content = self._merge_content(pages, video_summaries)

        # 3. 用LLM生成结构化知识
        structured = self._structure_knowledge(all_content, app_name)

        return {'status': 'success', 'knowledge': structured, 'app_name': app_name}

    def _merge_content(self, pages: list, video_summaries: list) -> str:
        content_parts = []
        for page in pages:
            part = f"## 来源: {page.get('url', 'unknown')}\n{page.get('text', '')[:3000]}"
            if page.get('image_descriptions'):
                part += "\n### 图片说明:\n"
                for img in page['image_descriptions']:
                    part += f"- {img['description']}\n"
            content_parts.append(part)

        for video in video_summaries:
            if video.get('status') == 'success':
                content_parts.append(f"## 视频内容: {video.get('url', '')}\n{video.get('summary', '')}")

        return "\n\n".join(content_parts)

    def _structure_knowledge(self, content: str, app_name: str) -> dict:
        prompt = f"""请将以下关于"{app_name}"的内容整理成结构化的知识文档。

要求:
1. 按照逻辑分成多个章节(如: 简介、安装、基础用法、高级功能、常见问题等)
2. 每个章节包含标题和内容
3. 保留关键的操作步骤和代码示例
4. 输出JSON格式: {{"chapters": [{{"title": "章节标题", "content": "章节内容"}}]}}

原始内容:
{content[:15000]}"""

        messages = [{'role': 'user', 'content': prompt}]
        response = call_vl_model(messages)

        # 解析JSON
        import json
        try:
            # 尝试提取JSON
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass

        return {'chapters': [{'title': '文档内容', 'content': response}]}
