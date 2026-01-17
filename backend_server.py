"""Flask后端服务 - 连接前端和executor_main.py"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from task_planner.config import OMNIPARSER_DIR
from task_planner.executor_agent import ExecutorAgent
from task_planner.planner_agent import TaskPlannerAgent
from task_planner.screen_analyzer import ScreenAnalyzer
from task_planner.agent_recommender import AgentRecommender

app = Flask(__name__)
CORS(app)

# 全局变量存储系统状态
executor = None
planner = None
screen_analyzer = None
agent_recommender = None
conversation_history = []
current_agent_name = None
guide_state = 'initial'  # 'initial', 'function_selection', 'execution'

def init_system():
    """初始化系统"""
    global executor, planner, screen_analyzer, agent_recommender
    executor = ExecutorAgent(OMNIPARSER_DIR)
    planner = TaskPlannerAgent()
    screen_analyzer = ScreenAnalyzer(OMNIPARSER_DIR)
    agent_recommender = AgentRecommender(executor.knowledge_base)

@app.route('/api/task', methods=['POST'])
def handle_task():
    """处理任务输入模式的消息"""
    data = request.json
    message = data.get('message', '')

    # LLM Agent推荐
    response = agent_recommender.recommend(message, message)

    # 保存对话历史
    conversation_history.append({"role": "user", "content": message})
    conversation_history.append({"role": "assistant", "content": response})

    return jsonify({"response": response})

@app.route('/api/guide', methods=['POST'])
def handle_guide():
    """处理操作指引模式的消息"""
    global current_agent_name, guide_state
    data = request.json
    message = data.get('message', '')

    if guide_state == 'initial':
        # 第一步：根据agent名称搜索
        current_agent_name = message
        rag_docs = executor.knowledge_base.search(message, top_k=5)

        if not rag_docs:
            return jsonify({"response": f"抱歉，我在知识库中没有找到关于 {message} 的相关信息。请确认Agent名称是否正确。"})

        # 第二步：功能推荐
        suggestions = planner.suggest_tasks(rag_docs)
        guide_state = 'function_selection'

        return jsonify({
            "response": f"好的，我将为您提供 {message} 的操作指引。\n\n我可以带你实现以下功能：\n{suggestions}\n\n请选择或输入你想实现的功能。",
            "state": "function_selection"
        })

    elif guide_state == 'function_selection':
        # 第三步：生成初始计划
        user_goal = message
        rag_docs = executor.knowledge_base.search(user_goal, top_k=3)
        screen_info = screen_analyzer.analyze("llm")
        plan = planner.plan(user_goal, screen_info, rag_docs)

        # 开始执行
        executor.start_task(user_goal, plan)
        guide_state = 'execution'

        # 获取第一步
        current_step = executor.get_current_step()
        if current_step:
            response = f"开始执行任务。\n\n步骤{current_step['step']}：{current_step['action']}\n对象：{current_step['target']}\n详情：{current_step['detail']}\n预期：{current_step['expected_result']}\n\n点击【继续】进入下一步，或点击【标亮】高亮当前操作区域。"
        else:
            response = "任务计划已生成。"

        return jsonify({"response": response, "state": "execution"})

    return jsonify({"response": "请重新开始。"})

@app.route('/api/continue', methods=['POST'])
def handle_continue():
    """处理继续按钮"""
    if not executor.current_plan:
        return jsonify({"response": "请先在操作指引模式输入要使用的Agent名称。"})

    result = executor.handle_feedback("next")

    if result['status'] == 'completed':
        return jsonify({"response": "任务完成！"})

    current_step = executor.get_current_step()
    if current_step:
        response = f"步骤{current_step['step']}：{current_step['action']}\n对象：{current_step['target']}\n详情：{current_step['detail']}\n预期：{current_step['expected_result']}"
        return jsonify({"response": response})

    return jsonify({"response": "继续执行中..."})

@app.route('/api/error', methods=['POST'])
def handle_error():
    """处理错误按钮"""
    if not executor.current_plan:
        return jsonify({"response": "请先在操作指引模式输入要使用的Agent名称。"})

    result = executor.handle_feedback("error")
    return jsonify({"response": f"已重新规划，共{len(result['new_plan']['steps'])}步"})

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """处理操作指引模式的对话（问题或质疑）"""
    if not executor.current_plan:
        return jsonify({"response": "请先在操作指引模式输入要使用的Agent名称。"})

    data = request.json
    message = data.get('message', '')

    # 使用LLM判断是问题还是质疑
    router_prompt = f"""判断用户的话是"疑问"还是"质疑"。

用户的话：{message}

- 疑问：用户不理解某个步骤，想要解释说明
- 质疑：用户认为某个步骤不正确，提出异议

只输出一个词："question" 或 "challenge"。"""

    router_response = agent_recommender.client.chat.completions.create(
        model="DeepSeek-V3.2-Fast",
        messages=[{"role": "user", "content": router_prompt}],
        temperature=0.1
    )

    intent = router_response.choices[0].message.content.strip().lower()

    if "question" in intent:
        result = executor.handle_feedback("question", message)
        return jsonify({"response": result['answer']})
    else:
        result = executor.handle_feedback("challenge", message)
        if result['status'] == 'replanned':
            return jsonify({"response": f"已重新规划：{result['explanation']}"})
        else:
            return jsonify({"response": f"步骤正确：{result['explanation']}"})

@app.route('/api/mark', methods=['POST'])
def handle_mark():
    """处理标亮按钮"""
    if not executor.current_plan:
        return jsonify({"response": "请先在操作指引模式输入要使用的Agent名称。"})

    result = executor.handle_feedback("highlight", save_highlight=False)

    if result['status'] == 'highlighted':
        return jsonify({"response": f"已高亮：{result.get('description', '')}\n坐标：{result['coordinates']}"})

    return jsonify({"response": f"错误：{result.get('message', '无法定位操作区域')}"})

if __name__ == '__main__':
    init_system()
    app.run(host='0.0.0.0', port=7860, debug=True)
