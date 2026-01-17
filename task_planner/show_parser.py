"""显示功能定位结果"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_planner.config import OMNIPARSER_DIR
from task_planner.screen_analyzer import ScreenAnalyzer
import pyautogui
from PIL import Image, ImageDraw, ImageTk, ImageFont
import tkinter as tk
import re

def parse_coordinates(parser_output, img_width, img_height):
    """解析功能定位输出中的坐标并转换为像素坐标"""
    import json

    coords = []
    lines = parser_output.strip().split('\n')

    for line in lines:
        if line.startswith('icon'):
            try:
                # 提取JSON部分
                json_str = line.split(': ', 1)[1]
                data = eval(json_str)  # 使用eval因为是Python字典格式

                if 'bbox' in data:
                    bbox = data['bbox']
                    # 转换比例坐标为像素坐标
                    x1 = int(bbox[0] * img_width)
                    y1 = int(bbox[1] * img_height)
                    x2 = int(bbox[2] * img_width)
                    y2 = int(bbox[3] * img_height)

                    coords.append({
                        'coords': (x1, y1, x2, y2),
                        'content': data.get('content', ''),
                        'type': data.get('type', '')
                    })
            except:
                continue

    return coords

def show_parser_result():
    """显示功能定位结果"""
    print("正在截图并分析...")

    # 截图
    screenshot = pyautogui.screenshot()

    # 获取功能定位结果
    analyzer = ScreenAnalyzer(OMNIPARSER_DIR)
    result = analyzer.analyze("parser")

    if 'parser_output' not in result:
        print("未找到功能定位结果")
        return

    parser_output = result['parser_output']
    print(f"\n找到 {len(parser_output.split('icon'))-1} 个元素\n")

    # 解析坐标
    img_width, img_height = screenshot.size
    elements = parse_coordinates(parser_output, img_width, img_height)
    print(f"成功解析 {len(elements)} 个元素坐标")

    # 绘制框
    draw = ImageDraw.Draw(screenshot)

    for i, elem in enumerate(elements):
        x1, y1, x2, y2 = elem['coords']

        # 绘制红框
        for j in range(3):
            draw.rectangle([x1-j, y1-j, x2+j, y2+j], outline="red")

        # 绘制编号和内容
        label = f"{i}: {elem['content'][:10]}" if elem['content'] else f"{i}"
        draw.text((x1, y1-15), label, fill="red")

    # 显示
    root = tk.Tk()
    root.title(f"功能定位结果 ({len(elements)}个元素)")
    root.attributes('-topmost', True)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}+0+0")

    photo = ImageTk.PhotoImage(screenshot)
    label = tk.Label(root, image=photo)
    label.pack()

    print("显示中，点击窗口关闭")
    label.bind('<Button-1>', lambda _: root.destroy())
    root.mainloop()

if __name__ == "__main__":
    show_parser_result()
