"""多轮对话测试脚本 - 测试 DeerFlow Gateway 的流式 API 接口。

测试场景：
1. 第一轮对话：不传 thread_id，验证系统自动生成
2. 从 SSE 响应中解析 thread_id
3. 第二轮对话：使用上一轮的 thread_id，验证上下文保持
4. 第三轮对话：继续复用 thread_id，验证多轮对话连贯性

使用方法：
    python test_multi_turn_conversation.py
    
环境变量：
    GATEWAY_URL: Gateway 服务地址（默认 http://localhost:8001）
"""

import json
import os
import sys
from typing import Any, Generator

import httpx

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8001")
STREAM_ENDPOINT = f"{GATEWAY_URL}/api/runs/stream"
REQUEST_TIMEOUT = 120.0  # 秒


# ---------------------------------------------------------------------------
# SSE 解析器
# ---------------------------------------------------------------------------


def parse_sse_stream(response: httpx.Response) -> Generator[tuple[str, str, Any], None, None]:
    """解析 SSE 流，yield (event_id, event_type, data) 元组。"""
    event_id = None
    event_type = None
    data_buffer = []
    
    for line in response.iter_lines():
        line = line.strip()
        
        if not line:
            if event_type and data_buffer:
                full_data = "\n".join(data_buffer)
                try:
                    parsed_data = json.loads(full_data)
                    yield event_id, event_type, parsed_data
                except json.JSONDecodeError:
                    yield event_id, event_type, full_data
                event_id = None
                event_type = None
                data_buffer = []
            continue
        
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_buffer.append(line[5:].strip())
        elif line.startswith("id:"):
            event_id = line[3:].strip()
    
    if event_type and data_buffer:
        full_data = "\n".join(data_buffer)
        try:
            yield event_id, event_type, json.loads(full_data)
        except json.JSONDecodeError:
            yield event_id, event_type, full_data


def extract_thread_id_from_sse(response: httpx.Response) -> str | None:
    """从 SSE 响应中提取 thread_id。"""
    for event_id, event_type, data in parse_sse_stream(response):
        if event_type == "metadata" and isinstance(data, dict):
            thread_id = data.get("thread_id")
            if thread_id:
                return str(thread_id)
    
    content_location = response.headers.get("Content-Location", "")
    if content_location:
        parts = content_location.split("/")
        if len(parts) >= 5 and parts[3] == "threads":
            return parts[4]
    
    return None


def stream_with_live_print(response: httpx.Response) -> tuple[str, str | None]:
    """实时打印流式输出，并收集最终结果。
    
    Returns:
        tuple: (最终AI回复内容, thread_id)
    """
    thread_id = None
    last_ai_message = ""
    current_text_buffer = {}  # 按 message_id 累积文本
    
    print("\n🤖 AI 正在回复:")
    print("-" * 80)
    
    for event_id, event_type, data in parse_sse_stream(response):
        # print(f"\n[event_id: {event_id}, event_type: {event_type}], {data}")
        # 提取 thread_id
        if event_type == "metadata" and isinstance(data, dict):
            thread_id = data.get("thread_id")
            if thread_id:
                print(f"\n✅ Thread ID: {thread_id}")
        
        # 处理流式文本增量
        elif event_type == "messages":
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("type") == "AIMessageChunk":
                        content = item.get("content", "")
                        msg_id = item.get("id", "unknown")
                        
                        if isinstance(content, str) and content:
                            # 累积文本
                            current_text_buffer[msg_id] = current_text_buffer.get(msg_id, "") + content
                            # 实时打印增量
                            print(content, end="", flush=True)
                            last_ai_message = current_text_buffer[msg_id]
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    text = part.get("text", "")
                                    if text:
                                        current_text_buffer[msg_id] = current_text_buffer.get(msg_id, "") + text
                                        print(text, end="", flush=True)
                                        last_ai_message = current_text_buffer[msg_id]
        
        # 处理完整状态快照
        elif event_type == "values" and isinstance(data, dict):
            messages = data.get("messages", [])
            for msg in messages:
                if isinstance(msg, dict) and msg.get("type") == "ai":
                    content = msg.get("content", "")
                    msg_id = msg.get("id", "")
                    
                    if isinstance(content, str) and content:
                        current_text_buffer[msg_id] = content
                        last_ai_message = content
                    elif isinstance(content, list):
                        text_parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                        full_text = "\n".join(text_parts)
                        if full_text:
                            current_text_buffer[msg_id] = full_text
                            last_ai_message = full_text
        
        # 处理错误
        elif event_type == "error":
            print(f"\n\n❌ 错误: {data}")
    
    print("\n" + "-" * 80)
    
    # 从缓冲区获取最终的完整回复
    if current_text_buffer:
        last_message_id = list(current_text_buffer.keys())[-1]
        last_ai_message = current_text_buffer[last_message_id]
    
    return last_ai_message, thread_id


# ---------------------------------------------------------------------------
# 对话函数
# ---------------------------------------------------------------------------


