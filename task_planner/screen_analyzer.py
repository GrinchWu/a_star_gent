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
            parsed_text = self._parse_screenshot(screenshot)
            result['parser_output'] = parsed_text

        # 大模型分析
        if mode in ["llm", "both"]:
            # 保存临时截图
            temp_path = os.path.join(self.omniparser_dir, "output", f"{timestamp}_temp.png")
            screenshot.save(temp_path)

            analysis = self.analyze_with_qwen(
                temp_path,
                '分析这个屏幕截图，以 JSON 格式输出：{"顶部导航栏": {"应用名称": "","菜单项": [],"工具栏": []},"左侧边栏": {"导航项": [],"当前选中": ""},"主内容区": {"内容类型": "","用户操作": "","主题": ""},"底部区域": {"状态栏": "","任务栏应用": []},"其他细节": []}'
            )
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
        return parsed_text
