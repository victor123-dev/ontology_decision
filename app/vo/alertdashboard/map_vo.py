from pydantic import BaseModel, ConfigDict, Field


class MapNodeVO(BaseModel):
    """地图节点数据模型"""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="节点ID")
    name: str = Field(..., description="节点名称")
    type: str = Field(..., description="节点类型（factory/customer/supplier/logistics）")
    city: str = Field(..., description="所在城市")
    lat: float = Field(..., description="纬度")
    lng: float = Field(..., description="经度")


class MapRouteVO(BaseModel):
    """地图路由数据模型"""
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(..., description="起点节点ID", alias="from")
    to: str = Field(..., description="终点节点ID")
    type: str = Field(..., description="路线类型（supply/delivery/logistics）")
    active: bool = Field(..., description="是否活跃")
