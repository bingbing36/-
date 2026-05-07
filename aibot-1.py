import pprint
import urllib.parse
import json5
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.gui import WebUI
import os

# 步骤 1（可选）：添加一个名为 `my_image_gen` 的自定义工具。
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    # `description` 用于告诉智能体该工具的功能。
    description = 'AI 绘画（图像生成）服务，输入文本描述，返回基于文本信息绘制的图像 URL。'
    # `parameters` 告诉智能体该工具有哪些输入参数。
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '期望的图像内容的详细描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` 是由 LLM 智能体生成的参数。
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json5.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


# 步骤 2：配置您所使用的 LLM。
llm_cfg = {
    # 使用 DashScope 提供的模型服务：
    'model': 'deepseek-v3',
    'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv('DASHSCOPE_API_KEY'),  # 从环境变量获取API Key
    'generate_cfg': {
        'top_p': 0.8
    }
}

# 步骤 3：创建一个智能体。这里我们以 `Assistant` 智能体为例，它能够使用工具并读取文件。
system_instruction = '''你是一个乐于助人的AI助手。
在收到用户的请求后，你应该：
- 首先绘制一幅图像，得到图像的url，
- 然后运行代码`request.get`以下载该图像的url，
- 最后从给定的文档中选择一个图像操作进行图像处理。
用 `plt.show()` 展示图像。
你总是用中文回复用户。'''

tools = ['my_image_gen', 'code_interpreter']  # `code_interpreter` 是框架自带的工具，用于执行代码。my_image_gen是自己定义的。

# 获取文件夹下所有文件
file_dir = os.path.join('./', 'docs')  # 对文件夹下的文件做一个拼接，本质上是把这些数据放到一个叫files的数组中
files = []
if os.path.exists(file_dir):
    # 遍历目录下的所有文件
    for file in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file)
        if os.path.isfile(file_path):  # 确保是文件而不是目录
            files.append(file_path)
print('files=', files)


def init_agent_service():
    """初始化智能体服务"""
    # 智能体开发的核心所在，创建智能体实例，并将配置、系统指令、工具列表和文件列表传入。
    bot = Assistant(name='AI问答助手',
                    llm=llm_cfg,
                    system_message=system_instruction,  # 人设
                    function_list=tools,
                    files=files)  # 知识库
    return bot


def app_terminal():
    """终端模式，支持多轮对话"""
    try:
        print("正在启动终端模式...")
        bot = init_agent_service()
        
        # 步骤 4：作为聊天机器人运行智能体。
        messages = []  # 这里储存聊天历史。
        
        print("\n欢迎使用 AI 保险问询助手！")
        print("输入 'exit' 或 'quit' 退出程序\n")
        
        while True:
            query = input("您的问题：").strip()
            
            if query.lower() in ['exit', 'quit']:
                print("感谢使用，再见！")
                break
            
            if not query:
                print("请输入有效的问题\n")
                continue
            
            # 将用户请求添加到聊天历史。
            messages.append({'role': 'user', 'content': query})
            
            response = []
            current_index = 0
            
            print("\nAI 助手：", end='')
            
            for response in bot.run(messages=messages):
                if current_index == 0:
                    # 尝试获取并打印召回的文档内容
                    if hasattr(bot, 'retriever') and bot.retriever:
                        print("\n===== 召回的文档内容 =====")
                        retrieved_docs = bot.retriever.retrieve(query)
                        if retrieved_docs:
                            for i, doc in enumerate(retrieved_docs):
                                print(f"\n文档片段 {i+1}:")
                                print(f"内容: {doc.page_content}")
                                print(f"元数据: {doc.metadata}")
                        else:
                            print("没有召回任何文档内容")
                        print("===========================\n")

                current_response = response[0]['content'][current_index:]
                current_index = len(response[0]['content'])
                print(current_response, end='')
            
            print("\n")
            
            # 将机器人的回应添加到聊天历史。
            if response:
                messages.extend(response)
                
    except Exception as e:
        print(f"处理请求时出错: {str(e)}")


def app_gui():
    """图形界面模式，提供 Web 图形界面"""
    try:
        print("正在启动 Web 界面...")
        # 初始化助手
        bot = init_agent_service()
        
        # 配置聊天界面，列举典型保险问询
        chatbot_config = {
            'prompt.suggestions': [
                '介绍下雇主责任险',
                '平安商业综合责任保险的保障范围是什么？',
                '企业团体综合意外险包含哪些保障？',
                '施工保险有哪些主要特点？',
                '财产一切险的保障内容'
            ]
        }
        
        print("Web 界面准备就绪，正在启动服务...")
        # 启动 Web 界面
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run()
        
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 API Key 配置")


if __name__ == '__main__':
    # 运行模式选择：图形界面模式（默认）
    app_gui()
    # 如需使用终端模式，请使用以下代码：
    # app_terminal()
