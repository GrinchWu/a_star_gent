"""LLM调用工具"""
from openai import OpenAI
import config

client = OpenAI(base_url=config.MODELSCOPE_BASE_URL, api_key=config.MODELSCOPE_API_KEY)

def call_vl_model(messages: list, stream: bool = False) -> str:
    """调用多模态视觉语言模型"""
    response = client.chat.completions.create(
        model=config.VL_MODEL,
        messages=messages,
        stream=stream
    )
    if stream:
        result = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                result += chunk.choices[0].delta.content
        return result
    return response.choices[0].message.content

def get_embedding(text: str) -> list:
    """获取文本embedding"""
    response = client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

def analyze_image(image_url: str, prompt: str = "详细描述这张图片的内容") -> str:
    """分析图片内容"""
    messages = [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': image_url}}
        ]
    }]
    return call_vl_model(messages)

def analyze_video_frames(frame_urls: list, prompt: str = "根据这些视频帧，详细描述视频内容并总结关键知识点") -> str:
    """分析视频帧序列"""
    content = [{'type': 'text', 'text': prompt}]
    for url in frame_urls:
        content.append({'type': 'image_url', 'image_url': {'url': url}})
    messages = [{'role': 'user', 'content': content}]
    return call_vl_model(messages)
