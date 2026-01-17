"""执行系统主入口"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_planner.config import OMNIPARSER_DIR
from task_planner.executor_agent import ExecutorAgent
from task_planner.planner_agent import TaskPlannerAgent
from task_planner.screen_analyzer import ScreenAnalyzer

def main():
    print("=== 任务执行系统 ===\n")

    # 1. 初始化
    executor = ExecutorAgent(OMNIPARSER_DIR)
    planner = TaskPlannerAgent()
    screen_analyzer = ScreenAnalyzer(OMNIPARSER_DIR)

    # 2. 推荐功能
    print("正在分析应用功能...")
    app_docs = executor.knowledge_base.search("应用功能介绍", top_k=5)
    suggestions = planner.suggest_tasks(app_docs)

    print("\n我可以带你实现以下功能：")
    print(suggestions)
    user_goal = input("\n请选择或输入你想实现的功能：")

    # 3. 生成初始计划
    print("\n分析中...")
    screen_info = screen_analyzer.analyze("llm")
    rag_docs = executor.knowledge_base.search(user_goal, top_k=3)

    print("生成计划...")
    plan = planner.plan(user_goal, screen_info, rag_docs)

    print(f"\n=== 任务计划 ===")
    print(f"当前应用：{plan.get('current_app', '未知')}")
    print(f"目标应用：{plan.get('target_app', '未知')}\n")

    # 4. 开始执行
    executor.start_task(user_goal, plan)

    # 5. 执行循环
    while True:
        current_step = executor.get_current_step()
        if not current_step:
            print("\n任务完成！")
            break

        print(f"\n步骤{current_step['step']}：{current_step['action']}")
        print(f"  对象：{current_step['target']}")
        print(f"  详情：{current_step['detail']}")
        print(f"  预期：{current_step['expected_result']}")
        print(f"  置信度：{current_step['confidence']}")

        print("\n请选择操作：")
        print("1. 下一步")
        print("2. 执行错误（误操作）")
        print("3. 对此步有疑问")
        print("4. 质疑这一步")
        print("5. 高亮这一步")

        choice = input("选择 (1-5)：").strip()

        if choice == "1":
            result = executor.handle_feedback("next")
            if result['status'] == 'completed':
                print("\n任务完成！")
                break
        elif choice == "2":
            result = executor.handle_feedback("error")
            print(f"\n已重新规划，共{len(result['new_plan']['steps'])}步")
        elif choice == "3":
            question = input("请输入你的问题：")
            result = executor.handle_feedback("question", question)
            print(f"\n回答：{result['answer']}")
        elif choice == "4":
            challenge = input("请输入你的质疑：")
            result = executor.handle_feedback("challenge", challenge)
            if result['status'] == 'replanned':
                print(f"\n已重新规划：{result['explanation']}")
            else:
                print(f"\n步骤正确：{result['explanation']}")
        elif choice == "5":
            save_choice = input("是否保存高亮信息到文件？(y/n)：").strip().lower()
            save_to_file = save_choice == 'y'
            result = executor.handle_feedback("highlight", save_highlight=save_to_file)
            if result['status'] == 'highlighted':
                print(f"\n已高亮：{result.get('description', '')}")
                print(f"坐标：{result['coordinates']}")
                if save_to_file:
                    print("高亮信息已保存到文件")
            else:
                print(f"\n错误：{result.get('message', '无法定位操作区域')}")

if __name__ == "__main__":
    main()
