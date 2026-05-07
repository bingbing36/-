"""
Elasticsearch 保险数据搜索系统
功能：
1. 连接到Elasticsearch
2. 创建索引
3. 索引文档（从docs文件夹读取数据）
4. 执行搜索查询
5. 显示搜索结果
"""

import os
import json
from pathlib import Path
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import time
import warnings
import urllib3
from pypdf import PdfReader

# 抑制HTTPS安全警告（仅用于本地开发）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Connecting to .*using TLS with verify_certs=False')


class InsuranceSearchEngine:
    def __init__(self, es_host="localhost", es_port=9200, username=None, password=None, verify_certs=False, use_https=True):
        """
        初始化ES连接（支持8.x+和9.x版本）
        
        【Elasticsearch BM25检索算法详解】
        
        Elasticsearch采用BM25算法进行相关性排序。BM25相比TF-IDF有以下优势：
        ✓ 词频饱和性：避免高词频导致过度匹配
        ✓ 文档长度归一化：避免长文档获得不公平的高分
        ✓ 参数优化：k1=1.2和b=0.75是经验最优值
        
        【BM25公式】
        _score = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))
        
        参数说明：
        • qi: 第i个关键词（非虚词）
        • IDF(qi): 逆文档频率 = log((N - n + 0.5) / (n + 0.5))
          - 关键词在全体文档中越少见，IDF越高
        • f(qi, D): 词频 = 关键词在文档D中出现的次数
          - 但不是线性关系（k1参数控制饱和度）
        • |D|: 文档长度
        • avgdl: 平均文档长度
          - 长文档的分数会被压低（b参数控制影响程度）
        
        【关键词提取的关键作用】
        ⚠️ 重要：并非查询中的每一个词都参与BM25评分！
        
        示例：查询 = "工伤保险和雇主险有什么区别？"
        
        ❌ 错误理解：所有15个汉字都参与匹配
        ✓ 正确理解：只有关键词参与匹配
        
        分析过程：
        1. 按语义单位分词：["工伤保险", "和", "雇主险", "有", "什么", "区别"]
        2. 识别虚词（stopwords）：["和" "有" "什么"]
        3. 提取关键词：["工伤保险", "雇主险", "区别"]
        4. 仅用关键词进行BM25评分
        
        虚词被过滤的原因：
        • 虚词几乎出现在所有文档中，IDF接近0
        • 不能体现文档的主题信息
        • 保留会导致大量无意义匹配
        
        【搜索流程】
        1️⃣  分析查询 → 提取关键词(移除虚词)
        2️⃣  扫描索引 → 遍历所有文档
        3️⃣  计算分数 → 使用BM25公式
        4️⃣  排序结果 → 按_score高到低
        """
        try:
            # 支持Elasticsearch 8.x+版本（包括9.x）
            # ES 9.x默认使用HTTPS
            protocol = "https" if use_https else "http"
            es_url = f"{protocol}://{es_host}:{es_port}"
            
            print(f"连接到: {es_url}")
            
            # 连接参数
            kwargs = {
                "verify_certs": verify_certs
            }
            
            # 如果提供了用户名和密码，则使用认证
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
            print("\n尝试建议:")
            print("1. 确保Elasticsearch服务正在运行")
            print("2. 对于ES 8.0+，默认启用了安全认证")
            print("3. 尝试访问: http://localhost:9200 或 https://localhost:9200")
            print("4. 如需使用认证，创建ES客户端时传入username和password参数")
            raise

        self.index_name = "insurance_docs"
        self.docs_path = Path(__file__).parent / "docs"

    def extract_keywords(self, query_text):
        """
        从查询文本中提取关键词
        移除虚词（如：和、有、什么、的、了等）
        """
        # 常见的中文虚词
        stopwords = {'和', '有', '什么', '的', '了', '是', '在', '都', '很', '这', '那', 
                    '也', '又', '还', '怎', '为', '以', '被', '把', '给', '让', '跟',
                    '通过', '或', '及', '等', '但', '然而', '因为', '所以', '如果',
                    '就', '只', '才', '已', '不', '否则', '反而', '相比', '相对'}
        
        # 分词
        words = query_text.replace('？', '').replace('?', '').split()
        
        # 过滤虚词，只保留关键词
        keywords = [w for w in words if w and w not in stopwords]
        
        return keywords
    
    def get_explanation(self, score, max_score):
        """
        基于_score值给出ES评分的理论解释
        BM25公式: score = Σ (IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl)))
        其中：
        - qi: 第i个关键词
        - IDF(qi): 词的逆文档频率
        - f(qi, D): 关键词在文档D中的频率(词频)
        - |D|: 文档长度
        - avgdl: 平均文档长度
        - k1, b: 调优参数（通常k1=1.2, b=0.75）
        """
        relevance = (score / max_score) * 100 if max_score > 0 else 0
        
        if relevance >= 90:
            explanation = "多个关键词高频匹配，文档长度合理，高度相关"
        elif relevance >= 70:
            explanation = "关键词多次出现或稀有词匹配，相关度高"
        elif relevance >= 50:
            explanation = "部分关键词匹配，中等相关度"
        else:
            explanation = "最少一个关键词匹配，相关度较低"
        
        return relevance, explanation

    def create_index(self):
        """创建索引，并定义mapping"""
        # 删除旧索引（如果存在）
        if self.es.indices.exists(index=self.index_name):
            print(f"删除旧索引: {self.index_name}")
            self.es.indices.delete(index=self.index_name)
            time.sleep(1)

        # 定义索引配置和mapping
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "chinese_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
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
                    "content": {
                        "type": "text",
                        "analyzer": "standard",
                        "search_analyzer": "standard",
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "raw": {
                                "type": "keyword"
                            }
                        }
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
                
                # 提取标题（通常是第一行或包含【】的行）
                lines = content.split('\n')
                title = lines[0] if lines else file_path.stem
                
                # 清理标题
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
                
                # 提取标题
                title = file_path.stem
                
                # 截断编码长度过长的内容，避免索引失败
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
        """将文档索引到Elasticsearch"""
        if not documents:
            print("✗ 没有文档可以索引")
            return 0

        # 使用bulk API批量插入
        actions = []
        for i, doc in enumerate(documents):
            action = {
                "_index": self.index_name,
                "_id": i,
                "_source": doc
            }
            actions.append(action)

        try:
            success_count = 0
            failed_docs = []
            
            # 使用bulk并捕获详细错误
            for ok, action in bulk(self.es, actions, chunk_size=100, raise_on_error=False):
                if not ok:
                    failed_docs.append(action)
                else:
                    success_count += 1
            
            print(f"✓ 成功索引 {success_count} 条文档")
            
            if failed_docs:
                print(f"✗ 失败 {len(failed_docs)} 条文档:")
                for idx, failed in enumerate(failed_docs[:5]):  # 只显示前5个失败
                    print(f"  - {documents[idx].get('filename', 'unknown')}: {failed.get('error', 'Unknown error')}")
            
            return success_count
        except Exception as e:
            print(f"✗ 索引文档失败: {e}")
            # 尝试单个索引，找出具体问题
            print("\n尝试逐个索引以找出问题文档...")
            success_count = 0
            for i, doc in enumerate(documents):
                try:
                    self.es.index(index=self.index_name, id=i, body=doc)
                    success_count += 1
                    print(f"  ✓ {doc.get('filename')}")
                except Exception as doc_error:
                    print(f"  ✗ {doc.get('filename')}: {doc_error}")
            
            return success_count

    def search(self, query_text, size=10):
        """
        执行搜索查询 - 使用BM25检索算法
        
        【BM25算法原理】
        BM25是Elasticsearch采用的默认相关性评分算法。
        
        基本流程：
        1. 分析查询：提取关键词（移除虚词，只保留有实际意义的词）
        2. 遍历文档：对索引中的每个文档进行评分
        3. BM25计算：
           _score = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))
           
           其中：
           - qi: 第i个关键词（非虚词）
           - IDF(qi): 逆文档频率 = log((N - n + 0.5) / (n + 0.5))
             * N: 总文档数
             * n: 包含该词的文档数
             * 关键词越少见，IDF值越高
           
           - f(qi, D): 关键词在文档D中的频率(词频)
             * 词频越高，_score越高
           
           - |D|: 文档长度
           - avgdl: 平均文档长度
             * 长文档中相同词频的权重较低
           
           - k1=1.2: 调控词频饱和度（1.2是经验最优值）
           - b=0.75: 调控文档长度的影响（0.75是经验最优值）
        
        4. 排序：按 _score 从高到低排列
        
        【关键词提取的重要性】
        并非查询文本中的每一个词都用于匹配。例如：
        原始查询："工伤保险和雇主险有什么区别？"
        包含的所有词语：["工伤保险", "和", "雇主险", "有", "什么", "区别"]
        
        其中：
        - 关键词：["工伤保险", "雇主险", "区别"] ✓ 参与BM25评分
        - 虚词：["和", "有", "什么"] ✗ 直接过滤，不参与评分
        
        虚词不参与评分的原因：
        - 虚词在几乎所有文档中都出现（IDF接近0）
        - 会产生大量无意义的匹配
        - 影响搜索精准度
        """
        # 分词处理
        keywords = query_text.split()
        
        search_body = {
            "query": {
                "bool": {
                    "should": [
                        # 标题精确短语匹配（权重最高）
                        {
                            "match_phrase": {
                                "title": {
                                    "query": query_text,
                                    "boost": 5
                                }
                            }
                        },
                        # 标题模糊匹配
                        {
                            "match": {
                                "title": {
                                    "query": query_text,
                                    "boost": 3,
                                    "operator": "or"
                                }
                            }
                        },
                        # 内容精确短语匹配
                        {
                            "match_phrase": {
                                "content": {
                                    "query": query_text,
                                    "boost": 2
                                }
                            }
                        },
                        # 内容模糊匹配
                        {
                            "match": {
                                "content": {
                                    "query": query_text,
                                    "boost": 1,
                                    "operator": "or"
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": size
        }

        try:
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

        print("=" * 80)
        print(f"搜索结果详情 (共 {total} 条相关文档)")
        print("=" * 80 + "\n")

        if total == 0:
            print("未找到匹配的文档")
            return

        # 获取最高分用于归一化显示
        max_score = hits['hits'][0]['_score'] if hits['hits'] else 1
        
        for idx, hit in enumerate(hits.get('hits', []), 1):
            source = hit['_source']
            score = hit['_score']
            relevance, explanation = self.get_explanation(score, max_score)

            print(f"【结果 {idx}】")
            print(f"文件: {source.get('filename', 'N/A')}")
            print(f"标题: {source.get('title', 'N/A')}")
            print(f"_score: {score:.4f} | 相关性: {relevance:.1f}%")
            print(f"BM25解释: {explanation}")
            
            # 显示内容摘要
            content = source.get('content', '')
            print(f"内容: {content[:300]}...")
            
            print("-" * 80 + "\n")


def main():
    """主函数"""
    print("开始初始化保险数据搜索系统...\n")

    try:
        # ===== 配置部分 =====
        ES_HOST = "localhost"
        ES_PORT = 9200
        # 如果ES启用了安全认证，请配置用户名和密码
        # ES_USERNAME = "elastic"
        # ES_PASSWORD = "your_password"
        ES_USERNAME = "elastic"
        ES_PASSWORD = "cKyMr-jgTTeFGAHG9yHo"
        
        # 1. 初始化搜索引擎
        engine = InsuranceSearchEngine(
            es_host=ES_HOST, 
            es_port=ES_PORT,
            username=ES_USERNAME,
            password=ES_PASSWORD,
            verify_certs=False,
            use_https=True  # ES 9.x默认使用HTTPS
        )

        # 2. 创建索引
        print("\n--- 创建索引 ---")
        engine.create_index()

        # 3. 读取文档
        print("\n--- 读取文档 ---")
        documents = engine.read_txt_files()

        # 4. 索引文档
        print("\n--- 索引文档 ---")
        indexed_count = engine.index_documents(documents)

        if indexed_count == 0:
            print("✗ 没有文档被索引，无法继续搜索")
            return

        # 等待索引完成
        time.sleep(1)

        # 5. 执行搜索
        print("\n--- 执行搜索 ---")
        search_query = "工伤保险和雇主险有什么区别？"
        
        # 提取关键词
        keywords = engine.extract_keywords(search_query)
        
        print(f"\n📋 原始查询: '{search_query}'")
        print(f"\n【步骤1】分析查询")
        print(f"  原始词汇: {search_query.replace('？', '').split()}")
        print(f"  提取关键词: {keywords} (移除虚词后)")
        print(f"  说明: 虚词如'和','有','什么'等不参与匹配，只有关键词'工伤保险','雇主险','区别'等会被用于检索")
        
        print(f"\n【步骤2-5】Elasticsearch BM25检索过程")
        print(f"  • 遍历索引中的每个文档")
        print(f"  • 对每个文档计算 _score:")
        print(f"    - TF (Term Frequency): 关键词'{keywords[0]}'在文档中的频率")
        print(f"    - IDF (Inverse Document Frequency): 关键词在全体文档中的稀有度")
        print(f"    - 字段长度: 标题字段(短) 权重 > 内容字段(长) 权重")
        print(f"  • BM25公式: score = Σ IDF(keyword) × TF / (TF + k1×(1-b+b×|D|/avgdl))")
        print(f"    其中 k1=1.2, b=0.75 是经过优化的参数值")
        print(f"  • 按 _score 从高到低排序结果\n")
        
        # 执行搜索
        results = engine.search(search_query, size=20)
        
        # 检查搜索结果
        if results:
            total_hits = results.get('hits', {}).get('total', {}).get('value', 0)
            print(f"✓ 搜索完成！共找到 {total_hits} 条相关文档\n")
            engine.display_results(results, search_query)
        else:
            print("[搜索失败] 无法获得搜索结果")

    except Exception as e:
        print(f"\n✗ 出错: {e}")
        print("\n✓ 故障排除:")
        print("  1. 检查Elasticsearch是否已安装和运行")
        print("  2. 运行: python -m pip install elasticsearch")
        print("  3. 启动Elasticsearch服务")
    
    print("\n✓ 搜索完成！")


if __name__ == "__main__":
    main()
