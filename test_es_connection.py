"""
Elasticsearch 连接测试工具
==========================

用于测试和验证 Elasticsearch 连接配置

"""

import sys
import os
from typing import Dict, Optional, Tuple

def test_elasticsearch_connection(config: Dict) -> Tuple[bool, str]:
    """测试 Elasticsearch 连接
    
    Args:
        config: Elasticsearch 配置字典
        
    Returns:
        (成功/失败, 消息)
    """
    try:
        from elasticsearch import Elasticsearch
        from elasticsearch.exceptions import ConnectionError, AuthenticationError
        
        # 解析配置
        hosts = config.get('es_hosts', ['localhost:9200'])
        index_name = config.get('es_index', 'knowledge_base')
        username = config.get('es_username')
        password = config.get('es_password')
        use_https = config.get('use_https', True)
        verify_certs = config.get('verify_certs', False)
        
        # 构建 URL
        protocol = "https" if use_https else "http"
        es_urls = []
        for host in hosts:
            if "://" in host:
                es_urls.append(host)
            else:
                es_urls.append(f"{protocol}://{host}")
        
        print("📋 连接配置：")
        print(f"  URLs: {es_urls}")
        print(f"  协议: {'HTTPS' if use_https else 'HTTP'}")
        print(f"  验证证书: {verify_certs}")
        print(f"  用户名: {username if username else '(无)'}")
        print()
        
        # 创建连接参数
        kwargs = {"verify_certs": verify_certs}
        if username and password:
            kwargs["basic_auth"] = (username, password)
            print("🔐 使用认证连接...")
        else:
            print("⚠️  无认证信息，尝试匿名连接...")
        
        # 创建客户端
        print("🔗 连接中...")
        client = Elasticsearch(es_urls, **kwargs)
        
        # 测试 ping
        if client.ping():
            print("✅ Ping 成功！")
            
            # 获取集群信息
            info = client.info()
            cluster_name = info.get('cluster_name', 'unknown')
            version = info.get('version', {}).get('number', 'unknown')
            
            print(f"\n📊 集群信息：")
            print(f"  集群名: {cluster_name}")
            print(f"  版本: {version}")
            
            # 获取索引信息
            indices = client.indices.get_alias(index="*")
            index_count = len(indices)
            print(f"  索引数: {index_count}")
            
            # 检查目标索引
            if client.indices.exists(index=index_name):
                count = client.count(index=index_name)
                doc_count = count.get('count', 0)
                print(f"  目标索引: {index_name} (文档数: {doc_count})")
            else:
                print(f"  目标索引: {index_name} (不存在)")
            
            return True, "✅ 连接成功！"
        
        else:
            return False, "❌ Ping 失败"
    
    except AuthenticationError as e:
        return False, f"❌ 认证失败: {e}\n检查用户名和密码"
    except ConnectionError as e:
        return False, f"❌ 连接失败: {e}\n检查服务器是否运行"
    except ImportError:
        return False, "❌ 缺少 elasticsearch 库: pip install elasticsearch"
    except Exception as e:
        return False, f"❌ 错误: {e}"


