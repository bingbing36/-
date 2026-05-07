import argparse
import importlib.util
import os
import re
import socket
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
from qwen_agent.gui.utils import convert_fncall_to_text


BASE_FILE = os.path.join(os.path.dirname(__file__), 'aibot-3.py')


def load_base_module():
    """Dynamically load aibot-3.py so we can reuse existing agent/RAG logic."""
    spec = importlib.util.spec_from_file_location('aibot3_base', BASE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'无法加载基础脚本: {BASE_FILE}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base_module()


CUSTOM_CSS = """
:root {
  --brand-primary: #0057b8;
  --brand-secondary: #0f3d75;
  --brand-bg: #f5f8fd;
  --panel-bg: #ffffff;
  --text-main: #1f2937;
  --text-muted: #64748b;
  --border-soft: #d8e3f2;
}

.gradio-container {
  background:
    radial-gradient(circle at 0% 0%, #dbeafe 0%, rgba(219, 234, 254, 0) 40%),
    radial-gradient(circle at 100% 20%, #e0f2fe 0%, rgba(224, 242, 254, 0) 42%),
    var(--brand-bg);
}

.page-wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 8px 22px;
}

.hero {
  background: linear-gradient(120deg, var(--brand-primary), var(--brand-secondary));
  color: #fff;
  border-radius: 18px;
  padding: 22px 24px;
  box-shadow: 0 12px 30px rgba(15, 61, 117, 0.2);
}

.hero-title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.hero-subtitle {
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.95;
}

.side-card {
  background: var(--panel-bg);
  border: 1px solid var(--border-soft);
  border-radius: 14px;
}

#status-box {
  border-radius: 10px;
  border: 1px solid #cfe0f7;
  background: #edf5ff;
  color: #123a69;
}

#chatbot {
  border-radius: 14px;
  border: 1px solid var(--border-soft);
}
"""


SUGGESTIONS = [
    '介绍一下雇主责任险的核心保障责任',
    '平安商业综合责任保险（亚马逊）适合哪些企业？',
    '企业综合意外险和雇主责任险如何组合配置？',
    '保险理赔通常需要哪些材料，处理周期多久？',
    '2026年最新企业保险合规注意事项有哪些？',
    '施工项目中如何选择施工保与财产一切险？',
]

SYSTEM_PROMPT_OVERRIDE = """你是专业的保险咨询助手。

工作原则：
1. 信息来源优先级：
   - 第一优先：本地知识库（RAG 检索到的保险条款/文档）。
   - 第二优先：Tavily 网络搜索（用于补充“最新政策、时效性强、知识库未覆盖”的信息）。
2. 回答时必须标注来源：
   - 本地知识库信息：标注文档名称或条款名称。
   - 网络信息：标注来源 URL 与发布日期（若可获取）。
3. 不确定性与时效性：
   - 对可能变化的信息，明确写出“查询时间”和“信息可能变动”。
4. 回答风格：
   - 中文、结构化、简洁专业，优先给出结论，再给依据与来源。

工具使用要求：
- 仅使用 tavily_search 作为实时信息补充工具。
- 如果问题是“最新/近期/今日/政策更新/行业动态”，优先调用 tavily_search。
- 每次回答最多调用 1 次 tavily_search，调用后直接输出结论与来源。
"""


def apply_runtime_policy():
    """Enforce product policy for this script."""
    base.tools = ['tavily_search']
    base.system_instruction = SYSTEM_PROMPT_OVERRIDE


def init_agent_service_safe():
    """
    Initialize agent with graceful fallback:
    if code_interpreter fails due to Docker unavailability, retry without it.
    """
    # Apply policy before initializing agent.
    apply_runtime_policy()

    # Warm up Docker first. This helps avoid false timeout on cold start.
    try:
        subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=20,
            encoding='utf-8',
            errors='replace'
        )
    except Exception:
        # Ignore warmup failure here; fallback logic below handles it.
        pass

    try:
        return base.init_agent_service(), False
    except Exception as e:
        err = str(e)
        docker_related = (
            'Docker command timed out' in err
            or 'Please check Docker installation' in err
            or 'docker' in err.lower()
        )
        if not docker_related:
            raise

        original_tools = list(getattr(base, 'tools', []))
        fallback_tools = [t for t in original_tools if t != 'code_interpreter']
        if not fallback_tools:
            raise RuntimeError('智能体初始化失败：Docker 不可用且无可用降级工具。') from e

        print('检测到 Docker 不可用，已自动禁用 code_interpreter，使用降级工具集启动。')
        base.tools = fallback_tools
        try:
            return base.init_agent_service(), True
        finally:
            # Restore global state to avoid side effects in later runs/imports.
            base.tools = original_tools


