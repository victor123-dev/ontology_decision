from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import StreamingResponse
import time
import json
from app.utils.logger import get_logger, get_request_logger

logger = get_logger(__name__)
request_logger = get_request_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"
        
        # 仅保留关键请求头
        key_headers = {
            "content-type": request.headers.get("content-type"),
            "authorization": request.headers.get("authorization")[:20] + "..." if request.headers.get("authorization") else None
        }
        
        # 获取请求基本信息
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "headers": key_headers
        }
        
        try:
            # 读取请求体
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        # 尝试解析为JSON
                        try:
                            request_info["body"] = json.loads(body.decode("utf-8"))
                        except json.JSONDecodeError:
                            # 如果不是JSON，记录原始内容（限制长度）
                            request_info["body"] = body.decode("utf-8")[:200]  # 限制长度为200字符
                except Exception as e:
                    request_info["body"] = f"无法读取请求体: {str(e)}"
            
            request_logger.debug(f"请求详情: {json.dumps(request_info, ensure_ascii=False)}")

            # 处理请求
            response = await call_next(request)
            
            # 计算请求处理时间
            process_time = time.time() - start_time
            
            # 检查是否为流式响应（同时考虑fastapi和starlette的流式响应类型）
            is_streaming = isinstance(response, StreamingResponse) or hasattr(response, 'body_iterator')
            
            # 根据响应类型处理
            if is_streaming:

                # 记录响应信息（不包含完整响应体，因为是流式）
                response_info = {
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}秒",
                    "body": "[StreamingResponse - 流式响应]",
                    "media_type": response.media_type
                }
                
                request_logger.debug(f"流式响应详情: {json.dumps(response_info, ensure_ascii=False)}")
                
                # 创建一个异步生成器来记录流式内容
                async def logging_body_iterator():
                    buffer = b""
                    
                    async for chunk in response.body_iterator:
                        buffer += chunk
                        
                        # 检查是否包含完整的SSE事件（以\n\n结尾）
                        while b"\n\n" in buffer:
                            event, buffer = buffer.split(b"\n\n", 1)
                            if event.strip():
                                try:
                                    event_str = event.decode("utf-8", errors="replace")
                                    request_logger.debug(f"流式响应事件: {event_str}")
                                except Exception as e:
                                    request_logger.debug(f"无法解析流式事件: {str(e)}")
                        
                        yield chunk
                    
                    # 记录剩余的内容（如果有的话）
                    if buffer.strip():
                        try:
                            buffer_str = buffer.decode("utf-8", errors="replace")
                            request_logger.debug(f"流式响应剩余内容: {buffer_str}")
                        except Exception as e:
                            request_logger.debug(f"无法解析剩余流式内容: {str(e)}")

                # 返回包装后的StreamingResponse
                return StreamingResponse(
                    logging_body_iterator(),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            else:
                # 处理普通响应
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                # 重新构造响应，避免后续无法读取
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # 尝试解析响应体
                try:
                    response_content = json.loads(response_body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    response_content = response_body.decode("utf-8", errors="replace")[:500]  # 限制长度
                
                # 记录响应信息
                response_info = {
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}秒",
                    "body": response_content
                }
                
                request_logger.debug(f"响应详情: {json.dumps(response_info, ensure_ascii=False)}")
                
                return response
            
        except Exception as e:
            # 记录异常信息
            process_time = time.time() - start_time
            request_logger.error(
                f"请求处理异常: {request.method} {request.url.path} | "
                f"处理时间: {process_time:.3f}秒 | 异常: {str(e)}"
            )
            request_logger.debug(f"请求详情: {json.dumps(request_info, ensure_ascii=False)}")
            raise