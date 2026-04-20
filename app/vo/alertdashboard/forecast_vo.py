from pydantic import BaseModel, Field


class ForecastDataVO(BaseModel):
    """需求预测数据视图对象"""
    productCode: str = Field(..., description="产品编码")
    productName: str = Field(..., description="产品名称")
    months: dict = Field(default_factory=dict, description="月份需求数据，key为月份(YYYY-MM)，value为需求量")


class ForecastResponseVO(BaseModel):
    """需求预测响应视图对象"""
    months: list[str] = Field(..., description="月份列表")
    data: list[ForecastDataVO] = Field(..., description="预测数据列表")
