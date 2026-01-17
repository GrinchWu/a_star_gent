"""屏幕分析模块接口"""
import os
import sys
import pyautogui
from datetime import datetime
from PIL import Image

class ScreenAnalyzer:
    def __init__(self, omniparser_dir: str):
        self.omniparser_dir = omniparser_dir

    def _load_models(self, mode: str):
        """加载OmniParser模型"""
        os.chdir(self.omniparser_dir)
        sys.path.insert(0, self.omniparser_dir)

        # 只加载需要的模型
        if mode in ["parser", "both"] and not hasattr(self, 'yolo_model'):
            from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img

            self.yolo_model = get_yolo_model(model_path='weights/icon_detect/model.pt')
            self.caption_model_processor = get_caption_model_processor(
                model_name="florence2",
                model_name_or_path="weights/icon_caption_florence"
            )
            self.check_ocr_box = check_ocr_box
            self.get_som_labeled_img = get_som_labeled_img

        if mode in ["llm", "both"] and not hasattr(self, 'analyze_with_qwen'):
            from qwen import analyze_with_qwen
            self.analyze_with_qwen = analyze_with_qwen

    def analyze(self, mode: str = "both") -> dict:
        """
        分析屏幕
        mode: "llm" (大模型分析) | "parser" (功能定位) | "both" (两者结合)
        """
        self._load_models(mode)

        # 截图
        screenshot = pyautogui.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = {}

        # 功能定位
        if mode in ["parser", "both"]:
            parsed_text, parsed_content_list = self._parse_screenshot(screenshot)
            result['parser_output'] = parsed_text
            result['parsed_content_list'] = parsed_content_list

        # 大模型分析
        if mode in ["llm", "both"]:
            # 保存临时截图
            temp_path = os.path.join(self.omniparser_dir, "output", f"{timestamp}_temp.png")
            screenshot.save(temp_path)

            prompt = '''分析屏幕截图，根据窗口类型重点识别：

**浏览器窗口**：
- 标题栏：浏览器名称、标签页标题
- 地址栏：完整URL、书签栏
- 网页功能：这个网页是做什么的、主要功能有哪些
- 页面布局：导航菜单位置、主功能区、侧边栏
- 可交互元素：按钮、输入框、链接的文本和位置

**Windows开始菜单**：
- 搜索框：位置、是否聚焦
- 应用列表：固定应用、最近使用、所有应用
- 电源/设置按钮位置

**办公应用（Word/Excel/PPT）**：
- 顶部：文件名、菜单栏、工具栏按钮
- 左侧：页面导航、大纲
- 主编辑区：当前内容、光标位置
- 右侧：属性面板

**IDE/编辑器（VSCode/PyCharm）**：
- 顶部：项目名、菜单、工具栏
- 左侧：文件树、当前文件
- 主编辑区：代码内容、行号
- 底部：终端、输出

**聊天应用（微信/钉钉）**：
- 左侧：会话列表、当前选中
- 主区域：聊天记录、输入框
- 右侧：会话详情

**文件管理器**：
- 地址栏：当前路径
- 左侧：文件夹树
- 主区域：文件列表
- 工具栏：操作按钮

**桌面**：
- 桌面图标
- 任务栏：应用、系统托盘

以JSON格式输出：
{
  "窗口类型": "浏览器/开始菜单/办公应用/IDE/聊天应用/文件管理器/桌面",
  "应用名称": "",
  "窗口标题": "",
  "地址栏或路径": "",
  "网页功能说明": "",
  "顶部工具栏": [],
  "左侧面板": {"类型": "", "内容": []},
  "主内容区": {"类型": "", "当前内容": ""},
  "右侧面板": {"类型": "", "内容": []},
  "底部区域": "",
  "可交互元素": [{"类型": "", "文本": "", "位置": ""}],
  "当前状态": ""
}'''

            analysis = self.analyze_with_qwen(temp_path, prompt)
            result['llm_analysis'] = analysis

        return result

    def _parse_screenshot(self, image_input):
        """OmniParser解析"""
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

        ocr_bbox_rslt, _ = self.check_ocr_box(
            image_input, display_img=False, output_bb_format='xyxy',
            easyocr_args={'paragraph': False, 'text_threshold': 0.9},
            use_paddleocr=False
        )
        text, ocr_bbox = ocr_bbox_rslt

        _, _, parsed_content_list = self.get_som_labeled_img(
            image_input, self.yolo_model, BOX_TRESHOLD=box_threshold,
            output_coord_in_ratio=True, ocr_bbox=ocr_bbox,
            draw_bbox_config=draw_bbox_config,
            caption_model_processor=self.caption_model_processor,
            ocr_text=text, iou_threshold=iou_threshold, imgsz=imgsz
        )

        parsed_text = '\n'.join([f'icon {i}: {str(v)}' for i, v in enumerate(parsed_content_list)])
        return parsed_text, parsed_content_list
