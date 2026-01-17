"""视觉语言模型处理器"""
import os
import base64
from openai import OpenAI
from knowledge.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, VL_MODEL

class VLProcessor:
    def __init__(self, md_dir: str = None):
        self.client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
        self.md_dir = md_dir

    def _load_image_as_base64(self, img_path: str) -> str:
        """加载本地图片为 base64"""
        if not os.path.isabs(img_path) and self.md_dir:
            img_path = os.path.join(self.md_dir, img_path)

        with open(img_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()

        ext = os.path.splitext(img_path)[1].lower()
        mime_type = {'png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp'}.get(ext, 'image/png')
        return f"data:{mime_type};base64,{img_data}"

    def process_section(self, section: dict) -> str:
        """处理包含文本和图片的章节"""
        content = []

        prompt = f"""你是一个专业的技术文档分析专家。请深入分析以下内容，提取结构化知识。

章节标题：{section['title']}

分析要求：
1. 核心概念：识别并解释所有关键术语、技术名词和概念定义。对于每个概念，说明其含义、作用和与其他概念的关系。
2. 操作步骤：如果包含教程或操作指南，按顺序详细列出每个步骤。每个步骤应包含：具体操作、预期结果、注意事项。保留步骤编号和层级结构。
3. 技术细节：完整保留所有代码示例、配置参数、API接口、命令行指令、数据格式等技术信息。对代码进行简要说明，解释其功能和关键逻辑。
4. 图片说明：如果有图片，详细描述图片内容，包括：界面元素及其位置、按钮和菜单项、流程图的节点和连接关系、架构图的组件和交互、标注和箭头指向的含义。
5. 使用场景：说明该功能的典型应用场景、适用条件、最佳实践建议、常见问题和解决方案。

请用结构化的方式组织输出，保持信息完整性和准确性。"""

        content.append({"type": "text", "text": prompt})

        if section['text']:
            content.append({"type": "text", "text": f"\n文本内容：\n{section['text']}"})

        for img_url in section['images']:
            try:
                if img_url.startswith('http://') or img_url.startswith('https://'):
                    content.append({"type": "image_url", "image_url": {"url": img_url}})
                else:
                    base64_url = self._load_image_as_base64(img_url)
                    content.append({"type": "image_url", "image_url": {"url": base64_url}})
            except Exception as e:
                print(f"警告: 无法加载图片 {img_url}: {e}")

        if len(content) == 1:
            return ""

        response = self.client.chat.completions.create(
            model=VL_MODEL,
            messages=[{"role": "user", "content": content}]
        )

        return response.choices[0].message.content
