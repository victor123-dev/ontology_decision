from app.utils.llm_client import LLMClient, llm_client
from app.config import settings
from typing import Optional, List, Dict

class LLMTranslator:
    def __init__(self):
        self.llm_client = llm_client
    
    def translate_to_chinese(self, text: str) -> str:
        """将英文表名或字段名翻译为中文"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        prompt = f"请将以下英文技术术语翻译为中文，保持专业准确性，不要添加任何解释：{text}"
        response = self.llm_client.chat.completions.create(
            model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    
    def generate_description(self, text: str, context: Optional[str] = None) -> str:
        """基于表名或字段名生成中文描述"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        if context:
            prompt = f"请基于以下上下文，为'{text}'生成一个简洁的中文描述（1-2句话）：{context}"
        else:
            prompt = f"请为'{text}'生成一个简洁的中文描述（1-2句话），假设它是数据库中的表名或字段名"
        
        response = self.llm_client.chat.completions.create(
            model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    
    def batch_translate(self, texts: List[str]) -> Dict[str, str]:
        """批量翻译多个英文术语为中文"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        prompt = "请将以下英文技术术语批量翻译为中文，保持专业准确性，不要添加任何英文原文或解释，只返回中文翻译结果。\n\n"
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"
        
        response = self.llm_client.chat.completions.create(
            model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手，能够批量翻译术语"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result = {}
        lines = response.choices[0].message.content.strip().split('\n')
        for i, line in enumerate(lines):
            if i < len(texts):
                # 提取翻译结果，假设格式为 "1. 翻译结果"
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    result[texts[i]] = parts[1].strip()
                else:
                    result[texts[i]] = line.strip()
        
        return result
    
    def batch_generate_descriptions(self, texts: List[str]) -> Dict[str, str]:
        """批量为多个术语生成中文描述"""
        if not self.llm_client:
            raise Exception("LLM client is not initialized")
        
        prompt = "请为以下数据库表名或字段名批量生成简洁的中文描述（每个1-2句话），只返回描述内容，不要包含字段名。\n\n"
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"
        
        response = self.llm_client.chat.completions.create(
            model=settings.AZURE_OPENAI_ADVANCED_GPT_DEPLOYMENT or settings.AZURE_OPENAI_GPT_DEPLOYMENT or "gpt-35-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的翻译和内容生成助手，能够批量生成描述"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result = {}
        lines = response.choices[0].message.content.strip().split('\n')
        for i, line in enumerate(lines):
            if i < len(texts):
                # 提取描述结果，假设格式为 "1. 描述内容"
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    result[texts[i]] = parts[1].strip()
                else:
                    result[texts[i]] = line.strip()
        
        return result
