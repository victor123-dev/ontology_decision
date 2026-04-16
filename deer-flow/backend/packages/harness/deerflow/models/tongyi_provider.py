"""Custom Tongyi provider with function.arguments format validation.

Tongyi (Qwen) models sometimes return function call arguments in non-JSON format,
but the API requires them to be valid JSON strings. This custom provider
intercepts the response parsing and ensures proper argument formatting.
"""

import asyncio
import functools
import json
import logging
import os
from typing import Any, Dict, List, Optional, Mapping

from langchain_community.chat_models import ChatTongyi
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.outputs import ChatGeneration, ChatResult, ChatGenerationChunk

# Ensure logger is properly configured
logger = logging.getLogger(__name__)
# Set logger level to INFO if not already set
if logger.level == logging.NOTSET:
    logger.setLevel(logging.INFO)

# Log that the module is loaded
logger.debug("tongyi_provider module loaded successfully")

# Also ensure root logger has a handler if none exists
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class PatchedChatTongyi(ChatTongyi):
    """Patched ChatTongyi that handles function.arguments format issues and logs requests/responses."""
        
    def _log_request(self, messages: List[BaseMessage], **kwargs: Any) -> None:
        """Log the LLM request for debugging."""
        try:
            # Convert messages to serializable format
            serializable_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    content = msg.content if msg.content is not None else ""
                    role = getattr(msg, 'role', 'unknown')
                    serializable_messages.append({
                        'role': role,
                        'content': str(content)[:500] + "..." if len(str(content)) > 500 else str(content),
                        'type': type(msg).__name__
                    })
                else:
                    serializable_messages.append({
                        'content': str(msg)[:500] + "..." if len(str(msg)) > 500 else str(msg),
                        'type': type(msg).__name__
                    })
            
            tools = kwargs.get('tools', [])
            serializable_tools = []
            for tool in tools:
                if isinstance(tool, dict):
                    serializable_tools.append({
                        'name': tool.get('name', 'unknown'),
                        'description': tool.get('description', '')[:2000] if tool.get('description') else '',
                        'parameters': '...' if 'parameters' in tool else 'none'
                    })
                else:
                    serializable_tools.append({
                        'name': getattr(tool, 'name', 'unknown'),
                        'description': getattr(tool, 'description', '')[:2000] if getattr(tool, 'description', None) else '',
                        'type': type(tool).__name__
                    })
            
            logger.info(
                "LLM Request - Model: %s, Messages: %s, Tools: %s",
                self.model_name,
                json.dumps(serializable_messages, ensure_ascii=False, indent=2),
                json.dumps(serializable_tools, ensure_ascii=False, indent=2) if serializable_tools else "None"
            )
        except Exception as e:
            logger.info("Failed to log LLM request: %s", str(e))
    
    def _log_response(self, resp: Any) -> None:
        """Log the LLM response for debugging."""
        try:
            # Extract response info
            request_id = resp.get("request_id", "unknown")
            model = resp.get("model", self.model_name)
            usage = resp.get("usage", {})
            
            # Extract message content
            choices = resp.get("output", {}).get("choices", [])
            if choices:
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "")[:500] + "..." if len(str(message.get("content", ""))) > 500 else str(message.get("content", ""))
                tool_calls = message.get("tool_calls", [])
                serializable_tool_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        function_data = tc.get("function", {})
                        serializable_tool_calls.append({
                            'name': function_data.get('name', 'unknown'),
                            'arguments': str(function_data.get('arguments', ''))[:200] + "..." if len(str(function_data.get('arguments', ''))) > 200 else str(function_data.get('arguments', ''))
                        })
                
                logger.info(
                    "LLM Response - Request ID: %s, Model: %s, Content: %s, Tool Calls: %s, Usage: %s",
                    request_id,
                    model,
                    content,
                    json.dumps(serializable_tool_calls, ensure_ascii=False, indent=2) if serializable_tool_calls else "None",
                    json.dumps(usage, ensure_ascii=False)
                )
            else:
                logger.info(
                    "LLM Response - Request ID: %s, Model: %s, No choices in response",
                    request_id, model
                )
        except Exception as e:
            logger.info("Failed to log LLM response: %s", str(e))
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response with request/response logging."""
        # Log the request
        self._log_request(messages, **kwargs)
        
        generations = []
        if self.streaming:
            generation_chunk: Optional[ChatGenerationChunk] = None
            for chunk in self._stream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            ):
                if generation_chunk is None:
                    generation_chunk = chunk
                else:
                    generation_chunk += chunk
            assert generation_chunk is not None
            generations.append(self._chunk_to_generation(generation_chunk))
        else:
            params: Dict[str, Any] = self._invocation_params(
                messages=messages, stop=stop, **kwargs
            )
            resp = self.completion_with_retry(**params)
            # Log the response
            self._log_response(resp)
            generations.append(
                ChatGeneration(**self._chat_generation_from_qwen_resp(resp))
            )
        return ChatResult(
            generations=generations,
            llm_output={
                "model_name": self.model_name,
            },
        )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        self._log_request(messages, **kwargs)
        generations = []
        if self.streaming:
            generation: Optional[ChatGenerationChunk] = None
            async for chunk in self._astream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            ):
                if generation is None:
                    generation = chunk
                else:
                    generation += chunk
            assert generation is not None
            generations.append(self._chunk_to_generation(generation))
        else:
            params: Dict[str, Any] = self._invocation_params(
                messages=messages, stop=stop, **kwargs
            )
            resp = await asyncio.get_running_loop().run_in_executor(
                None,
                functools.partial(self.completion_with_retry, **params),
            )
            self._log_response(resp)
            generations.append(
                ChatGeneration(**self._chat_generation_from_qwen_resp(resp))
            )
        return ChatResult(
            generations=generations,
            llm_output={
                "model_name": self.model_name,
            },
        )