def _extract_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and 'text' in item:
                parts.append(str(item.get('text', '')))
            else:
                parts.append(str(item))
        return '\n'.join([p for p in parts if p])
    if isinstance(value, dict):
        if 'text' in value:
            return str(value.get('text', ''))
        return str(value)
    return str(value)


def _merge_stream_text(existing: str, incoming: str) -> str:
    # Compatible with both delta-stream and full-text-stream responses.
    if not incoming:
        return existing
    if incoming == existing:
        return existing
    if existing.endswith(incoming):
        return existing
    if incoming.startswith(existing):
        return incoming
    if existing.startswith(incoming):
        return existing
    # Merge by maximal suffix/prefix overlap to avoid duplicated segments.
    max_overlap = min(len(existing), len(incoming))
    for i in range(max_overlap, 0, -1):
        if existing.endswith(incoming[:i]):
            return existing + incoming[i:]
    return existing + incoming


def _extract_display_text_from_chunk(chunk: Any) -> str:
    """Render chunk similarly to official WebUI (tool-call aware)."""
    if not chunk:
        return ''
    try:
        display_msgs = convert_fncall_to_text(chunk)
    except Exception:
        display_msgs = chunk

    if not isinstance(display_msgs, list):
        return _extract_text(display_msgs)

    for msg in reversed(display_msgs):
        if isinstance(msg, dict) and 'content' in msg:
            return _extract_text(msg.get('content', ''))
    return ''


def _clean_visible_text(text: str) -> str:
    if not text:
        return ''
    # Hide tool-call trace blocks for end users.
    text = re.sub(r'<details>.*?</details>', '', text, flags=re.S | re.I)
    text = re.sub(r'<tool_call.*?>', '', text, flags=re.I)
    text = re.sub(r'^\s*Start calling tool.*$', '', text, flags=re.M)
    text = re.sub(r'^\s*Finished tool calling.*$', '', text, flags=re.M)
    return text.strip()


def _extract_final_answer(final_responses: Any, fallback_text: str = '') -> str:
    # Prefer assistant final content.
    try:
        display_msgs = convert_fncall_to_text(final_responses) if final_responses else []
    except Exception:
        display_msgs = final_responses or []

    if isinstance(display_msgs, list):
        for msg in reversed(display_msgs):
            if not isinstance(msg, dict):
                continue
            if str(msg.get('role', '')).lower() == 'assistant':
                cleaned = _clean_visible_text(_extract_text(msg.get('content', '')))
                if cleaned:
                    return cleaned

    # If assistant did not provide final summary, show the latest function output.
    if isinstance(final_responses, list):
        for msg in reversed(final_responses):
            if not isinstance(msg, dict):
                continue
            if str(msg.get('role', '')).lower() == 'function':
                tool_out = _extract_text(msg.get('content', ''))
                tool_out = tool_out.strip()
                if tool_out:
                    return f'已调用检索工具，但模型未生成总结。以下是工具原始返回：\n\n{tool_out}'

    cleaned_fallback = _clean_visible_text(fallback_text)
    if cleaned_fallback:
        return cleaned_fallback
    return '已调用检索工具，但未得到可展示结果。请稍后重试，或检查 Tavily 返回是否为空。'


