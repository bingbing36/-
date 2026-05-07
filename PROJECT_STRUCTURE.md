# AI 保险问询助手 - 项目文件夹结构

## 📂 项目概览

```
CASE-AI搜索问题-20260303/
│
├── 📚 核心文档（4个）
│   ├── README.md                   # 项目主文档 - 项目概述和版本说明
│   ├── QUICKSTART.md               # 快速开始指南 - 5分钟快速上手
│   ├── ARCHITECTURE.md             # 架构设计说明 - 系统架构和设计原理
│   └── CHANGELOG.md                # 版本更新日志 - 版本演进和更新记录
│
├── ⚙️ 配置文件（2个）
│   ├── requirements.txt            # Python 依赖包列表
│   └── .env.example                # 环境变量配置示例
│
├── 💻 核心代码文件（8个）
│   ├── aibot-1.py                  # 基础版本 - 本地文档RAG检索
│   ├── aibot-2.py                  # Elasticsearch 增强版 - 企业级向量检索
│   ├── aibot-3.py                  # Elasticsearch + Tavily 增强版 - 双源融合
│   ├── aibot-4.py                  # Gradio Pro 版本 - 专业UI界面【推荐】
│   ├── assistant_ticket_bot-3.py   # 智能工单助手
│   ├── es_insurance_search.py      # Elasticsearch 保险搜索工具
│   ├── index_and_search_docs-embedding.py  # 文档嵌入和索引
│   ├── qwen-agent-multi-files.py   # 多文件Qwen智能体
│   ├── qwen3-embedding.py          # Qwen3 向量化模块
│   ├── stock_query_assistant-4.py  # 股票查询助手
│   └── test_es_connection.py       # Elasticsearch 连接测试
│
├── 📁 核心库目录
│   └── qwen_agent/                 # Qwen Agent 框架库
│       ├── __init__.py
│       ├── agent.py                # 智能体核心类
│       ├── log.py                  # 日志模块
│       ├── multi_agent_hub.py      # 多智能体协调
│       ├── settings.py             # 配置设置
│       ├── agents/                 # 智能体实现
│       │   ├── __init__.py
│       │   ├── article_agent.py    # 文章智能体
│       │   ├── assistant.py        # 助手基类
│       │   ├── dialogue_retrieval_agent.py  # 对话检索智能体
│       │   ├── dialogue_simulator.py        # 对话模拟器
│       │   ├── fncall_agent.py    # 函数调用智能体
│       │   ├── group_chat.py      # 群聊管理
│       │   ├── group_chat_auto_router.py    # 智能路由
│       │   ├── group_chat_creator.py       # 群聊创建器
│       │   ├── human_simulator.py # 人类模拟器
│       │   ├── memo_assistant.py  # 备忘录助手
│       │   ├── react_chat.py      # ReAct 对话
│       │   ├── router.py          # 路由器
│       │   ├── tir_agent.py       # TIR 智能体
│       │   ├── user_agent.py      # 用户智能体
│       │   ├── virtual_memory_agent.py     # 虚拟记忆智能体
│       │   ├── write_from_scratch.py       # 文本生成
│       │   ├── doc_qa/            # 文档问答模块
│       │   │   ├── __init__.py
│       │   │   ├── basic_doc_qa.py
│       │   │   ├── parallel_doc_qa.py
│       │   │   ├── parallel_doc_qa_member.py
│       │   │   └── parallel_doc_qa_summary.py
│       │   ├── keygen_strategies/ # 关键词生成策略
│       │   └── writing/           # 写作相关模块
│       │
│       ├── llm/                    # 大语言模型集成
│       │   ├── __init__.py
│       │   ├── azure.py           # Azure OpenAI
│       │   ├── base.py            # 基类
│       │   ├── function_calling.py # 函数调用
│       │   ├── oai.py             # OpenAI 接口
│       │   ├── openvino.py        # OpenVINO 本地推理
│       │   ├── qwen_dashscope.py  # Qwen DashScope
│       │   ├── qwenaudio_dashscope.py   # Qwen Audio
│       │   ├── qwenomni_oai.py    # Qwen Omni
│       │   ├── qwenvl_dashscope.py      # Qwen VL 视觉
│       │   ├── qwenvl_oai.py      # Qwen VL OpenAI
│       │   ├── qwenvlo_dashscope.py     # Qwen VLO
│       │   ├── schema.py          # 数据模式
│       │   ├── transformers_llm.py      # Transformers 支持
│       │   └── fncall_prompts/   # 函数调用提示词
│       │
│       ├── memory/                 # 记忆管理
│       │   ├── __init__.py
│       │   └── memory.py          # 记忆实现
│       │
│       ├── tools/                  # 工具系统
│       │   ├── __init__.py
│       │   ├── amap_weather.py    # 高德天气
│       │   ├── base.py            # 工具基类
│       │   ├── code_interpreter.py # 代码执行
│       │   ├── doc_parser.py      # 文档解析
│       │   ├── es_advanced_features.py    # ES 高级特性
│       │   ├── es_doc_parser.py   # ES 文档解析
│       │   ├── es_manager.py      # ES 管理器
│       │   ├── es_retrieval.py    # ES 检索
│       │   ├── extract_doc_vocabulary.py  # 词汇提取
│       │   ├── image_gen.py       # 图像生成
│       │   ├── image_search.py    # 图像搜索
│       │   ├── image_zoom_in_qwen3vl.py   # 图像放大
│       │   ├── mcp_manager.py     # MCP 管理
│       │   ├── python_executor.py # Python 执行
│       │   ├── retrieval.py       # 检索工具
│       │   ├── simple_doc_parser.py      # 简单文档解析
│       │   ├── storage.py         # 存储管理
│       │   ├── web_extractor.py   # 网页提取
│       │   ├── web_search.py      # 网页搜索
│       │   ├── resource/          # 资源目录
│       │   └── search_tools/      # 搜索工具集
│       │
│       ├── utils/                  # 工具函数
│       │   ├── __init__.py
│       │   ├── output_beautify.py # 输出美化
│       │   ├── parallel_executor.py      # 并行执行
│       │   ├── qwen.tiktoken      # Token 计数
│       │   ├── str_processing.py  # 字符串处理
│       │   ├── tokenization_qwen.py      # Token化
│       │   └── utils.py           # 通用工具
│       │
│       └── gui/                    # 图形界面
│           ├── __init__.py
│           ├── gradio_dep.py      # Gradio 依赖
│           ├── gradio_utils.py    # Gradio 工具
│           ├── utils.py           # UI 工具
│           ├── web_ui.py          # Web UI
│           └── assets/            # UI 资源
│
├── 📕 学习资源和逻辑说明
│   └── logics/                     # 核心逻辑文档
│       ├── 1-Qwen智能体RAG检索核心逻辑.md      # RAG 检索原理
│       ├── 2-Qwen智能体多跳推理实现详解.md     # 多跳推理
│       ├── 3-Qwen预定义Prompt模板详解.md       # Prompt 模板
│       ├── RAG_核心代码解析.md                  # RAG 代码详解
│       └── RAG_实现流程详解.md                  # RAG 流程说明
│
├── 📄 数据和文档
│   ├── docs/                       # 保险知识库文档
│       ├── 1-平安商业综合责任保险（亚马逊）.txt
│       ├── 2-雇主责任险.txt
│       ├── 3-平安企业团体综合意外险.txt
│       ├── 4-雇主安心保.txt
│       ├── 5-施工保.txt
│       ├── 6-财产一切险.txt
│       └── 7-平安装修保.txt
│
│   ├── workspace/                  # 工作空间
│       └── tools/
│           ├── doc_parser/        # 文档解析工具
│           └── simple_doc_parser/ # 简单文档解析
│
│   └── .sixth/                     # 第六方工具集成
│
├── 🎨 其他资源
│   ├── logo.png                    # 项目 Logo
│   └── 知乎直答.png                # 知乎展示图
│
└── 🐍 Python 缓存
    └── __pycache__/               # Python 编译缓存

```

