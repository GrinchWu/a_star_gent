"""任务规划Agent"""
from openai import OpenAI
from task_planner.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

class TaskPlannerAgent:
    def __init__(self):
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    def suggest_tasks(self, rag_docs: list) -> str:
        """根据RAG文档推荐可实现的功能"""
        prompt = f"""根据以下应用文档，推荐3个最简单、最基础的功能供用户学习：

{self._format_docs(rag_docs)}

要求：
1. 选择最简单、最容易上手的功能
2. 每个功能用一句话描述
3. 按难度从易到难排序

输出格式：
1. [功能名称] - [简短描述]
2. ...
3. ..."""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是一个应用功能推荐助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content

    def plan(self, user_goal: str, screen_info: dict, rag_docs: list) -> dict:
        """
        生成任务计划（根据置信度动态规划）
        user_goal: 用户目标
        screen_info: 屏幕分析信息
        rag_docs: RAG检索到的文档列表
        """
        context = self._build_context(screen_info)

        prompt = f"""你是任务规划助手。用户目标：{user_goal}

当前屏幕状态：
{context}

目标应用文档：
{self._format_docs(rag_docs)}

**关键要求**：
1. 根据当前屏幕状态，识别用户当前处于什么应用/环境中
2. 识别目标应用是什么，通常是浏览器中的Web应用
3. 如果当前不在目标应用中，必须先规划如何进入目标应用：
   - 打开浏览器（如果未打开）
   - 访问目标应用网址
   - 处理登录/注册（如果需要）
   - 等待页面加载完成
4. 只有确认进入目标应用后，才规划具体功能操作
5. 每步是原子操作，包含预期结果
6. **只规划到置信度>0.8的步骤**，不确定的步骤需要执行反馈后再规划

输出JSON：
{{
  "current_app": "当前所在应用",
  "target_app": "目标应用名称和网址",
  "steps": [
    {{"step": 1, "action": "操作", "target": "对象", "detail": "说明", "expected_result": "预期结果", "confidence": 0.95}},
    ...
  ],
  "need_feedback": true/false,
  "next_info_needed": "需要什么信息继续规划"
}}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是专业任务规划助手，只规划高置信度步骤。输出必须是纯JSON格式，不要包含任何其他文字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        import json
        content = response.choices[0].message.content.strip()

        # 提取JSON（如果被markdown包裹）
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"JSON解析失败，原始内容：\n{content}\n")
            raise

    def plan_from_current_state(self, user_goal: str, screen_info: dict, rag_docs: list) -> dict:
        """
        从当前状态继续规划（考虑已执行步骤）
        user_goal: 用户目标
        screen_info: 屏幕分析信息（包含executed_steps）
        rag_docs: RAG检索到的文档列表
        """
        context = self._build_context(screen_info)
        executed_steps = screen_info.get('executed_steps', [])

        prompt = f"""你是任务规划助手。用户目标：{user_goal}

当前屏幕状态：
{context}

已执行的步骤（禁止重复）：
{json.dumps(executed_steps, ensure_ascii=False, indent=2)}

目标应用文档：
{self._format_docs(rag_docs)}

**关键要求**：
1. 根据当前屏幕状态，识别用户当前处于什么位置
2. **禁止规划任何已执行过的步骤**
3. 从当前状态继续规划，只规划接下来需要执行的步骤
4. 如果用户已经在目标应用中，直接规划功能操作步骤
5. 每步是原子操作，包含预期结果
6. **只规划到置信度>0.8的步骤**

输出JSON：
{{
  "current_app": "当前所在应用",
  "target_app": "目标应用名称",
  "steps": [
    {{"step": 1, "action": "操作", "target": "对象", "detail": "说明", "expected_result": "预期结果", "confidence": 0.95}},
    ...
  ],
  "need_feedback": true/false,
  "next_info_needed": "需要什么信息继续规划"
}}"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是专业任务规划助手，从当前状态继续规划，禁止重复已执行步骤。输出必须是纯JSON格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        import json
        content = response.choices[0].message.content.strip()

        # 提取JSON（如果被markdown包裹）
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"JSON解析失败，原始内容：\n{content}\n")
            raise

    def _build_context(self, screen_info: dict) -> str:
        """构建屏幕上下文"""
        parts = []
        if 'llm_analysis' in screen_info:
            parts.append(f"大模型分析：\n{screen_info['llm_analysis']}")
        if 'parser_output' in screen_info:
            parts.append(f"功能定位：\n{screen_info['parser_output']}")
        return "\n\n".join(parts)

    def _format_docs(self, docs: list) -> str:
        """格式化文档"""
        return "\n\n".join([f"文档{i+1}：\n{doc['content']}" for i, doc in enumerate(docs)])