def respond(
    user_text: str,
    chat_history: List[List[Optional[str]]],
    messages: List[Dict[str, Any]],
    bot: Any,
):
    user_text = (user_text or '').strip()
    chat_history = chat_history or []
    messages = messages or []

    if not user_text:
        yield '', chat_history, messages, '请输入问题后再发送。'
        return

    chat_history.append([user_text, ''])
    messages.append({'role': 'user', 'content': user_text})

    yield '', chat_history, messages, '正在检索本地条款和外部信息，请稍候...'

    run_messages = list(messages)
    final_responses = None

    try:
        for chunk in bot.run(messages=run_messages):
            if not chunk:
                continue
            final_responses = chunk
            yield '', chat_history, messages, '正在联网检索并整理结果...'

        answer = _extract_final_answer(final_responses)
        chat_history[-1][1] = answer
        if final_responses:
            messages.extend(final_responses)
        else:
            fallback = answer or '暂时没有生成有效回复，请稍后再试。'
            messages.append({'role': 'assistant', 'content': fallback})

        yield '', chat_history, messages, '已完成。'

    except Exception as e:
        err = f'处理失败: {e}'
        chat_history[-1][1] = err
        messages.append({'role': 'assistant', 'content': err})
        yield '', chat_history, messages, err


def clear_conversation():
    return [], [], '会话已清空。'


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return int(s.getsockname()[1])


def app_gui(server_name: str = '127.0.0.1', server_port: int = 7860):
    print('\n正在启动专业版 Gradio 界面...')
    bot, degraded = init_agent_service_safe()
    
    def respond_with_bot(user_text, chat_history, messages):
        yield from respond(user_text, chat_history, messages, bot)

    logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')

    with gr.Blocks(title='AI保险咨询助手 Pro', css=CUSTOM_CSS) as demo:
        messages_state = gr.State([])

        with gr.Column(elem_classes='page-wrap'):
            with gr.Row():
                with gr.Column(scale=5):
                    gr.HTML(
                        '<div class="hero">'
                        '<div class="hero-title">AI保险咨询助手 Pro</div>'
                        '<div class="hero-subtitle">本地保险知识库 + 实时网络检索增强，提供结构化、可追溯、专业化咨询建议。</div>'
                        '</div>'
                    )
                with gr.Column(scale=1, min_width=140):
                    if os.path.exists(logo_path):
                        gr.Image(value=logo_path, show_label=False, interactive=False, container=False)

            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        elem_id='chatbot',
                        label='咨询对话',
                        height=620,
                        bubble_full_width=False,
                        show_copy_button=True,
                    )

                    user_input = gr.Textbox(
                        label='请输入你的保险问题',
                        placeholder='例如：我们是跨境电商企业，如何配置责任险和雇主责任险？',
                        lines=3,
                    )

                    with gr.Row():
                        send_btn = gr.Button('发送咨询', variant='primary')
                        clear_btn = gr.Button('清空会话')

                    initial_status = '系统就绪。'
                    if degraded:
                        initial_status = '系统就绪（已自动禁用 code_interpreter：当前环境 Docker 不可用）。'
                    status_box = gr.Markdown(initial_status, elem_id='status-box')

                with gr.Column(scale=1):
                    with gr.Group(elem_classes='side-card'):
                        gr.Markdown(
                            '### 使用建议\n'
                            '- 先说明你的行业、规模与核心风险\n'
                            '- 如涉及理赔，尽量提供事故时间与责任主体\n'
                            '- 涉及政策时，建议补充适用地区与时间范围'
                        )

                    with gr.Group(elem_classes='side-card'):
                        gr.Markdown('### 常见问题示例')
                        gr.Examples(
                            examples=SUGGESTIONS,
                            inputs=user_input,
                            label=None,
                        )

                    with gr.Group(elem_classes='side-card'):
                        gr.Markdown(
                            '### 信息说明\n'
                            '- 优先基于本地保险文档回答\n'
                            '- 必要时调用网络搜索补充最新信息\n'
                            '- 输出内容用于咨询参考，不替代正式投保/核保结论'
                        )

        send_btn.click(
            fn=respond_with_bot,
            inputs=[user_input, chatbot, messages_state],
            outputs=[user_input, chatbot, messages_state, status_box],
            queue=True,
            api_name=False,
            preprocess=True,
            postprocess=True,
            show_progress='minimal',
            concurrency_limit=8,
        )

        user_input.submit(
            fn=respond_with_bot,
            inputs=[user_input, chatbot, messages_state],
            outputs=[user_input, chatbot, messages_state, status_box],
            queue=True,
            api_name=False,
            preprocess=True,
            postprocess=True,
            show_progress='minimal',
            concurrency_limit=8,
        )

        clear_btn.click(
            fn=clear_conversation,
            inputs=None,
            outputs=[chatbot, messages_state, status_box],
            queue=False,
        )

    print(f'Web 界面已就绪: http://{server_name}:{server_port}')
    try:
        demo.queue(default_concurrency_limit=8).launch(server_name=server_name, server_port=server_port)
    except OSError as e:
        if 'Cannot find empty port' not in str(e):
            raise
        fallback_port = _find_free_port()
        print(f'端口 {server_port} 已占用，自动切换到: http://{server_name}:{fallback_port}')
        demo.queue(default_concurrency_limit=8).launch(server_name=server_name, server_port=fallback_port)


