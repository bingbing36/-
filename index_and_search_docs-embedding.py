"""
基于Embedding向量的保险数据搜索系统
功能：
1. 连接到Elasticsearch
2. 使用text-embedding-v4将文档向量化
3. 创建支持向量检索的索引
4. 索引文档（从docs文件夹读取数据）
5. 执行向量相似度搜索查询
6. 显示搜索结果
"""

import os
import json
import time
import warnings
import urllib3
from pathlib import Path
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from pypdf import PdfReader
from openai import OpenAI

# 抑制HTTPS安全警告（仅用于本地开发）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Connecting to .*using TLS with verify_certs=False')


class EmbeddingSearchEngine:
    def __init__(self, es_host="localhost", es_port=9200, username="elastic", password="cKyMr-jgTTeFGAHG9yHo", verify_certs=False, use_https=True):
        """
        初始化ES连接和Embedding模型
        
        【基于Embedding向量的检索原理】
        
        相比BM25关键词匹配，向量检索有以下优势：
        ✓ 语义理解：能理解文本的深层语义，而不仅仅是关键词匹配
        ✓ 同义词识别：自动识别语义相似的不同表述
        ✓ 多语言支持：能处理多语言的语义相关性
        ✓ 上下文感知：考虑整个文本的语义上下文
        
        【向量检索的关键技术】
        1. Embedding向量化：使用text-embedding-v4将文本转换为1024维向量
        2. 向量存储：在Elasticsearch中使用dense_vector类型存储
        3. KNN(K-Nearest Neighbors)检索：找与查询向量最相似的K个文档
        4. 相似度计算：使用cosine相似度
        
        【流程】
        1️⃣  本地文档 → text-embedding-v4 → 文档向量
        2️⃣  文档向量 → 存入Elasticsearch dense_vector字段
        3️⃣  查询文本 → text-embedding-v4 → 查询向量
        4️⃣  查询向量 → KNN搜索 → 返回相似文档
        """
        try:
            # 初始化Elasticsearch客户端
            protocol = "https" if use_https else "http"
            es_url = f"{protocol}://{es_host}:{es_port}"
            
            print(f"连接到: {es_url}")
            
            kwargs = {"verify_certs": verify_certs}
            
            if username and password:
                kwargs["basic_auth"] = (username, password)
                print(f"使用认证连接到Elasticsearch")
            
            self.es = Elasticsearch([es_url], **kwargs)
            
            # 测试连接
            if self.es.ping():
                print(f"✓ 成功连接到Elasticsearch: {es_host}:{es_port}")
            else:
                raise Exception("无法连接到Elasticsearch")
                
        except Exception as e:
            print(f"✗ 连接Elasticsearch失败: {e}")
            raise

        # 初始化Embedding模型客户端
        try:
            self.embedding_client = OpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            print(f"✓ 成功初始化text-embedding-v4模型")
        except Exception as e:
            print(f"✗ 初始化Embedding模型失败: {e}")
            print("  请确保已设置DASHSCOPE_API_KEY环境变量")
            raise

        self.index_name = "insurance_docs_embedding"
        self.docs_path = Path(__file__).parent / "docs"
        self.embedding_dim = 1024  # text-embedding-v4的维度

    def chunk_text(self, text, max_length=8000):
        """
        将超长文本分块处理
        text-embedding-v4的限制是[1, 8192]字符，所以我们保留8000的余量
        
        参数:
            text: 要分块的文本
            max_length: 每块的最大长度，默认8000(留192字符的余量)
        
        返回:
            分块后的文本列表
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        # 按换行符优先分块（保持语义完整性）
        paragraphs = text.split('\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 <= max_length:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_length]]

    def get_embedding(self, text):
        """
        调用text-embedding-v4生成文本的嵌入向量
        
        参数:
            text: 要转换为向量的文本
        
        返回:
            float列表: 1024维的嵌入向量
        """
        try:
            # 处理超长文本：分块后取第一块或平均所有chunks
            if len(text) > 8192:
                print(f"    ⚠️  文本长度({len(text)}字符) > 8192，进行分块处理")
                chunks = self.chunk_text(text)
                print(f"    分块数: {len(chunks)}")
                # 使用第一块作为代表（保留文档开头的关键信息）
                text_to_embed = chunks[0]
            else:
                text_to_embed = text
            
            response = self.embedding_client.embeddings.create(
                model="text-embedding-v4",
                input=text_to_embed,
                dimensions=self.embedding_dim,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"✗ 生成embedding失败: {e}")
            return None

    def create_index(self):
        """创建支持向量检索的索引，并定义mapping"""
        # 删除旧索引（如果存在）
        if self.es.indices.exists(index=self.index_name):
            print(f"删除旧索引: {self.index_name}")
            self.es.indices.delete(index=self.index_name)
            time.sleep(1)

        # 定义索引配置 - 支持向量检索
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "max_result_window": 10000
                }
            },
            "mappings": {
                "properties": {
                    "filename": {
                        "type": "keyword"
                    },
                    "file_type": {
                        "type": "keyword"
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "content_embedding": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine"  # 使用cosine相似度
                    },
                    "timestamp": {
                        "type": "long"
                    }
                }
            }
        }

        try:
            self.es.indices.create(index=self.index_name, body=index_body)
            print(f"✓ 成功创建索引: {self.index_name}")
            print(f"  向量维度: {self.embedding_dim}")
            print(f"  相似度算法: cosine")
        except Exception as e:
            print(f"✗ 创建索引失败: {e}")
            raise

    def read_txt_files(self):
        """读取docs文件夹下的所有txt和pdf文件"""
        documents = []
        txt_files = list(self.docs_path.glob("*.txt"))
        pdf_files = list(self.docs_path.glob("*.pdf"))
        
        all_files = txt_files + pdf_files
        
        if not all_files:
            print("✗ 在docs文件夹中未找到txt或pdf文件")
            return documents

        print(f"找到 {len(txt_files)} 个txt文件，{len(pdf_files)} 个pdf文件")
        
        # 处理txt文件
        for file_path in txt_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取标题
                lines = content.split('\n')
                title = lines[0] if lines else file_path.stem
                title = title.strip().lstrip('【').rstrip('】')
                
                documents.append({
                    "filename": file_path.name,
                    "file_type": "txt",
                    "title": title,
                    "content": content,
                    "timestamp": int(time.time() * 1000)
                })
                print(f"  ✓ 加载TXT: {file_path.name}")
            except Exception as e:
                print(f"  ✗ 读取失败 {file_path.name}: {e}")
        
        # 处理pdf文件
        for file_path in pdf_files:
            try:
                reader = PdfReader(file_path)
                content = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n"
                
                title = file_path.stem
                
                # 截断过长的内容
                if len(content) > 50000:
                    content = content[:50000]
                
                documents.append({
                    "filename": file_path.name,
                    "file_type": "pdf",
                    "title": title,
                    "content": content,
                    "timestamp": int(time.time() * 1000)
                })
                print(f"  ✓ 加载PDF: {file_path.name}")
            except Exception as e:
                print(f"  ✗ 读取失败 {file_path.name}: {e}")
        
        return documents

    def index_documents(self, documents):
        """
        将文档索引到Elasticsearch，同时生成向量嵌入
        
        【向量生成策略】
        对每个文档，我们使用content字段来生成嵌入向量，因为：
        ✓ content包含最完整的语义信息
        ✓ 更好地捕获文档的主题和内容
        ✓ 便于语义相似度计算
        """
        if not documents:
            print("✗ 没有文档可以索引")
            return 0

        print("\n--- 生成文档向量 ---")
        
        actions = []
        for i, doc in enumerate(documents):
            try:
                # 为文档内容生成向量
                print(f"  正在向量化: {doc.get('filename')} ({i+1}/{len(documents)})")
                embedding = self.get_embedding(doc['content'])
                
                if embedding is None:
                    print(f"    ✗ 向量化失败，跳过该文档")
                    continue
                
                # 添加向量到文档
                doc['content_embedding'] = embedding
                
                action = {
                    "_index": self.index_name,
                    "_id": i,
                    "_source": doc
                }
                actions.append(action)
                print(f"    ✓ 向量化完成 ({len(embedding)}维)")
                
            except Exception as e:
                print(f"    ✗ 处理失败: {e}")
                continue

        if not actions:
            print("✗ 没有可以索引的文档")
            return 0

        # 批量索引
        print(f"\n--- 索引文档 ---")
        success_count = 0
        
        try:
            # 使用bulk操作，raise_on_error=False会继续处理后续文档
            for ok, result in bulk(self.es, actions, chunk_size=10, raise_on_error=False):
                if ok:
                    success_count += 1
            
            print(f"✓ 成功索引 {success_count} 条文档")
            return success_count
            
        except Exception as e:
            print(f"⚠️  Bulk索引报错: {e}，尝试逐个索引...")
            
            # 回退方案：逐个索引文档
            success_count = 0
            for action in actions:
                try:
                    self.es.index(
                        index=action["_index"],
                        id=action["_id"],
                        body=action["_source"]
                    )
                    success_count += 1
                except Exception as doc_error:
                    print(f"  ✗ 索引失败 {action['_source'].get('filename')}: {doc_error}")
            
            print(f"✓ 通过逐个索引方式成功索引 {success_count} 条文档")
            return success_count

    def search(self, query_text, size=10):
        """
        执行向量相似度搜索
        
        【KNN(K-Nearest Neighbors)搜索原理】
        1. 查询向量化：将查询文本转换为1024维向量
        2. 相似度计算：使用cosine相似度度量
           cosine_similarity = (A · B) / (||A|| × ||B||)
           其中 A是查询向量，B是文档向量
        3. 排序：返回相似度最高的K个文档
        4. 结果范围：相似度分数在[-1, 1]之间
           * 1.0: 完全相同
           * 0.0: 完全正交（无关）
           * -1.0: 完全相反
        
        【与BM25的对比】
        BM25:
        - 关键词匹配，不理解语义
        - "工伤保险"和"工作伤害保险"被视为完全不同
        - 易受关键词选择影响
        
        向量检索:
        - 语义理解，捕捉深层含义
        - "工伤保险"和"工作伤害保险"被识别为高度相似（都在向量空间中靠近）
        - 对表述变化更鲁棒
        """
        try:
            # 生成查询向量
            print(f"正在向量化查询: '{query_text}'")
            query_embedding = self.get_embedding(query_text)
            
            if query_embedding is None:
                print("✗ 查询向量化失败")
                return None
            
            print(f"✓ 查询向量化完成 ({len(query_embedding)}维)")
            
            # 构建KNN搜索查询
            search_body = {
                "knn": {
                    "field": "content_embedding",
                    "query_vector": query_embedding,
                    "k": size,
                    "num_candidates": min(size * 10, 100)
                },
                "size": size
            }
            
            # 执行搜索
            results = self.es.search(index=self.index_name, body=search_body)
            return results
            
        except Exception as e:
            print(f"✗ 搜索失败: {e}")
            return None

    def display_results(self, results, query_text):
        """显示搜索结果"""
        if not results:
            print("未获得搜索结果")
            return

        hits = results.get('hits', {})
        total = hits.get('total', {}).get('value', 0)

        print("=" * 100)
        print(f"搜索结果详情 (共 {total} 条相关文档)")
        print("=" * 100 + "\n")

        if total == 0:
            print("未找到匹配的文档")
            return

        # 获取最高分用于归一化显示
        max_score = hits['hits'][0]['_score'] if hits['hits'] else 1
        
        for idx, hit in enumerate(hits.get('hits', []), 1):
            source = hit['_source']
            score = hit['_score']  # cosine相似度分数
            similarity_pct = ((score + 1) / 2) * 100  # 转换为百分比
            
            print(f"【结果 {idx}】")
            print(f"文件: {source.get('filename', 'N/A')}")
            print(f"标题: {source.get('title', 'N/A')}")
            print(f"相似度分数: {score:.4f} | 相似度百分比: {similarity_pct:.1f}%")
            
            if score > 0.7:
                explanation = "高度相似，语义匹配度很高"
            elif score > 0.5:
                explanation = "中等相似，有明显的语义关联"
            elif score > 0.3:
                explanation = "低相似，有一定的语义关联"
            else:
                explanation = "相似度较低，语义关联弱"
            
            print(f"向量检索解释: {explanation}")
            
            # 显示内容摘要
            content = source.get('content', '')
            print(f"内容摘要: {content[:300]}...")
            
            print("-" * 100 + "\n")


def main():
    """主函数"""
    print("开始初始化向量搜索系统...\n")

    try:
        # ===== 配置部分 =====
        ES_HOST = "localhost"
        ES_PORT = 9200
        ES_USERNAME = "elastic"
        ES_PASSWORD = "cKyMr-jgTTeFGAHG9yHo"
        
        # 1. 初始化搜索引擎
        engine = EmbeddingSearchEngine(
            es_host=ES_HOST, 
            es_port=ES_PORT,
            username=ES_USERNAME,
            password=ES_PASSWORD,
            verify_certs=False,
            use_https=True
        )

        # 2. 创建支持向量检索的索引
        print("\n--- 创建索引 ---")
        engine.create_index()

        # 3. 读取文档
        print("\n--- 读取文档 ---")
        documents = engine.read_txt_files()

        # 4. 索引文档（包括向量化）
        print("\n--- 索引文档并生成向量 ---")
        indexed_count = engine.index_documents(documents)

        if indexed_count == 0:
            print("✗ 没有文档被索引，无法继续搜索")
            return

        # 等待索引完成
        time.sleep(2)

        # 5. 执行搜索
        print("\n--- 执行向量相似度搜索 ---")
        search_query = "工伤保险和雇主险有什么区别？"
        
        print(f"\n📋 原始查询: '{search_query}'")
        print(f"\n【步骤1】向量化查询")
        print(f"  查询文本 → text-embedding-v4 → 1024维向量")
        
        print(f"\n【步骤2-4】Elasticsearch KNN搜索过程")
        print(f"  • 计算查询向量与每个文档向量的cosine相似度")
        print(f"  • cosine相似度公式: (A · B) / (||A|| × ||B||)")
        print(f"  • 相似度范围: [-1, 1]")
        print(f"    - 1.0: 完全相同")
        print(f"    - 0.5: 中等相似")
        print(f"    - 0.0: 完全无关")
        print(f"  • 返回相似度最高的前K个文档\n")
        
        # 执行搜索
        results = engine.search(search_query, size=10)
        
        if results:
            total_hits = results.get('hits', {}).get('total', {}).get('value', 0)
            print(f"\n✓ 搜索完成！共找到 {total_hits} 条相关文档\n")
            engine.display_results(results, search_query)
        else:
            print("✗ 搜索失败")

    except Exception as e:
        print(f"\n✗ 出错: {e}")
        print("\n✓ 故障排除:")
        print("  1. 检查Elasticsearch是否已安装和运行")
        print("  2. 运行: pip install elasticsearch openai")
        print("  3. 设置DASHSCOPE_API_KEY环境变量")
        print("  4. 启动Elasticsearch服务")
    
    print("\n✓ 完成！")


if __name__ == "__main__":
    main()
