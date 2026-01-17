"""任务执行Agent"""
from openai import OpenAI
from task_planner.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from task_planner.screen_analyzer import ScreenAnalyzer
from task_planner.planner_agent import TaskPlannerAgent
from knowledge.vector_store import VectorStore
import json

class ExecutorAgent:
    def __init__(self, omniparser_dir: str):
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        self.screen_analyzer = ScreenAnalyzer(omniparser_dir)
        self.planner = TaskPlannerAgent()
        self.knowledge_base = VectorStore()
        self.memory = []  # 短期记忆：[{step, screen_info, status}]
        self.current_plan = None
        self.current_step_idx = 0
        self.user_goal = None

    def start_task(self, user_goal: str, initial_plan: dict):
        """开始任务"""
        self.user_goal = user_goal
        self.current_plan = initial_plan
        self.current_step_idx = 0
        self.memory = []

    def get_current_step(self):
        """获取当前步骤"""
        if self.current_step_idx < len(self.current_plan['steps']):
            return self.current_plan['steps'][self.current_step_idx]
        return None

    def handle_feedback(self, feedback_type: str, user_input: str = ""):
        """
        处理用户反馈
        feedback_type: "next" | "error" | "question" | "challenge" | "highlight"
        """
        current_step = self.get_current_step()
        if not current_step:
            return {"status": "completed", "message": "所有步骤已完成"}

        if feedback_type == "next":
            return self._handle_next(current_step)
        elif feedback_type == "error":
            return self._handle_error(current_step)
        elif feedback_type == "question":
            return self._handle_question(current_step, user_input)
        elif feedback_type == "challenge":
            return self._handle_challenge(current_step, user_input)
        elif feedback_type == "highlight":
            return self._handle_highlight(current_step)

    def _handle_next(self, current_step):
        """处理下一步"""
        # 记录当前步骤成功
        screen_info = self._get_screen_info()
        self.memory.append({
            "step": current_step,
            "screen_info": screen_info,
            "status": "success"
        })

        self.current_step_idx += 1

        # 检查是否需要继续规划
        if self._should_continue_planning():
            self._extend_plan()

        next_step = self.get_current_step()
        if next_step:
            return {"status": "continue", "next_step": next_step}
        else:
            self._clear_memory()
            return {"status": "completed", "message": "任务完成"}

    def _handle_error(self, current_step):
        """处理执行错误（用户误操作）"""
        # 记录失败
        screen_info = self._get_screen_info()
        self.memory.append({
            "step": current_step,
            "screen_info": screen_info,
            "status": "failed"
        })

        # 重新分析屏幕并规划
        screen_info = self.screen_analyzer.analyze("llm")
        rag_docs = self.knowledge_base.search(self.user_goal, top_k=3)

        new_plan = self.planner.plan(self.user_goal, screen_info, rag_docs)
        self.current_plan = new_plan
        self.current_step_idx = 0

        return {"status": "replanned", "new_plan": new_plan}

    def _handle_question(self, current_step, user_input):
        """处理用户疑问"""
        screen_info = self._get_screen_info()

        prompt = f"""用户对当前步骤有疑问。

用户问题：{user_input}

当前步骤：
{json.dumps(current_step, ensure_ascii=False, indent=2)}

当前屏幕状态：
{json.dumps(screen_info, ensure_ascii=False, indent=2)}

执行历史：
{self._format_memory()}

请根据以上信息回答用户的问题。"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是任务执行助手，根据执行历史和当前状态回答用户问题。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return {"status": "answered", "answer": response.choices[0].message.content}

    def _handle_challenge(self, current_step, user_input):
        """处理用户质疑"""
        prompt = f"""用户质疑当前步骤的正确性。

用户质疑：{user_input}

当前步骤：
{json.dumps(current_step, ensure_ascii=False, indent=2)}

执行历史：
{self._format_memory()}

请分析：
1. 这一步是否正确
2. 如果正确，解释为什么
3. 如果错误，说明问题

