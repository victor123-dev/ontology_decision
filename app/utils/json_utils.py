import re
import json
import logging

logger = logging.getLogger(__name__)

def extract_json_from_content(content: str) -> dict:
    """
    从文本内容中提取JSON
    
    Args:
        content: 包含JSON的内容
        
    Returns:
        提取的JSON字典
    """
    content = content.strip()
    
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON失败: {str(e)}, JSON字符串: {json_str[:100]}...")
            pass
    
    if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
        content = content[1:-1]
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    json_pattern_match = re.search(r'\{(?:[^{}]|"(?:[^"\\]|\\.)*")*\}', content)
    if json_pattern_match:
        json_str = json_pattern_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    logger.error(f"解析JSON失败，内容: {content[:100]}...")
    return {"content": content}