"""AI Agent推荐系统"""
from openai import OpenAI

class AgentRecommender:
    """基于RAG知识库的Agent推荐器"""

    def __init__(self, knowledge_base):
        self.client = OpenAI(
            base_url="https://www.sophnet.com/api/open-apis/v1",
            api_key="CL9TPTG2Qro1oto8pSyBq6bQpXFCRs8g-Yl2d7nuElQBr2HtqkA19yu7wC1Zy6DGWOe4BELfLoZXUfuhD3yIoQ"
        )
        self.knowledge_base = knowledge_base
        self.system_prompt = """# 角色
你是一个能理解用户角色身份和用户任务、并且了解市面上的AI Agent的AI达人，你非常善于拆解用户的任务，用AI Agent产品来提效你的日常工作。你的职责是基于用户的身份和特定的任务，给他推荐你知识库里已有的智能体，并且推送给他以帮助他完成任务。

# 你的能力
1、你理解用户的身份，理解他的日常工作内容和需求。
2、你拆解用户的任务，拆解成多个步骤，并且针对每个步骤，推荐你知识库里的特定的Agent。
3、对于针对每个步骤的特定推荐，你需要根据知识库，输出：该agent的名字，该agent官网的网址，该agent的简介，该agent的功能，该功能如何契合用户的任务步骤、并且分析是如何提效。
4、如果用户有多轮对话、继续询问该agent的详细信息，你要继续给他用通俗易懂的语言分析推荐该agent，解答用户的相关疑问。
5、如果用户想要使用任务规划指引相关的内容，请明确告诉用户："请点击下方的【操作指引】按钮，然后输入您想要帮忙引导的Agent名字，我会为您提供详细的操作步骤。"

# 严格要求
1、你只能根据知识库进行agent的挑选，千万不能推荐一些知识库里没有的agent。
2、在推荐完成的末尾，你要输出一句："如果您感兴趣，请我来引导您使用吧~"
3、你的回复语气要耐心、善解人意，用户是不懂ai agent的非技术人员纯小白，比如文科生和金融行政法律从业者。"""

    def recommend(self, user_identity, user_task):
        """根据用户身份和任务推荐Agent"""
        # 从知识库检索相关Agent信息
        rag_docs = self.knowledge_base.search(f"{user_identity} {user_task}", top_k=5)

        # 构建上下文
        context = "\n\n".join([f"Agent信息：{doc}" for doc in rag_docs])

        # 调用LLM进行推荐
        response = self.client.chat.completions.create(
            model="DeepSeek-V3.2-Fast",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"用户身份：{user_identity}\n用户任务：{user_task}\n\n知识库中的Agent信息：\n{context}"}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    def chat(self, user_message, conversation_history=None):
        """多轮对话功能"""
        if conversation_history is None:
            conversation_history = []

        # 检索相关知识
        rag_docs = self.knowledge_base.search(user_message, top_k=3)
        context = "\n\n".join([f"Agent信息：{doc}" for doc in rag_docs])

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": f"{user_message}\n\n相关知识：\n{context}"})

        response = self.client.chat.completions.create(
            model="DeepSeek-V3.2-Fast",
            messages=messages,
            temperature=0.7
        )

        return response.choices[0].message.content
