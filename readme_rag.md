# 知识库智能体系统

多Agent协作系统，从应用官网抓取文档，理解多模态内容（文字、图像、视频），构建结构化知识库支持RAG检索。

## 安装

```bash
cd d:/A_star_gent
pip install -r requirements.txt
```

## 配置

编辑 `config.py` 设置 ModelScope API Key：
```python
MODELSCOPE_API_KEY = "你的API Key"
```

## 使用

### 构建知识库
```bash
python main.py build --url https://docs.example.com --app_name "应用名"
```

### 检索知识库
```bash
python main.py search --query "如何安装" --app_name "应用名"
python main.py search --query "配置方法" --top_k 10
```

## 系统架构

### 5个Agent

| Agent | 职责 |
|-------|------|
| DocSearchAgent | 在官网搜索文档链接，失败则用搜索引擎 |
| ContentCrawlerAgent | 抓取网页内容（文字、图片、视频URL） |
| VideoUnderstandAgent | 使用qwen3-omni模型理解视频内容 |
| KnowledgeStructureAgent | 将内容组织成章节结构 |
| KnowledgeStoreAgent | 存入ChromaDB向量库，支持RAG检索 |

### 工作流程

```
官网URL → DocSearchAgent → ContentCrawlerAgent → VideoUnderstandAgent
                                                        ↓
                    RAG检索 ← KnowledgeStoreAgent ← KnowledgeStructureAgent
```

## 视频理解

使用阿里云 qwen3-omni-flash 模型直接处理视频，支持：
- 画面内容理解
- 语音旁白识别
- 文字提取

输出格式：
```json
{
  "title": "视频标题",
  "overview": "内容概述",
  "timeline": [{"time": "0:00-1:00", "content": "描述"}],
  "steps": [{"step": 1, "action": "操作", "detail": "说明"}],
  "key_points": ["知识点"],
  "tips": ["注意事项"],
  "summary": "核心总结"
}
```

## 数据存储

- 知识结构：`data/knowledge_base/{app_name}_structure.json`
- 向量数据库：`data/chroma_db/`

## 项目结构

```
d:/A_star_gent/
├── config.py           # 配置
├── main.py             # 入口
├── requirements.txt
├── agents/
│   ├── doc_search.py
│   ├── content_crawler.py
│   ├── video_understand.py
│   ├── knowledge_structure.py
│   └── knowledge_store.py
└── tools/
    ├── llm_tools.py
    └── web_tools.py
```
