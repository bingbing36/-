"""
AI 保险问询助手 - Elasticsearch 增强版
使用Elasticsearch作为RAG检索后端，提供更高效的文档索引和检索
"""

import pprint
import urllib.parse
import json5
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.gui import WebUI
import os
import sys

# ============================================================================
# 步骤 1：添加自定义工具
# ============================================================================

@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    """AI 绘画（图像生成）服务"""
    description = 'AI 绘画（图像生成）服务，输入文本描述，返回基于文本信息绘制的图像 URL。'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '期望的图像内容的详细描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json5.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


# ============================================================================
# 步骤 2：配置 LLM
# ============================================================================

llm_cfg = {
    'model': 'deepseek-v3',
    'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv('DASHSCOPE_API_KEY'),
    'generate_cfg': {
        'top_p': 0.8
    }
}

# ============================================================================
# 步骤 3：系统提示词
# ============================================================================

system_instruction = '''你是一个乐于助人的AI助手。
在收到用户的请求后，你应该：
- 首先通过Elasticsearch检索相关的保险文档
- 然后基于检索到的内容提供准确回答
- 必要时可以绘制图像或执行代码进行分析
- 用中文回复用户
'''

# ============================================================================
# 步骤 4：加载文档
# ============================================================================

file_dir = os.path.join('./', 'docs')
files = []
if os.path.exists(file_dir):
    for file in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file)
        if os.path.isfile(file_path):
            files.append(file_path)

print('待索引文件:', files)

# ============================================================================
# 步骤 5：配置 RAG 和 Elasticsearch
# ============================================================================

# Elasticsearch 配置（支持 ES 8.x+ HTTPS + 认证）
rag_cfg = {
    # 基本RAG配置
    'max_ref_token': 4000,              # 最大参考token数
    'parser_page_size': 500,            # 文档解析页大小
    'rag_keygen_strategy': 'SplitQueryThenGenKeyword',  # 关键词生成策略
    
    # Elasticsearch 配置（支持HTTPS和认证）
    'use_elasticsearch': True,           # 启用Elasticsearch
    'es_hosts': ['localhost:9200'],     # ES服务器地址列表
    'es_index': 'insurance_knowledge',   # ES索引名称
    'embedding_dim': 768,                # 向量维度
    
    # Elasticsearch 认证（ES 8.x+ 需要）
    'es_username': 'elastic',            # ES用户名
    'es_password': 'cKyMr-jgTTeFGAHG9yHo',  # ES密码
    'use_https': True,                   # 使用HTTPS（ES 9.x默认）
    'verify_certs': False,               # 不验证SSL证书（自签名证书）
}

tools = ['my_image_gen', 'code_interpreter']

# ============================================================================
# 步骤 6：初始化代理
# ============================================================================

def init_agent_service():
    """初始化智能体服务"""
    print("\n" + "="*50)
    print("初始化 AI 保险问询助手（Elasticsearch 版）")
    print("="*50)
    
    # 检查 Elasticsearch 连接
    print("\n检查 Elasticsearch 连接...")
    try:
        from qwen_agent.tools.es_manager import ESManager
        es_manager = ESManager(
            hosts=rag_cfg['es_hosts'],
            index_name=rag_cfg['es_index'],
            username=rag_cfg.get('es_username'),
            password=rag_cfg.get('es_password'),
            use_https=rag_cfg.get('use_https', True),
            verify_certs=rag_cfg.get('verify_certs', False)
        )
        
        # 尝试获取统计信息
        stats = es_manager.get_stats()
        print(f"✓ Elasticsearch 连接成功")
        print(f"  索引名称: {stats.get('index_name')}")
        print(f"  文档数量: {stats.get('doc_count')}")
        print(f"  存储大小: {stats.get('store_size')} bytes")
        
    except Exception as e:
        print(f"✗ Elasticsearch 连接失败: {e}")
        print("  请确保 Elasticsearch 服务已启动")
        print("  启动命令: docker run -d -p 9200:9200 -e discovery.type=single-node docker.elastic.co/elasticsearch/elasticsearch:8.x.x")
        sys.exit(1)
    
    # 创建智能体
    print("\n创建智能体实例...")
    bot = Assistant(
        name='AI问答助手',
        llm=llm_cfg,
        system_message=system_instruction,
        function_list=tools,
        files=files,
        rag_cfg=rag_cfg
    )
    
    print("✓ 智能体初始化完成\n")
    return bot


# ============================================================================
# 步骤 7：初始化 Elasticsearch 索引
# ============================================================================

def init_elasticsearch_index():
    """初始化 Elasticsearch 索引"""
    print("\n初始化 Elasticsearch 索引...")
    
    try:
        from qwen_agent.tools.es_manager import ESManager
        
        es_manager = ESManager(
            hosts=rag_cfg['es_hosts'],
            index_name=rag_cfg['es_index'],
            embedding_dim=rag_cfg['embedding_dim'],
            username=rag_cfg.get('es_username'),
            password=rag_cfg.get('es_password'),
            use_https=rag_cfg.get('use_https', True),
            verify_certs=rag_cfg.get('verify_certs', False)
        )
        
        # 创建索引（如果不存在）
        if es_manager.create_index(force_recreate=False):
            print("✓ 索引创建/加载成功")
        
        return es_manager
        
    except Exception as e:
        print(f"✗ 索引创建失败: {e}")
        return None


# ============================================================================
# 步骤 8：预加载文档到 Elasticsearch
# ============================================================================