def app_terminal():
    """Terminal mode with Docker fallback."""
    bot, degraded = init_agent_service_safe()
    messages: List[Dict[str, Any]] = []

    print('\n欢迎使用 AI 保险咨询助手 Pro（终端模式）')
    if degraded:
        print('提示：当前 Docker 不可用，已自动禁用 code_interpreter。')
    print("输入 'exit' 或 'quit' 退出。\n")

    while True:
        try:
            query = input('你的问题：').strip()
            if query.lower() in ('exit', 'quit'):
                print('已退出。')
                break
            if not query:
                continue

            messages.append({'role': 'user', 'content': query})
            print('\n助手：', end='', flush=True)

            final_responses = None
            for chunk in bot.run(messages=messages):
                if not chunk:
                    continue
                final_responses = chunk
                text = _extract_text(chunk[0].get('content', ''))
                if text:
                    print(text, end='', flush=True)

            if final_responses:
                messages.extend(final_responses)

            print('\n')
        except KeyboardInterrupt:
            print('\n已中断。')
            break
        except Exception as e:
            print(f'\n处理失败: {e}\n')


def main():
    parser = argparse.ArgumentParser(description='AI 保险咨询助手 Pro - 自定义 Gradio 界面版')
    parser.add_argument('--mode', type=str, default='gui', choices=['gui', 'terminal'], help='运行模式')
    parser.add_argument('--init-es', action='store_true', help='启动前初始化并预加载 Elasticsearch 索引')
    parser.add_argument('--server-name', type=str, default='127.0.0.1', help='Web 服务监听地址')
    parser.add_argument('--server-port', type=int, default=7860, help='Web 服务端口')
    args = parser.parse_args()

    print('\n【环境检查】')
    if os.getenv('DASHSCOPE_API_KEY'):
        print('DASHSCOPE_API_KEY 已配置')
    else:
        print('DASHSCOPE_API_KEY 未配置')
        sys.exit(1)

    if args.init_es:
        es_manager = base.init_elasticsearch_index()
        if es_manager:
            base.preload_documents_to_es(es_manager)

    if args.mode == 'terminal':
        app_terminal()
    else:
        app_gui(server_name=args.server_name, server_port=args.server_port)


if __name__ == '__main__':
    main()
