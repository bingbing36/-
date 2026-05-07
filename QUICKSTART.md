# 快速开始指南

## 5 分钟快速开始

### 第 1 步：准备环境（2 分钟）

```bash
# 克隆或下载项目到本地
cd insurance-qa-system

# 创建 Python 虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 第 2 步：配置 API Key（1 分钟）

创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_api_key_here
TAVILY_API_KEY=your_api_key_here
```

或直接设置环境变量：

```bash
# Windows PowerShell:
$env:DASHSCOPE_API_KEY = "your_api_key"
$env:TAVILY_API_KEY = "your_api_key"

# Linux/Mac:
export DASHSCOPE_API_KEY="your_api_key"
export TAVILY_API_KEY="your_api_key"
```

### 第 3 步：准备文档（1 分钟）

创建 `docs` 文件夹并放入保险文档：

```
insurance-qa-system/
├── docs/
│   ├── 1-平安商业综合责任保险.txt
│   ├── 2-雇主责任险.txt
│   └── ...
└── versions/
```

### 第 4 步：启动应用（1 分钟）

选择你想使用的版本启动：

```bash
# 推荐：使用最新的 v4 Pro 版本
python versions/aibot-v4-gradio.py

# 首次运行会自动初始化 Elasticsearch
# 等待初始化完成后访问：http://localhost:7860
```

---

## 版本选择指南

| 需求 | 推荐版本 | 命令 |
|------|--------|------|
| 最简单快速体验 | v1 基础版 | `python versions/aibot-v1-basic.py` |
| 企业级大数据 | v2 ES版 | `python versions/aibot-v2-elasticsearch.py` |
| 需要实时信息 | v3 增强版 | `python versions/aibot-v3-enhanced.py` |
| 生产环境部署 | v4 Pro版 | `python versions/aibot-v4-gradio.py` |

---

## 常见问题排查

### ❌ 错误：`DASHSCOPE_API_KEY not found`

**原因**：未配置 API Key

**解决**：
1. 创建 `.env` 文件（复制 `.env.example`）
2. 填入实际的 API Key
3. 重新启动应用

### ❌ 错误：`Elasticsearch connection failed`

**原因**：Elasticsearch 服务未启动

**解决**：
```bash
# 使用 Docker 启动 Elasticsearch
docker run -d -p 9200:9200 \
  -e discovery.type=single-node \
  -e ELASTIC_PASSWORD=your_password \
  docker.elastic.co/elasticsearch/elasticsearch:8.10.0

# 更新 .env 文件中的密码
# 然后重新启动应用
```

### ❌ 错误：`Port 7860 already in use`

**原因**：端口被占用

**解决**：
```bash
# 方式 1：使用不同的端口
python versions/aibot-v4-gradio.py --server-port 8080

# 方式 2：关闭占用端口的进程
# Windows:
netstat -ano | findstr :7860
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :7860
kill -9 <PID>
```

### ❌ 错误：`Docker command timed out`

**原因**：Docker 不可用或超时

**解决**：
- 确保 Docker 服务已启动
- v4 版本会自动降级（禁用 code_interpreter）
- 或切换到 v3 版本

---

## 各版本启动命令详解

### v1 - 基础版本

```bash
python versions/aibot-v1-basic.py

# 参数说明：
# --mode gui        启动 Web 界面（默认）
# --mode terminal   启动终端模式

# 完整示例：
python versions/aibot-v1-basic.py --mode gui
```

### v2 - Elasticsearch 版本

```bash
# 首次运行：初始化并预加载文档
python versions/aibot-v2-elasticsearch.py --init-es

# 启动应用
python versions/aibot-v2-elasticsearch.py --mode gui

# 参数说明：
# --init-es         初始化 Elasticsearch 索引
# --mode gui        启动 Web 界面（默认）
# --mode terminal   启动终端模式
```

### v3 - 增强版本

```bash
# 完整启动命令
python versions/aibot-v3-enhanced.py --mode gui --init-es

# 仅启动（不初始化）
python versions/aibot-v3-enhanced.py

# 终端模式
python versions/aibot-v3-enhanced.py --mode terminal
```

### v4 - Pro 专业版（推荐）

