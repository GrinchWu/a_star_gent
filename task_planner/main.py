"""任务规划系统主入口"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_planner.config import OMNIPARSER_DIR
from task_planner.screen_analyzer import ScreenAnalyzer
from task_planner.planner_agent import TaskPlannerAgent
from knowledge.vector_store import VectorStore

def main():
    print("=== 任务规划系统 ===\n")

    # 1. 初始化
    screen_analyzer = ScreenAnalyzer(OMNIPARSER_DIR)
    planner = TaskPlannerAgent()
    knowledge_base = VectorStore()

    # 2. 获取应用文档并推荐功能
    print("正在分析应用功能...")
    app_docs = knowledge_base.search("应用功能介绍", top_k=5)
    suggestions = planner.suggest_tasks(app_docs)

    print("\n我可以带你实现以下功能：")
    print(suggestions)
    user_goal = input("\n请选择或输入你想实现的功能：")

    # 3. 选择屏幕分析模式
    print("\n屏幕分析模式：1.大模型 2.功能定位 3.结合（推荐）")
    mode_choice = input("选择模式 (默认3)：").strip() or "3"
    mode = {"1": "llm", "2": "parser", "3": "both"}[mode_choice]

    # 4. 并行执行
    print(f"\n分析中...")
    screen_info = screen_analyzer.analyze(mode)
    rag_docs = knowledge_base.search(user_goal, top_k=3)

    # 5. 生成任务计划
    print("生成计划...")
    plan = planner.plan(user_goal, screen_info, rag_docs)

    # 6. 输出计划
    print(f"\n=== 任务计划 ===")
    print(f"当前应用：{plan.get('current_app', '未知')}")
    print(f"目标应用：{plan.get('target_app', '未知')}\n")

    for step in plan['steps']:
        print(f"步骤{step['step']}：{step['action']}")
        print(f"  对象：{step['target']}")
        print(f"  详情：{step['detail']}")
        print(f"  预期：{step['expected_result']}")
        print(f"  置信度：{step['confidence']}\n")

    if plan.get('need_feedback'):
        print(f"需要反馈：{plan['next_info_needed']}")

if __name__ == "__main__":
    main()