输出JSON：
{{
  "is_correct": true/false,
  "explanation": "解释"
}}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是任务规划审查助手，客观分析步骤正确性。输出纯JSON。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        if not result['is_correct']:
            # 重新规划
            screen_info = self._get_screen_info()
            rag_docs = self.knowledge_base.search(self.user_goal, top_k=3)
            new_plan = self.planner.plan(self.user_goal, screen_info, rag_docs)
            self.current_plan = new_plan
            self.current_step_idx = 0
            return {"status": "replanned", "explanation": result['explanation'], "new_plan": new_plan}
        else:
            return {"status": "confirmed", "explanation": result['explanation']}

    def _handle_highlight(self, current_step):
        """处理高亮请求"""
        # 获取屏幕分析（功能定位+大模型）
        screen_info = self.screen_analyzer.analyze("both")

        prompt = f"""分析这一步应该在屏幕的哪个位置操作。

当前步骤：
{json.dumps(current_step, ensure_ascii=False, indent=2)}

屏幕分析：
{json.dumps(screen_info, ensure_ascii=False, indent=2)}

输出JSON：
{{
  "coordinates": {{"x": 100, "y": 200, "width": 50, "height": 30}},
  "description": "操作区域描述"
}}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是屏幕定位助手，分析操作位置。输出纯JSON。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # 调用高亮工具
        if result.get('coordinates'):
            self._highlight_area(result['coordinates'])
            return {"status": "highlighted", "coordinates": result['coordinates'], "description": result.get('description', '')}
        else:
            return {"status": "error", "message": "无法定位操作区域"}

    def _should_continue_planning(self):
        """判断是否需要继续规划"""
        # 检查是否为核心步骤
        prompt = f"""判断已执行的步骤中有多少是核心步骤（已进入应用界面后的功能操作步骤）。

执行历史：
{self._format_memory()}

输出JSON：
{{
  "core_steps_count": 数字
}}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是步骤分析助手。输出纯JSON。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        return result['core_steps_count'] < 2 and self.current_step_idx >= len(self.current_plan['steps'])

    def _extend_plan(self):
        """扩展计划"""
        screen_info = self._get_screen_info()
        rag_docs = self.knowledge_base.search(self.user_goal, top_k=3)
        new_plan = self.planner.plan(self.user_goal, screen_info, rag_docs)

        # 合并计划
        self.current_plan['steps'].extend(new_plan['steps'])

    def _get_screen_info(self):
        """获取当前屏幕信息"""
        return self.screen_analyzer.analyze("both")

    def _format_memory(self):
        """格式化记忆"""
        return json.dumps(self.memory, ensure_ascii=False, indent=2)

    def _clear_memory(self):
        """清空记忆"""
        self.memory = []

    def _highlight_area(self, coordinates):
        """在屏幕上高亮区域"""
        import pyautogui
        from PIL import Image, ImageDraw, ImageTk
        import tkinter as tk

        # 截图
        screenshot = pyautogui.screenshot()
        screen_w, screen_h = screenshot.size

        # 解析坐标（支持多种格式）
        if isinstance(coordinates, dict):
            if 'x' in coordinates:
                # 格式: {'x': ..., 'y': ..., 'width': ..., 'height': ...}
                x, y, w, h = coordinates['x'], coordinates['y'], coordinates['width'], coordinates['height']
            elif 'bbox' in coordinates:
                # 格式: {'bbox': [x1, y1, x2, y2]}
                bbox = coordinates['bbox']
                x, y = int(bbox[0] * screen_w), int(bbox[1] * screen_h)
                w, h = int((bbox[2] - bbox[0]) * screen_w), int((bbox[3] - bbox[1]) * screen_h)
        elif isinstance(coordinates, list) and len(coordinates) == 4:
            # 格式: [x1, y1, x2, y2] (ratio)
            x, y = int(coordinates[0] * screen_w), int(coordinates[1] * screen_h)
            w, h = int((coordinates[2] - coordinates[0]) * screen_w), int((coordinates[3] - coordinates[1]) * screen_h)
        draw = ImageDraw.Draw(screenshot)

        # 绘制粗红框
        for i in range(8):
            draw.rectangle([x-i, y-i, x+w+i, y+h+i], outline="red")

        # 创建窗口
        root = tk.Tk()
        root.title("高亮区域")
        root.attributes('-topmost', True)

        # 全屏显示
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{screen_width}x{screen_height}+0+0")

        # 显示图片
        photo = ImageTk.PhotoImage(screenshot)
        label = tk.Label(root, image=photo)
        label.pack()

        # 10秒后关闭
        root.after(10000, root.destroy)

        print("高亮区域已显示，10秒后自动关闭（或点击窗口关闭）")
        label.bind('<Button-1>', lambda _: root.destroy())
        root.mainloop()