```bash
# 推荐启动方式
python versions/aibot-v4-gradio.py

# 指定端口
python versions/aibot-v4-gradio.py --server-port 8080

# 指定监听地址
python versions/aibot-v4-gradio.py --server-name 0.0.0.0

# 完整参数
python versions/aibot-v4-gradio.py \
    --mode gui \
    --server-name 0.0.0.0 \
    --server-port 7860 \
    --init-es

# 终端模式
python versions/aibot-v4-gradio.py --mode terminal
```

---

## 使用示例

### 例 1：查询本地知识库

**用户输入**：
```
介绍一下雇主责任险的保障范围
```

**预期流程**：
1. ✅ 系统搜索本地文档
2. ✅ 检索相关条款
3. ✅ LLM 生成回答
4. ✅ 标注来源信息

### 例 2：获取最新政策信息

**用户输入**：
```
2026年企业保险有什么新政策？
```

**预期流程**：
1. ✅ 本地检索查询
2. ✅ 网络搜索获取最新信息
3. ✅ 信息融合和整理
4. ✅ 标注来源和发布日期

### 例 3：保险产品对比

**用户输入**：
```
请对比：平安企业综合意外险和施工保险
```

**预期流程**：
1. ✅ 检索两个产品的条款
2. ✅ 自动生成对比表
3. ✅ 突出核心差异
4. ✅ 提出建议

---

## 性能优化建议

### 1. 首次启动优化

```bash
# 预热 Docker（如果使用 code_interpreter）
docker run --rm hello-world

# 预加载 Elasticsearch 索引
python versions/aibot-v4-gradio.py --init-es --mode terminal

# 然后正常启动
python versions/aibot-v4-gradio.py
```

### 2. 文档优化

- 优先加载常用文档
- 定期清理过期文档
- 文档分类放在不同目录

### 3. 查询优化

```python
# 明确具体问题而不是模糊查询
✅ 好：雇主责任险对员工工伤有什么保障？
❌ 差：保险怎么样？

# 提供关键信息上下文
✅ 好：我们是科技公司，员工有 100 人，如何选择保险？
❌ 差：应该买什么保险？
```

---

## 进阶配置

### 更改 LLM 模型

编辑版本文件中的 `llm_cfg`：

```python
llm_cfg = {
    'model': 'qwen-turbo',  # 改为其他模型
    'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv('DASHSCOPE_API_KEY'),
    'generate_cfg': {
        'top_p': 0.8,
        'temperature': 0.3,
    }
}
```

### 自定义系统提示词

编辑版本文件中的 `system_instruction`：

```python
system_instruction = '''你是一个保险顾问...

你的职责是：
1. 提供准确的保险信息
2. 分析客户的保险需求
3. 建议合适的保险方案

回答时要注意：
- 突出条款中的重要信息
- 明确说明保障范围和限制
- 提供具体建议
'''
```

### 调整检索参数

编辑版本文件中的 `rag_cfg`：

```python
rag_cfg = {
    'max_ref_token': 6000,           # 增加返回的参考文本
    'parser_page_size': 500,         # 调整分块大小
    'rag_keygen_strategy': '...',    # 更改关键词策略
    'similarity_threshold': 0.5,     # 调整相似度阈值
}
```

---

## 故障排查清单

- [ ] 已安装 Python 3.8+
- [ ] 已创建虚拟环境并激活
- [ ] 已安装所有依赖包
- [ ] 已配置 DASHSCOPE_API_KEY
- [ ] 已创建 docs 文件夹并放入文档
- [ ] 已启动 Elasticsearch（如使用 v2+）
- [ ] 已检查防火墙设置
- [ ] 已检查网络连接
- [ ] 已查看错误日志并理解错误信息
- [ ] 尝试重启应用和服务

---

## 获取帮助

1. **查看详细文档**
   - [README.md](README.md) - 完整项目说明
   - [ARCHITECTURE.md](ARCHITECTURE.md) - 架构设计
   - [CHANGELOG.md](CHANGELOG.md) - 版本更新

2. **检查常见问题**
   - 本文件的"常见问题排查"部分
   - README.md 中的 FAQ 部分

3. **查看日志**
   - 启动时的初始化日志
   - 运行时的详细日志输出

4. **社区支持**
   - 提交 Issue
   - 联系开发团队

---

**祝你使用愉快！** 🎉

如有问题，欢迎反馈和改进建议。
