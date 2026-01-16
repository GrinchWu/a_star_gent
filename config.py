# 配置文件
import os

# ModelScope API配置
MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY", "<MODELSCOPE_TOKEN>")
MODELSCOPE_BASE_URL = "https://api-inference.modelscope.cn/v1"

# 模型配置
VL_MODEL = "Qwen/Qwen3-VL-235B-A22B-Instruct"  # 多模态模型
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"    # Embedding模型

# 知识库配置
KNOWLEDGE_BASE_DIR = "d:/A_star_gent/data/knowledge_base"
CHROMA_DB_DIR = "d:/A_star_gent/data/chroma_db"

# 视频处理配置
VIDEO_FRAME_INTERVAL = 2  # 每2秒提取一帧
MAX_FRAMES_PER_VIDEO = 30  # 每个视频最多提取30帧

# 搜索配置
MAX_SEARCH_RESULTS = 10