def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         Elasticsearch 连接测试工具                             ║
╚════════════════════════════════════════════════════════════════╝
""")
    
    # 配置示例（在这里修改您的配置）
    config = {
        'es_hosts': ['localhost:9200'],
        'es_index': 'insurance_knowledge',
        'es_username': 'elastic',
        'es_password': 'cKyMr-jgTTeFGAHG9yHo',
        'use_https': True,
        'verify_certs': False,
    }
    
    # 从环境变量覆盖（可选）
    if os.getenv('ES_HOSTS'):
        config['es_hosts'] = [os.getenv('ES_HOSTS')]
    if os.getenv('ES_USERNAME'):
        config['es_username'] = os.getenv('ES_USERNAME')
    if os.getenv('ES_PASSWORD'):
        config['es_password'] = os.getenv('ES_PASSWORD')
    if os.getenv('ES_HTTPS'):
        config['use_https'] = os.getenv('ES_HTTPS').lower() == 'true'
    if os.getenv('ES_VERIFY_CERTS'):
        config['verify_certs'] = os.getenv('ES_VERIFY_CERTS').lower() == 'true'
    
    # 测试连接
    success, message = test_elasticsearch_connection(config)
    
    print(f"\n{'='*60}")
    print(message)
    print('='*60)
    
    # 建议
    if not success:
        print("\n💡 故障排除建议：")
        print("\n1️⃣  检查服务是否运行")
        print("   docker ps | grep elasticsearch")
        
        print("\n2️⃣  启动 Elasticsearch（如果未运行）")
        print("   docker run -d -p 9200:9200 -e discovery.type=single-node \\")
        print("     docker.elastic.co/elasticsearch/elasticsearch:latest")
        
        print("\n3️⃣  查看日志")
        print("   docker logs <container_id>")
        
        print("\n4️⃣  测试连接（使用 curl）")
        print("   curl -u elastic:password https://localhost:9200 -k")
        
        print("\n5️⃣  重置密码")
        print("   docker exec -it <container_id> bash")
        print("   bin/elasticsearch-reset-password -u elastic")
        
        return 1
    
    print("\n✨ 一切就绪！现在可以运行应用了：")
    print("   python aibot-2.py --mode gui --init-es")
    
    return 0


if __name__ == '__main__':
    # 如果在 aibot-2.py 所在目录运行此脚本
    sys.exit(main())


# ============================================================================
# 交互式配置向导（可选）
# ============================================================================

def interactive_config():
    """交互式配置向导"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         Elasticsearch 交互式配置向导                            ║
╚════════════════════════════════════════════════════════════════╝

请输入 Elasticsearch 配置信息，按 Enter 使用默认值。
""")
    
    config = {}
    
    # ES 主机
    default_host = 'localhost:9200'
    host_input = input(f"Elasticsearch 主机地址 [{default_host}]: ").strip()
    config['es_hosts'] = [host_input] if host_input else [default_host]
    
    # 索引名称
    default_index = 'insurance_knowledge'
    index_input = input(f"索引名称 [{default_index}]: ").strip()
    config['es_index'] = index_input if index_input else default_index
    
    # 用户名
    default_user = 'elastic'
    user_input = input(f"用户名 [{default_user}]: ").strip()
    config['es_username'] = user_input if user_input else default_user
    
    # 密码
    password_input = input("密码: ").strip()
    config['es_password'] = password_input if password_input else None
    
    # HTTPS
    https_input = input("使用 HTTPS (y/n) [y]: ").strip().lower()
    config['use_https'] = https_input != 'n'
    
    # 验证证书
    verify_input = input("验证 SSL 证书 (y/n) [n]: ").strip().lower()
    config['verify_certs'] = verify_input == 'y'
    
    print("\n测试连接...")
    success, message = test_elasticsearch_connection(config)
    print(message)
    
    if success:
        # 保存配置（可选）
        save_input = input("\n是否保存配置到 es_config.json? (y/n) [n]: ").strip().lower()
        if save_input == 'y':
            import json
            with open('es_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            print("✅ 配置已保存到 es_config.json")
    
    return config


# ============================================================================
# 命令行选项
# ============================================================================

if __name__ == '__main__' and len(sys.argv) > 1:
    if sys.argv[1] == '--interactive':
        config = interactive_config()
    elif sys.argv[1] == '--help':
        print("""
用法：python test_es_connection.py [选项]

选项：
  (无)           使用默认配置运行测试
  --interactive  交互式配置向导
  --help         显示此帮助信息

配置文件说明：
  可以在 test_es_connection.py 的 main() 函数中修改 config 字典
  或使用环境变量覆盖：
    ES_HOSTS=localhost:9200
    ES_USERNAME=elastic
    ES_PASSWORD=your_password
    ES_HTTPS=true
    ES_VERIFY_CERTS=false
""")
    sys.exit(0)
