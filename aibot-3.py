"""
AI 保险问询助手 - Elasticsearch + Tavily 网络搜索增强版
使用Elasticsearch作为RAG检索后端，同时集成Tavily网络搜索获取最新信息
"""

import pprint
import urllib.parse
import json5
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.gui import WebUI
import os
import sys
import requests
import json
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

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


@register_tool('tavily_search')
class TavilySearchTool(BaseTool):
    """
    Tavily 网络搜索工具
    用于搜索网络上的最新信息、新闻、政策等，补充本地RAG知识库
    """
    description = '''使用Tavily搜索引擎搜索网络上的信息。用于获取：
    - 最新的保险政策和法规
    - 实时的保险产品信息
    - 行业动态和新闻
    - 用户评价和口碑
    
    返回包含标题、摘要、源网址和发布日期的搜索结果。'''
    
    parameters = [
        {
            'name': 'query',
            'type': 'string',
            'description': '搜索查询词，可以是中文或英文',
            'required': True
        },
        {
            'name': 'topic',
            'type': 'string',
            'description': '搜索主题：general(通用搜索), news(新闻), financial(金融), research(研究)，默认为general',
            'required': False
        },
        {
            'name': 'include_raw_content',
            'type': 'boolean',
            'description': '是否包含原始网页内容，默认为False（仅返回摘要）',
            'required': False
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        """
        调用Tavily API获取搜索结果
        """
        try:
            args = json5.loads(params)
            query = args.get('query', '')
            topic = args.get('topic', 'general')
            include_raw_content = args.get('include_raw_content', False)
            
            if not query:
                return json5.dumps({
                    'success': False,
                    'error': '搜索查询不能为空'
                }, ensure_ascii=False)
            
            # 获取 Tavily API Key
            api_key = os.getenv('TAVILY_API_KEY')
            if not api_key:
                return json5.dumps({
                    'success': False,
                    'error': '未配置TAVILY_API_KEY。\n配置方式：\n1. 设置环境变量: $env:TAVILY_API_KEY = "your_key"\n2. 在当前目录创建.env文件: TAVILY_API_KEY=your_key\n获取API Key: https://tavily.com/'
                }, ensure_ascii=False)
            
            # 调用 Tavily API
            url = "https://api.tavily.com/search"
            
            payload = {
                "api_key": api_key,
                "query": query,
                "topic": topic,
                "include_raw_content": include_raw_content,
                "max_results": 5,  # 最多返回5条结果
                "include_images": False,
                "include_domains": []  # 不限制域名
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                return json5.dumps({
                    'success': False,
                    'error': f'Tavily API 错误: {response.status_code}'
                }, ensure_ascii=False)
            
            result = response.json()
            
            # 格式化搜索结果
            if not result.get('results'):
                return json5.dumps({
                    'success': True,
                    'results': [],
                    'message': f'未找到与 "{query}" 相关的网络结果'
                }, ensure_ascii=False)
            
            formatted_results = []
            for item in result.get('results', []):
                formatted_item = {
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('snippet', ''),
                    'published_date': item.get('published_date', ''),
                }
                if include_raw_content:
                    formatted_item['content'] = item.get('content', '')
                formatted_results.append(formatted_item)
            
            return json5.dumps({
                'success': True,
                'query': query,
                'total_results': len(formatted_results),
                'results': formatted_results
            }, ensure_ascii=False)
            
        except Exception as e:
            return json5.dumps({
                'success': False,
                'error': f'搜索失败: {str(e)}'
            }, ensure_ascii=False)


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

system_instruction = '''你是一个专业的AI保险问询助手。

在回答用户问题时，你应该：

【信息来源】
1. 优先使用Elasticsearch中存储的本地保险文档（通过RAG检索）
2. 对于本地知识库中没有的信息，使用Tavily网络搜索获取最新信息
3. 必要时结合两个信息源进行综合回答

【回答原则】
- 对本地文档的内容：明确指出出处（如"平安企业团体综合意外险条款"）
- 对网络搜索的内容：注明来源网址和发布日期
- 优先使用本地文档中的准确信息
- 对于可能发生变化的信息（如保险产品、政策），注明查询时间

【工具使用】
- tavily_search: 搜索最新的保险产品、政策、新闻
- code_interpreter: 执行代码进行数据分析或复杂计算
- my_image_gen: 生成相关图像

【用户交互】
- 用中文回复用户
- 结构清晰，使用列表和表格展示信息
- 如无把握，明确说明信息的不确定性
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

# ============================================================================
# 步骤 6：配置工具列表
# ============================================================================

tools = ['my_image_gen', 'tavily_search', 'code_interpreter']

# ============================================================================
# 步骤 7：初始化代理
# ============================================================================

def init_agent_service():
    """初始化智能体服务"""
    print("\n" + "="*60)
    print("初始化 AI 保险问询助手（Elasticsearch + Tavily 增强版）")
    print("="*60)
    
    # 检查 Elasticsearch 连接
    print("\n[1/3] 检查 Elasticsearch 连接...")
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
        sys.exit(1)
    
    # 检查 Tavily API Key
    print("\n[2/3] 检查 Tavily API Key...")
    if os.getenv('TAVILY_API_KEY'):
        print("✓ Tavily API Key 已配置")
        print("  功能: 支持网络搜索获取最新信息")
    else:
        print("⚠ Tavily API Key 未配置")
        print("  网络搜索功能将不可用")
        print("  获取方式: https://tavily.com/")
        print("  配置: set TAVILY_API_KEY=your_api_key")
    
    # 创建智能体
    print("\n[3/3] 创建智能体实例...")
    bot = Assistant(
        name='AI保险问询助手',
        llm=llm_cfg,
        system_message=system_instruction,
        function_list=tools,
        files=files,
        rag_cfg=rag_cfg
    )
    
    print("✓ 智能体初始化完成\n")
    return bot


# ============================================================================
# 步骤 8：初始化 Elasticsearch 索引
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
# 步骤 9：预加载文档到 Elasticsearch
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
# 步骤 10：终端交互模式
# ============================================================================

def app_terminal():
    """终端模式 - 交互式对话"""
    try:
        print("\n正在启动终端模式...")
        bot = init_agent_service()
        
        messages = []
        
        print("\n欢迎使用 AI 保险问询助手（Elasticsearch + Tavily 增强版）！")
        print("="*60)
        print("功能特性：")
        print("  - 本地RAG检索：从Elasticsearch索引中获取保险文档")
        print("  - 网络搜索：使用Tavily搜索最新的保险政策和信息")
        print("  - 代码执行：进行数据分析和复杂计算")
        print("  - 图像生成：根据描述生成相关图像")
        print("\n命令说明：")
        print("  - 输入 'exit' 或 'quit' 退出程序")
        print("  - 输入 'help' 查看示例问题")
        print("  - 输入 'stats' 查看索引统计信息")
        print("  - 输入 'tools' 查看可用工具\n")
        
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
                    print(f"\n【Elasticsearch 索引统计】")
                    print(f"  索引名: {stats.get('index_name')}")
                    print(f"  文档数: {stats.get('doc_count')}")
                    print(f"  大小: {stats.get('store_size')} bytes\n")
                except:
                    pass
                continue
            
            if query.lower() == 'tools':
                print("\n【可用工具】")
                print("  1. tavily_search - 搜索网络最新信息")
                print("     用途：获取最新保险政策、产品信息、行业新闻")
                print("  2. my_image_gen - AI绘画")
                print("     用途：根据描述生成相关图像")
                print("  3. code_interpreter - 代码执行")
                print("     用途：数据分析、复杂计算\n")
                continue
            
            if query.lower() == 'help':
                print("\n【示例问题】")
                print("  本地知识库相关：")
                print("    - 介绍下雇主责任险")
                print("    - 平安商业综合责任保险的保障范围是什么？")
                print("    - 企业团体综合意外险包含哪些保障？")
                print("\n  网络搜索相关：")
                print("    - 2024年中国保险行业有什么新政策？")
                print("    - 最新的健康保险产品有哪些？")
                print("    - 保险理赔流程和时间是怎样的？\n")
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
# 步骤 11：Web 图形界面模式
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
                '2024年中国保险行业最新动态',
                '健康保险和医疗保险有什么区别？',
                '保险理赔流程通常需要多久？',
                '企业该如何选择合适的财产保险？'
            ]
        }
        
        print("Web 界面准备就绪，正在启动服务...")
        print("访问地址: http://localhost:7860\n")
        
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run()
        
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 API Key 配置")


# ============================================================================
# 步骤 12：主程序入口
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='AI 保险问询助手 - Elasticsearch + Tavily 增强版'
    )
    parser.add_argument(
        '--mode', 
        type=str, 
        default='gui', 
        choices=['gui', 'terminal'],
        help='运行模式：gui (图形界面) 或 terminal (终端)'
    )
    parser.add_argument(
        '--init-es', 
        action='store_true', 
        help='初始化并预加载文档到 Elasticsearch'
    )
    
    args = parser.parse_args()
    
    # 检查必要的API Key
    print("\n【环境检查】")
    if os.getenv('DASHSCOPE_API_KEY'):
        print("✓ DASHSCOPE_API_KEY 已配置")
    else:
        print("✗ DASHSCOPE_API_KEY 未配置")
        sys.exit(1)
    
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
