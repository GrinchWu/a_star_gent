"""主入口"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.builder import KnowledgeBuilder

def main():
    parser = argparse.ArgumentParser(description='知识库构建系统')
    subparsers = parser.add_subparsers(dest='command')

    build_parser = subparsers.add_parser('build', help='构建知识库')
    build_parser.add_argument('--md', required=True, help='Markdown文档路径')
    build_parser.add_argument('--app_name', required=True, help='应用名称')

    search_parser = subparsers.add_parser('search', help='检索知识库')
    search_parser.add_argument('--query', required=True, help='检索问题')
    search_parser.add_argument('--top_k', type=int, default=5, help='返回结果数')

    args = parser.parse_args()
    builder = KnowledgeBuilder()

    if args.command == 'build':
        builder.build(args.md, args.app_name)
    elif args.command == 'search':
        results = builder.search(args.query, args.top_k)
        print(f"\n检索结果 (共{len(results)}条):\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] 相关度: {1-r['distance']:.3f}")
            print(f"    标题: {r['metadata'].get('title', 'N/A')}")
            print(f"    内容: {r['content'][:200]}...")
            print()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
