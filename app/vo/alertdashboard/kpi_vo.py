from pydantic import BaseModel, Field


class KpiMetricVO(BaseModel):
    """单个KPI指标模型"""
    val: float = Field(0, description="指标当前值")
    trendVal: float = Field(0, description="指标趋势值（环比变化）")

class MonthlySalesMetricsVO(BaseModel):
    """月销售指标模型（包含金额和数量的KPI）"""
    monthlySalesAmount: KpiMetricVO = Field(..., description="月销售金额")
    monthlySalesQty: KpiMetricVO = Field(..., description="月销售数量")
