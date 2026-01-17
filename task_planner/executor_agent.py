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

    def handle_feedback(self, feedback_type: str, user_input: str = "", save_highlight: bool = False):
        """
        处理用户反馈
        feedback_type: "next" | "error" | "question" | "challenge" | "highlight"
        save_highlight: 是否保存高亮信息到文件（仅对highlight有效）
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
            return self._handle_highlight(current_step, save_highlight)

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
            try:
                rag_docs = self.knowledge_base.search(self.user_goal, top_k=3)
            except Exception as e:
                print(f"知识库访问失败: {e}")
                rag_docs = []

            # 构建包含执行历史的上下文
            context_with_history = {
                **screen_info,
                'executed_steps': self.memory
            }

            new_plan = self.planner.plan_from_current_state(self.user_goal, context_with_history, rag_docs)
            self.current_plan = new_plan
            self.current_step_idx = 0
            return {"status": "replanned", "explanation": result['explanation'], "new_plan": new_plan}
        else:
            return {"status": "confirmed", "explanation": result['explanation']}

    def _handle_highlight(self, current_step, save_to_file=False):
        """处理高亮请求"""
        # 获取屏幕分析（功能定位+大模型）
        screen_info = self.screen_analyzer.analyze("both")

        prompt = f"""分析这一步应该在屏幕的哪个位置操作。从 parsed_content_list 中选择最匹配的图标ID。

当前步骤：
{json.dumps(current_step, ensure_ascii=False, indent=2)}

屏幕解析结果：
{screen_info.get('parser_output', '')}

输出JSON（只返回图标ID）：
{{
  "icon_id": 0,
  "description": "操作区域描述"
}}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是屏幕定位助手，从解析结果中选择最匹配的图标ID。输出纯JSON。"},
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

        # 从 parsed_content_list 获取坐标
        if result.get('icon_id') is not None and 'parsed_content_list' in screen_info:
            icon_id = result['icon_id']
            parsed_list = screen_info['parsed_content_list']
            if 0 <= icon_id < len(parsed_list):
                coordinates = parsed_list[icon_id].get('bbox')
                if coordinates:
                    # 保存到文件
                    if save_to_file:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"highlight_{timestamp}.txt"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(f"=== 高亮信息 ===\n\n")
                            f.write(f"当前步骤：\n{json.dumps(current_step, ensure_ascii=False, indent=2)}\n\n")
                            f.write(f"选择的图标ID：{icon_id}\n\n")
                            f.write(f"图标信息：\n{json.dumps(parsed_list[icon_id], ensure_ascii=False, indent=2)}\n\n")
                            f.write(f"坐标（bbox）：{coordinates}\n\n")
                            f.write(f"描述：{result.get('description', '')}\n\n")
                            f.write(f"完整解析结果：\n{screen_info.get('parser_output', '')}\n")

                    self._highlight_area(coordinates)
                    return {"status": "highlighted", "coordinates": coordinates, "description": result.get('description', '')}

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
        return self.screen_analyzer.analyze("llm")

    def _format_memory(self):
        """格式化记忆"""
        return json.dumps(self.memory, ensure_ascii=False, indent=2)

    def _clear_memory(self):
        """清空记忆"""
        self.memory = []

    def _highlight_area(self, coordinates):
        """在屏幕上高亮区域"""
        import tkinter as tk
        import pyautogui

        # 获取屏幕尺寸
        screen_w, screen_h = pyautogui.size()

        # 解析坐标（支持多种格式）
        if isinstance(coordinates, dict):
            if 'x' in coordinates:
                x1, y1 = coordinates['x'], coordinates['y']
                x2, y2 = x1 + coordinates['width'], y1 + coordinates['height']
            elif 'bbox' in coordinates:
                bbox = coordinates['bbox']
                x1, y1 = int(bbox[0] * screen_w), int(bbox[1] * screen_h)
                x2, y2 = int(bbox[2] * screen_w), int(bbox[3] * screen_h)
        elif isinstance(coordinates, list) and len(coordinates) == 4:
            x1, y1 = int(coordinates[0] * screen_w), int(coordinates[1] * screen_h)
            x2, y2 = int(coordinates[2] * screen_w), int(coordinates[3] * screen_h)

        # 创建透明窗口
        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.3)
        root.configure(bg='black')

        # 创建画布
        canvas = tk.Canvas(root, bg='black', highlightthickness=0)
        canvas.pack(fill='both', expand=True)

        # 绘制红框
        canvas.create_rectangle(x1, y1, x2, y2, outline='red', width=5)

        # 3秒后关闭
        root.after(3000, root.destroy)
        root.mainloop()