---

## 📖 文件功能速查表

### 📚 文档说明

| 文件 | 用途 | 适合人群 | 内容量 |
|------|------|--------|-------|
| README.md | 项目全面介绍 | 所有用户 | 10KB+ |
| QUICKSTART.md | 快速开始指南 | 新手用户 | 8KB+ |
| ARCHITECTURE.md | 架构设计说明 | 开发人员 | 12KB+ |
| CHANGELOG.md | 版本更新日志 | 升级用户 | 8KB+ |

### 💻 核心代码版本对比

| 版本 | 文件名 | 功能特点 | 推荐场景 |
|------|-------|--------|--------|
| v1 | aibot-1.py | 本地 RAG 检索 | 快速体验 |
| v2 | aibot-2.py | Elasticsearch 增强 | 企业应用 |
| v3 | aibot-3.py | 双源融合（ES + Tavily） | 完整功能 |
| v4 | aibot-4.py | Gradio 专业 UI | 生产部署 ⭐ |

### 🔧 工具和助手代码

| 文件 | 功能 |
|------|------|
| es_insurance_search.py | Elasticsearch 保险搜索 |
| index_and_search_docs-embedding.py | 文档嵌入和向量索引 |
| qwen-agent-multi-files.py | 多文件处理智能体 |
| qwen3-embedding.py | 向量化模块 |
| stock_query_assistant-4.py | 股票查询助手 |
| assistant_ticket_bot-3.py | 工单处理助手 |
| test_es_connection.py | Elasticsearch 连接测试 |

