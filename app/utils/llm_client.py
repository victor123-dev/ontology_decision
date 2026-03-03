import json
from openai import AzureOpenAI
from openai.resources.chat import Chat, Completions


from app.utils.logger import get_llm_logger
from app.config import settings

llm_logger = get_llm_logger()

class ChatCompletionsWrapper:
    """
    包装ChatCompletions类，添加日志记录
    """
    def __init__(self, chat_completions: Completions):
        self.chat_completions = chat_completions
    
    def create(self, **kwargs):
        """
        包装create方法，添加日志记录
        
        Args:
            **kwargs: 传递给create的参数
            
        Returns:
            大模型响应
        """
        # 处理请求参数，只保留业务相关信息
        request_log = {
            "model": kwargs.get("model"),
            "messages": kwargs.get("messages"),
            "tools": kwargs.get("tools"),
            "tool_choice": kwargs.get("tool_choice"),
            "temperature": kwargs.get("temperature"),
            "top_p": kwargs.get("top_p"),
            "max_tokens": kwargs.get("max_tokens"),
            "n": kwargs.get("n")
        }
        # 移除None值
        request_log = {k: v for k, v in request_log.items() if v is not None}
        
        # 记录请求参数
        llm_logger.debug(f"LLM API请求参数: {json.dumps(request_log, ensure_ascii=False, indent=2)}")
        
        # 调用实际的API
        response = self.chat_completions.create(**kwargs)
        
        # 处理响应，只保留业务相关信息
        response_dict = response.model_dump()
        response_log = {}
        
        # 保留choices字段，但过滤掉非业务信息
        if "choices" in response_dict:
            response_log["choices"] = []
            for choice in response_dict["choices"]:
                choice_log = {}
                # 保留message字段
                if "message" in choice:
                    choice_log["message"] = choice["message"]
                # 保留finish_reason和index字段
                if "finish_reason" in choice:
                    choice_log["finish_reason"] = choice["finish_reason"]
                if "index" in choice:
                    choice_log["index"] = choice["index"]
                response_log["choices"].append(choice_log)
        
        # 记录响应
        llm_logger.debug(f"LLM API响应: {json.dumps(response_log, ensure_ascii=False, indent=2)}")
        
        return response
    
    def __getattr__(self, name):
        """
        代理其他方法调用到原始ChatCompletions对象
        """
        return getattr(self.chat_completions, name)

class ChatWrapper:
    """
    包装Chat类，返回ChatCompletionsWrapper实例
    """
    def __init__(self, chat: Chat):
        self.chat = chat
    
    @property
    def completions(self):
        """
        返回包装后的completions对象
        """
        return ChatCompletionsWrapper(self.chat.completions)
    
    def __getattr__(self, name):
        """
        代理其他方法调用到原始Chat对象
        """
        return getattr(self.chat, name)

class LLMClient:
    """
    OpenAI客户端包装类，用于统一处理大模型调用的日志记录
    """
    
    def __init__(self):
        # 初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )
    
    @property
    def chat(self):
        """
        返回包装后的chat对象
        """
        return ChatWrapper(self.client.chat)
    

    
    def __getattr__(self, name):
        """
        代理其他方法调用到原始客户端
        """
        return getattr(self.client, name)

# 创建单例实例（仅当配置存在时）
llm_client = None
if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_API_VERSION:
    try:
        llm_client = LLMClient()
    except Exception as e:
        llm_logger.error(f"初始化LLM客户端失败: {str(e)}")
        llm_client = None