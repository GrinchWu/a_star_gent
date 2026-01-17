import base64
from openai import OpenAI

def analyze_with_qwen(image_path, prompt):
    """分析图片（非流式）"""

    # 1. 读取图片并转 base64
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()

    # 2. 创建客户端
    client = OpenAI(
        base_url='https://api-inference.modelscope.cn/v1',
        api_key='ms-4e1541a2-a2be-4b06-806e-2daa9a550767',
        timeout=60.0,
    )

    # 3. 非流式请求
    response = client.chat.completions.create(
        model='Qwen/Qwen3-VL-8B-Instruct',
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_base64}'}},
            ],
        }],
        stream=False
    )

    return response.choices[0].message.content


# 使用示例
if __name__ == "__main__":
    result = analyze_with_stream(
        r"D:\OmniParser\OmniParser-master\image.png",
        """分析这个屏幕截图，以 JSON 格式输出：

            {
            "顶部导航栏": {
                "应用名称": "",
                "菜单项": [],
                "工具栏": []
            },
            "左侧边栏": {
                "导航项": [],
                "当前选中": ""
            },
            "主内容区": {
                "内容类型": "",
                "用户操作": "",
                "主题": ""
            },
            "底部区域": {
                "状态栏": "",
                "任务栏应用": []
            },
            "其他细节": []
            }"""
                )
    
    # 保存结果
    with open("analysis_result.txt", "w", encoding="utf-8") as f:
        f.write(result)