---

## 🏗️ 项目架构层次

```
用户交互层 (GUI)
    ↓
qwen_agent/gui/        ← Web UI + Gradio 界面
    ↓
智能体层 (Agent)
    ↓
qwen_agent/agents/     ← 各类智能体实现
    ↓
能力层 (Tools)
    ↓
qwen_agent/tools/      ← RAG、搜索、代码执行等
    ↓
基础层 (LLM & Memory)
    ↓
qwen_agent/llm/        ← 模型接口
qwen_agent/memory/     ← 记忆管理
```

---

## 🚀 快速开始

### 第 1 步：选择版本

```bash
# 推荐使用 v4 Pro 版本（最完善）
python aibot-4.py --mode gui

# 或选择其他版本
python aibot-1.py      # 基础版
python aibot-2.py      # ES 版
python aibot-3.py      # 增强版
```

### 第 2 步：配置环境

```bash
# 1. 复制环境配置
cp .env.example .env

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
# 编辑 .env，填入：
# - DASHSCOPE_API_KEY
# - TAVILY_API_KEY (可选)
```

### 第 3 步：运行应用

```bash
# 初始化 Elasticsearch（首次）
python aibot-4.py --init-es

# 启动应用
python aibot-4.py --mode gui

# 访问 http://localhost:7860
```

---

## 📊 项目统计

| 项目 | 数量 | 说明 |
|------|------|------|
| 文档文件 | 4 个 | README、快速开始、架构、更新日志 |
| 配置文件 | 2 个 | 环境配置、依赖包 |
| 核心代码 | 8 个 | 4 个版本 + 4 个工具脚本 |
| 库模块 | 1 个 | qwen_agent 完整框架 |
| 学习文档 | 5 个 | logics/ 下的深度讲解 |
| 知识库文档 | 7 个 | docs/ 下的保险资料 |
| **代码总行数** | **3000+** | 包括注释和文档 |

---

## 🎯 模块功能速查

### qwen_agent - 核心框架

| 模块 | 功能 | 关键文件 |
|------|------|--------|
| agents | 智能体实现 | agent.py, assistant.py |
| llm | LLM 模型集成 | qwen_dashscope.py, oai.py |
| tools | 工具系统 | base.py, es_retrieval.py |
| memory | 记忆管理 | memory.py |
| utils | 工具函数 | utils.py, str_processing.py |
| gui | 用户界面 | web_ui.py, gradio_utils.py |

### tools - 工具详解

| 工具 | 功能 | 用途 |
|------|------|------|
| es_retrieval.py | Elasticsearch 检索 | RAG 本地检索 |
| web_search.py | 网页搜索 | 实时信息获取 |
| code_interpreter.py | 代码执行 | 数据分析 |
| doc_parser.py | 文档解析 | 知识库建立 |
| image_gen.py | 图像生成 | 可视化 |

---

## 💡 关键代码文件速览

### 1. 主应用入口
- **aibot-1.py** → aibot-4.py：4 个完整版本，递进式功能升级

### 2. RAG 检索核心
- **es_retrieval.py**：Elasticsearch 检索实现
- **index_and_search_docs-embedding.py**：文档索引和嵌入

### 3. 智能体框架
- **qwen_agent/agents/assistant.py**：Assistant 基类
- **qwen_agent/agents/dialogue_retrieval_agent.py**：对话检索智能体

### 4. LLM 集成
- **qwen_agent/llm/qwen_dashscope.py**：Qwen DashScope 集成
- **qwen_agent/llm/oai.py**：OpenAI 兼容接口

### 5. UI 界面
- **qwen_agent/gui/web_ui.py**：标准 Web UI
- **aibot-4.py**：自定义 Gradio 专业界面

---

## 🔗 文件依赖关系

```
用户脚本（aibot-*.py）
    ↓
    依赖 qwen_agent/agents/assistant.py
    ↓
    ├→ qwen_agent/llm/*           （LLM 模型）
    ├→ qwen_agent/tools/*         （工具系统）
    ├→ qwen_agent/memory/*        （记忆管理）
    └→ qwen_agent/gui/*           （用户界面）

工具脚本（es_insurance_search.py 等）
    ↓
    依赖 qwen_agent/tools/*       （工具库）
    ↓
    依赖 qwen_agent/llm/*         （LLM 集成）
```

