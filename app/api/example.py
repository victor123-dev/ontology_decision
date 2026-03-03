from fastapi import APIRouter

router = APIRouter()


@router.get("/example")
def get_example():
    """示例API端点"""
    return {"message": "Hello from example endpoint"}


@router.post("/example")
def create_example(data: dict):
    """示例POST端点"""
    return {"message": "Example created", "data": data}
