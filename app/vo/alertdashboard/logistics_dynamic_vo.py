from pydantic import BaseModel, ConfigDict, Field


class LogisticsDynamicVO(BaseModel):
    """物流动态数据模型"""
    model_config = ConfigDict(populate_by_name=True, alias_generator=None)

    id: str = Field(..., description="物流单号")
    time: str = Field(..., description="时间，格式：HH:mm")
    carrier: str = Field(..., description="承运商")
    from_: str = Field(..., description="发货地", alias="from")
    to: str = Field(..., description="收货地")
    material: str = Field(..., description="物料名称")
    status: str = Field(..., description="状态（在途、已到达、清关中、延误等）")
    po: str = Field(..., description="采购订单号")