def send_message(
    message: str,
    thread_id: str | None = None,
    assistant_id: str = "lead_agent",
) -> tuple[str, str | None]:
    """发送消息到 DeerFlow 并获取回复。"""
    payload: dict[str, Any] = {
        "assistant_id": assistant_id,
        "input": {
            "messages": [
                {"role": "human", "content": message}
            ]
        },
        "stream_mode": ["values", "messages-tuple"],
    }
    
    payload["config"] = {
        "configurable": {
            'model_name': 'mimo-v2.5-pro',
            'mode': 'flash',
            'reasoning_effort': 'minimal',
            'thinking_enabled': False,
            'is_plan_mode': False,
            'subagent_enabled': False,
            'graph_id': 'lead_agent',
        }
    }
    
    # 如果有 thread_id，则添加到配置中
    if thread_id:
        payload["config"]["configurable"]["thread_id"] = thread_id
    
    print(f"\n{'='*80}")
    if thread_id:
        print(f"📍 使用已有 thread: {thread_id}")
    else:
        print(f"🆕 创建新 thread")
    print(f"👤 用户: {message}")
    print(f"{'='*80}")
    
    try:
        with httpx.stream(
            "POST",
            STREAM_ENDPOINT,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            
            # 实时打印流式输出并收集结果
            ai_response, returned_thread_id = stream_with_live_print(response)
            
            if not thread_id and returned_thread_id:
                print(f"\n✅ 新 thread 已创建: {returned_thread_id}")
            
            if ai_response:
                print(f"\n📝 最终回复长度: {len(ai_response)} 字符")
            else:
                print(f"\n⚠️  未获取到 AI 回复")
            
            return ai_response, returned_thread_id or thread_id
            
    except httpx.TimeoutException:
        print(f"\n❌ 请求超时（{REQUEST_TIMEOUT}秒）")
        return "", thread_id
    except httpx.HTTPError as e:
        print(f"\n❌ HTTP 错误: {e}")
        return "", thread_id
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return "", thread_id


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------


def test_multi_turn_conversation():
    """执行多轮对话测试。"""
    print("\n" + "="*80)
    print("🧪 DeerFlow 多轮对话测试")
    print("="*80)
    print(f"🌐 Gateway URL: {GATEWAY_URL}")
    print(f"📡 端点: {STREAM_ENDPOINT}")
    print("="*80)
    
    thread_id = None
    
    print("\n【第 1 轮对话】")
    response_1, thread_id = send_message(
        message="你好，请简单介绍一下你自己。",
        thread_id=None,
    )
    
    if not thread_id:
        print("\n❌ 测试失败：未能获取 thread_id")
        return False
    
    print(f"\n✅ 第 1 轮完成，thread_id: {thread_id}")
    
    print("\n\n【第 2 轮对话】")
    response_2, thread_id = send_message(
        message="我刚才问了什么？",
        thread_id=thread_id,
    )
    
    if "介绍" in response_2 or "自己" in response_2 or "第一" in response_2:
        print(f"\n✅ 第 2 轮完成，上下文保持良好")
    else:
        print(f"\n⚠️  第 2 轮完成，但上下文可能未正确保持")
    
    print("\n\n【第 3 轮对话】")
    response_3, thread_id = send_message(
        message="你能帮我做什么？",
        thread_id=thread_id,
    )
    
    print(f"\n✅ 第 3 轮完成")
    
    print("\n" + "="*80)
    print("📊 测试总结")
    print("="*80)
    print(f"✅ 成功完成 3 轮对话")
    print(f"✅ Thread ID: {thread_id}")
    print(f"✅ 上下文保持: {'是' if '介绍' in response_2 or '自己' in response_2 else '待验证'}")
    print("="*80)
    
    return True


def test_custom_thread_id():
    """测试使用自定义 thread_id。"""
    print("\n" + "="*80)
    print("🧪 自定义 Thread ID 测试")
    print("="*80)
    
    custom_thread_id = "my-custom-thread-001"
    
    print(f"\n【使用自定义 thread_id: {custom_thread_id}】")
    response, returned_id = send_message(
        message="这是一次使用自定义 thread_id 的测试。",
        thread_id=custom_thread_id,
    )
    
    if returned_id == custom_thread_id:
        print(f"\n✅ 自定义 thread_id 测试通过")
        return True
    else:
        print(f"\n⚠️  返回的 thread_id ({returned_id}) 与自定义的不一致")
        return False


def main():
    """主测试入口。"""
    print("\n🚀 开始 DeerFlow 多轮对话测试\n")
    
    try:
        send_message(
            message="客户AMD预订TSMC先进封装产能，导致AI芯片供应链瓶颈对我的业务有什么影响",
            thread_id=None,
        )

        # success_1 = test_multi_turn_conversation()
        
        # print("\n\n")
        # success_2 = test_custom_thread_id()
        
        print("\n\n" + "="*80)
        # if success_1 and success_2:
        #     print("🎉 所有测试通过！")
        # else:
        #     print("⚠️  部分测试未通过，请检查日志")
        # print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
