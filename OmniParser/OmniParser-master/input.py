"""
OmniParser 截图监听模块
功能：通过键盘监听截图，自动进行 OmniParser 解析和 Qwen-VL 分析
按 Enter 键截图，按 Esc 键退出
"""
import os
import sys
import io
import base64
import threading
from datetime import datetime
from pynput import keyboard
import pyautogui
from PIL import Image

# 切换到脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 设置 HuggingFace 镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 导入模块
from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img
from qwen import analyze_with_qwen

# ========== 全局变量 ==========
OUTPUT_DIR = r"D:\OmniParser\OmniParser-master\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

listener = None
is_running = True

# ========== 加载模型 ==========
print("正在加载 OmniParser 模型...")
yolo_model = get_yolo_model(model_path='weights/icon_detect/model.pt')
caption_model_processor = get_caption_model_processor(
    model_name="florence2",
    model_name_or_path="weights/icon_caption_florence"
)
print("模型加载完成！\n")

# ========== 日志函数 ==========
def print_log(message):
    """打印日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

# ========== OmniParser 处理 ==========
def process_screenshot(image_input):
    """OmniParser 解析"""
    box_threshold = 0.05
    iou_threshold = 0.1
    imgsz = 640
    
    box_overlay_ratio = image_input.size[0] / 3200
    draw_bbox_config = {
        'text_scale': 0.8 * box_overlay_ratio,
        'text_thickness': max(int(2 * box_overlay_ratio), 1),
        'text_padding': max(int(3 * box_overlay_ratio), 1),
        'thickness': max(int(3 * box_overlay_ratio), 1),
    }
    
    ocr_bbox_rslt, _ = check_ocr_box(
        image_input, display_img=False, output_bb_format='xyxy',
        easyocr_args={'paragraph': False, 'text_threshold': 0.9},
        use_paddleocr=False
    )
    text, ocr_bbox = ocr_bbox_rslt
    
    dino_labled_img, _, parsed_content_list = get_som_labeled_img(
        image_input, yolo_model, BOX_TRESHOLD=box_threshold,
        output_coord_in_ratio=True, ocr_bbox=ocr_bbox,
        draw_bbox_config=draw_bbox_config,
        caption_model_processor=caption_model_processor,
        ocr_text=text, iou_threshold=iou_threshold, imgsz=imgsz
    )
    
    image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
    parsed_text = '\n'.join([f'icon {i}: {str(v)}' for i, v in enumerate(parsed_content_list)])
    
    return image, parsed_text

# ========== 截图并处理 ==========
def capture_and_process():
    """截图 → OmniParser → Qwen-VL"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print_log(f"检测到 Enter，开始处理...")
    
    # 1. 截图
    print_log("📸 正在截图...")
    screenshot = pyautogui.screenshot()
    raw_path = os.path.join(OUTPUT_DIR, f"{timestamp}_raw.png")
    screenshot.save(raw_path)
    print_log(f"✓ 原始截图已保存: {raw_path}")
    
    # 2. OmniParser 解析
    print_log("🔍 正在使用 OmniParser 解析...")
    try:
        processed_img, parsed_text = process_screenshot(screenshot)
        
        processed_path = os.path.join(OUTPUT_DIR, f"{timestamp}_processed.png")
        processed_img.save(processed_path)
        
        parsed_path = os.path.join(OUTPUT_DIR, f"{timestamp}_parsed.txt")
        with open(parsed_path, 'w', encoding='utf-8') as f:
            f.write(parsed_text)
        print_log(f"✓ OmniParser 解析完成: {processed_path}")
    except Exception as e:
        print_log(f"✗ OmniParser 处理失败: {e}")
        return
    
    # 3. Qwen-VL 分析
    print_log("🤖 正在使用 Qwen-VL 分析...")
    try:
        analysis = analyze_with_qwen(
            raw_path,
            '分析这个屏幕截图，以 JSON 格式输出：{"顶部导航栏": {"应用名称": "","菜单项": [],"工具栏": []},"左侧边栏": {"导航项": [],"当前选中": ""},"主内容区": {"内容类型": "","用户操作": "","主题": ""},"底部区域": {"状态栏": "","任务栏应用": []},"其他细节": []}'
        )
        
        analysis_path = os.path.join(OUTPUT_DIR, f"{timestamp}_analysis.txt")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            f.write(analysis)
        print_log(f"✓ Qwen-VL 分析完成: {analysis_path}")
    except Exception as e:
        print_log(f"✗ Qwen-VL 分析失败: {e}")
    
    print_log("✓ 处理完成！\n")

# ========== 键盘监听 ==========
def on_press(key):
    """键盘按键回调"""
    global is_running
    
    if key == keyboard.Key.enter and is_running:
        # 在新线程中处理截图，避免阻塞监听
        threading.Thread(target=capture_and_process, daemon=True).start()
    elif key == keyboard.Key.esc:
        print_log("检测到 Esc 键，正在退出...")
        is_running = False
        return False  # 停止监听器

# ========== 主程序 ==========
def main():
    """主程序入口"""
    global listener, is_running
    
    print("=" * 60)
    print("🖥️  OmniParser 键盘监听系统")
    print("=" * 60)
    print("📋 使用说明：")
    print("   • 按 Enter 键：截图并分析")
    print("   • 按 Esc 键：退出程序")
    print("=" * 60)
    print()
    
    print_log("✅ 监听已启动，等待按键...")
    print_log("💡 提示：按 Enter 截图，按 Esc 退出")
    
    # 启动键盘监听
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    try:
        # 保持程序运行
        while is_running:
            listener.join(timeout=1)
            if not listener.running:
                break
    except KeyboardInterrupt:
        print_log("检测到 Ctrl+C，正在退出...")
        is_running = False
    
    # 清理资源
    if listener and listener.running:
        listener.stop()
    
    print_log("🛑 程序已退出")
    print("感谢使用 OmniParser 监听系统！")

# ========== 启动 ==========
if __name__ == "__main__":
    main()