def preload_documents_to_es(es_manager):
    """将文档预加载到 Elasticsearch"""
    if not es_manager or not files:
        return
    
    print(f"\n预加载 {len(files)} 个文档到 Elasticsearch...")
    
    try:
        from qwen_agent.tools.es_doc_parser import ESDocParser
        
        parser = ESDocParser({
            'max_ref_token': rag_cfg['max_ref_token'],
            'parser_page_size': rag_cfg['parser_page_size'],
            'es_hosts': rag_cfg['es_hosts'],
            'es_index': rag_cfg['es_index'],
            'es_username': rag_cfg.get('es_username'),
            'es_password': rag_cfg.get('es_password'),
            'use_https': rag_cfg.get('use_https', True),
            'verify_certs': rag_cfg.get('verify_certs', False)
        })
        
        for file_path in files:
            print(f"  处理: {os.path.basename(file_path)}")
            result = parser.call({'file_path': file_path})
            
            if result['status'] == 'success':
                print(f"    ✓ 已索引 {result['chunks_count']} 个文档片段")
            elif result['status'] == 'already_indexed':
                print(f"    ℹ 文件已在索引中")
            else:
                print(f"    ✗ 处理失败: {result['message']}")
        
        # 显示最终统计
        stats = es_manager.get_stats()
        print(f"\n索引统计:")
        print(f"  总文档数: {stats.get('doc_count')}")
        print(f"  索引大小: {stats.get('store_size')} bytes")
        
    except Exception as e:
        print(f"✗ 预加载文档失败: {e}")


# ============================================================================
# 步骤 9：终端交互模式
# ============================================================================

def app_terminal():
    """终端模式 - 交互式对话"""
    try:
        print("\n正在启动终端模式...")
        bot = init_agent_service()
        
        messages = []
        
        print("\n欢迎使用 AI 保险问询助手（Elasticsearch 版）！")
        print("==================================================")
        print("- 本助手使用 Elasticsearch 进行高效的文档检索")
        print("- 输入 'exit' 或 'quit' 退出程序")
        print("- 输入 'help' 查看示例问题")
        print("- 输入 'stats' 查看索引统计信息\n")
        
        while True:
            query = input("您的问题：").strip()
            
            if query.lower() == 'exit' or query.lower() == 'quit':
                print("感谢使用，再见！")
                break
            
            if query.lower() == 'stats':
                # 显示统计信息
                try:
                    from qwen_agent.tools.es_manager import ESManager
                    es_manager = ESManager(
                        hosts=rag_cfg['es_hosts'],
                        index_name=rag_cfg['es_index'],
                        username=rag_cfg.get('es_username'),
                        password=rag_cfg.get('es_password'),
                        use_https=rag_cfg.get('use_https', True),
                        verify_certs=rag_cfg.get('verify_certs', False)
                    )
                    stats = es_manager.get_stats()
                    print(f"\n索引统计:")
                    print(f"  索引名: {stats.get('index_name')}")
                    print(f"  文档数: {stats.get('doc_count')}")
                    print(f"  大小: {stats.get('store_size')} bytes\n")
                except:
                    pass
                continue
            
            if query.lower() == 'help':
                print("\n示例问题：")
                print("  - 介绍下雇主责任险")
                print("  - 平安商业综合责任保险的保障范围是什么？")
                print("  - 企业团体综合意外险包含哪些保障？")
                print("  - 施工保险有哪些主要特点？\n")
                continue
            
            if not query:
                print("请输入有效的问题\n")
                continue
            
            # 添加用户问题到历史
            messages.append({'role': 'user', 'content': query})
            
            print("\nAI 助手：", end='', flush=True)
            
            response = []
            for response in bot.run(messages=messages):
                if response:
                    print(response[0]['content'], end='', flush=True)
            
            print("\n")
            
            # 添加助手回复到历史
            if response:
                messages.extend(response)
    
    except KeyboardInterrupt:
        print("\n\n程序已中断")
    except Exception as e:
        print(f"处理请求时出错: {str(e)}")


# ============================================================================
# 步骤 10：Web 图形界面模式
# ============================================================================

def app_gui():
    """Web 图形界面模式"""
    try:
        print("\n正在启动 Web 界面...")
        bot = init_agent_service()
        
        chatbot_config = {
            'prompt.suggestions': [
                '介绍下雇主责任险',
                '平安商业综合责任保险的保障范围是什么？',
                '企业团体综合意外险包含哪些保障？',
                '施工保险有哪些主要特点？',
                '财产一切险的保障内容',
                '雇主安心保有什么优势？'
            ]
        }
        
        print("Web 界面准备就绪，正在启动服务...")
        print("http://localhost:7860\n")
        
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run()
        
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 API Key 配置")


# ============================================================================
# 步骤 11：主程序入口
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AI 保险问询助手 - Elasticsearch 版')
    parser.add_argument('--mode', type=str, default='gui', choices=['gui', 'terminal'],
                       help='运行模式：gui (图形界面) 或 terminal (终端)')
    parser.add_argument('--init-es', action='store_true', help='初始化并预加载文档到 Elasticsearch')
    
    args = parser.parse_args()
    
    # 初始化 Elasticsearch 索引
    if args.init_es or True:  # 默认初始化
        es_manager = init_elasticsearch_index()
        if es_manager:
            preload_documents_to_es(es_manager)
    
    # 启动应用
    if args.mode == 'terminal':
        app_terminal()
    else:
        app_gui()