---

## 📚 学习路径推荐

### 快速体验（1 小时）
1. 阅读 README.md 了解项目（10 分钟）
2. 按 QUICKSTART.md 快速开始（20 分钟）
3. 运行 aibot-4.py 体验（30 分钟）

### 深入理解（3 小时）
1. 阅读 ARCHITECTURE.md（30 分钟）
2. 查看 logics/ 下的文档理解原理（1 小时）
3. 阅读 qwen_agent/agents/assistant.py 代码（1 小时）
4. 比较 aibot-1.py 到 aibot-4.py 的演进（30 分钟）

### 完全掌握（5+ 小时）
1. 详细研究 qwen_agent/ 框架结构
2. 理解 tools/ 下各工具的实现
3. 学习 llm/ 下的模型集成方式
4. 尝试开发自己的工具或智能体

---

## 🔐 项目配置

### 必需配置
```
DASHSCOPE_API_KEY     # 阿里云 API Key
ES_HOSTS              # Elasticsearch 服务器
ES_USERNAME/PASSWORD  # ES 认证（可选）
```

### 可选配置
```
TAVILY_API_KEY        # 网络搜索 API Key（用于实时信息）
LLM_MODEL             # 选择的 LLM 模型
LOG_LEVEL             # 日志级别
```

详见 `.env.example` 文件

---

## 📦 依赖要求

```
Python >= 3.8
elasticsearch >= 8.0
qwen-agent >= 0.0.10
gradio >= 4.0.0
requests >= 2.28.0
python-dotenv >= 0.19.0
```

完整列表见 `requirements.txt`

---

## 🚀 一键启动命令

```bash
# 1. 环境准备
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置 API
cp .env.example .env
# 编辑 .env 文件

# 3. 运行应用
python aibot-4.py --mode gui

# 4. 访问
# 打开浏览器：http://localhost:7860
```

---

## 📞 获取帮助

### 常见问题
- 查看 QUICKSTART.md 中的"常见问题排查"
- 查看 ARCHITECTURE.md 中的"性能优化"
- 查看 logics/ 目录下的详细讲解

### 遇到错误
1. 查看错误日志
2. 检查 API Key 配置
3. 测试 Elasticsearch 连接：`python test_es_connection.py`
4. 查看相关文档

---

## 📝 版本信息

- **项目名称**：AI 保险问询助手（CASE-AI搜索问题）
- **最新版本**：v4 Gradio Pro
- **更新时间**：2026 年 5 月
- **状态**：✅ 生产就绪

---

## 🎓 核心概念

| 概念 | 说明 | 相关文件 |
|------|------|--------|
| **RAG** | 检索增强生成 | logics/RAG_* |
| **LLM** | 大语言模型 | qwen_agent/llm/ |
| **Agent** | 智能体 | qwen_agent/agents/ |
| **Tool** | 工具系统 | qwen_agent/tools/ |
| **Embedding** | 向量化 | qwen3-embedding.py |
| **Elasticsearch** | 向量数据库 | es_*.py |

---

## 🔗 内部文档交叉引用

| 主题 | 参考文档 |
|------|---------|
| 快速开始 | QUICKSTART.md |
| 项目架构 | ARCHITECTURE.md |
| RAG 原理 | logics/RAG_实现流程详解.md |
| 多跳推理 | logics/2-Qwen智能体多跳推理实现详解.md |
| Prompt | logics/3-Qwen预定义Prompt模板详解.md |
| 版本更新 | CHANGELOG.md |

---

## 📌 重要提示

✅ **推荐使用 aibot-4.py**：最完善的版本，专业 UI + 完整功能  
✅ **首次运行需初始化**：执行 `--init-es` 参数初始化 Elasticsearch  
✅ **API Key 必需**：至少需要配置 DASHSCOPE_API_KEY  
✅ **文档参考**：遇到问题先查看相关文档，再提问  

---

## 🎉 准备就绪

这个项目文件夹包含了完整的代码、文档和资源，可以直接：
1. ✅ 上传到 GitHub
2. ✅ 用于生产部署
3. ✅ 作为学习参考
4. ✅ 进行二次开发

**祝你使用愉快！** 🚀

---

**最后更新**：2026 年 5 月 7 日  
**项目地址**：CASE-AI搜索问题-20260303  
**状态**：✅ 完整 / 📦 可部署 / 📚 文档齐全
