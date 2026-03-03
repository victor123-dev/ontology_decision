from pydantic import BaseModel


class ExampleModel(BaseModel):
    """示例模型"""
    id: int
    name: str
    description: str = None
