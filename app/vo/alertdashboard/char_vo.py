from pydantic import BaseModel, Field


class CharVO(BaseModel):
    """图表数据视图对象 - 物料预测与订单对比"""
    item_code: str = Field(..., description="物料编码")
    month: str = Field(..., description="月份，格式：YYYY-MM")
    product: str = Field(..., description="产品名称")
    salesForecast: int = Field(0, description="预测数量")
    salesOrder: int = Field(0, description="订单数量")
    purchaseQty: int = Field(0, description="采购数量")
