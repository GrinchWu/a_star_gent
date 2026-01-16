"""视频理解Agent - 使用qwen3-omni模型直接理解视频"""
from openai import OpenAI
from agents.base_agent import BaseAgent

# 阿里云DashScope配置
DASHSCOPE_API_KEY = "sk-471ef1d9f6734e79a4186adec3660bdd"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

class VideoUnderstandAgent(BaseAgent):
    """
    视频理解方案说明:
    使用阿里云qwen3-omni-flash模型直接理解视频内容。
    该模型支持视频输入，可以理解视频画面和音频内容。
    """

    def __init__(self):
        super().__init__("VideoUnderstandAgent")
        self.client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)

    def run(self, video_urls: list) -> dict:
        self.log(f"开始处理 {len(video_urls)} 个视频")
        results = []
        for url in video_urls:
            try:
                summary = self._process_video(url)
                results.append({'url': url, 'summary': summary, 'status': 'success'})
                self.log(f"视频处理成功: {url}")
            except Exception as e:
                results.append({'url': url, 'error': str(e), 'status': 'failed'})
                self.log(f"视频处理失败 {url}: {e}")
        return {'status': 'success', 'videos': results}

    def _process_video(self, video_url: str) -> str:
        """使用qwen3-omni模型处理视频"""
        prompt = """你是一个专业的视频内容分析专家。请仔细观看整个视频，从头到尾完整理解视频内容，包括画面、文字、语音旁白等所有信息。

请严格按照以下JSON格式输出分析结果:
```json
{
  "title": "视频标题或主题",
  "overview": "视频整体内容概述(100-200字)",
  "timeline": [
    {"time": "0:00-1:00", "content": "该时间段的内容描述"}
  ],
  "steps": [
    {"step": 1, "action": "具体操作步骤", "detail": "详细说明"}
  ],
  "key_points": ["关键知识点1", "关键知识点2"],
  "tips": ["注意事项或技巧"],
  "summary": "视频核心内容总结(50-100字)"
}
```

要求:
1. 必须完整观看视频，不要遗漏任何重要内容
2. timeline要覆盖视频全程，按时间顺序记录
3. steps要提取所有可操作的步骤，保持顺序
4. 只输出JSON，不要有其他文字"""

        messages = [{
            "role": "user",
            "content": [
                {"type": "video_url", "video_url": {"url": video_url}},
                {"type": "text", "text": prompt}
            ]
        }]

        response = self.client.chat.completions.create(
            model="qwen3-omni-flash",
            messages=messages,
            stream=True
        )

        result = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                result += chunk.choices[0].delta.content
        return result
