from typing import Optional, List
from pydantic import BaseModel, Field


class CharVO(BaseModel):
    """图表数据视图对象 - 物料预测与订单对比"""
    item_code: str = Field(..., description="物料编码")
    month: str = Field(..., description="月份，格式：YYYY-MM")
    product: str = Field(..., description="产品名称")
    salesForecast: Optional[int] = Field(None, description="预测数量，无数据时为null")
    salesOrder: Optional[int] = Field(None, description="订单数量，无数据时为null")


class ChartResponseVO(BaseModel):
    """图表数据响应对象 - 包含月份列表和明细数据"""
    months: List[str] = Field(..., description="月份列表，格式：YYYY-MM")
    data: List[CharVO] = Field(..., description="图表明细数据")
