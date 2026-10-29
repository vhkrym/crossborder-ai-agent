from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class ProfitItem(BaseModel):
    sku: str
    quantity: int
    gross_sales: Decimal
    refund_amount: Decimal
    net_revenue: Decimal
    purchase_cost: Decimal | None
    logistics_cost: Decimal | None
    platform_fees: Decimal | None
    ad_spend: Decimal
    contribution_profit: Decimal | None
    profit_margin: Decimal | None
    cost_increased: bool
    reasons: list[str]

class AdvertisingItem(BaseModel):
    sku: str
    spend: Decimal
    attributed_sales: Decimal
    clicks: int
    ad_orders: int
    acos: Decimal | None
    roas: Decimal | None
    cpc: Decimal | None
    conversion_rate: Decimal | None
    reasons: list[str]

class InventoryItem(BaseModel):
    sku: str
    snapshot_date: date | None
    on_hand: int | None
    reserved: int | None
    available: int | None
    inbound: int | None
    lead_time_days: int | None
    observed_days: int
    average_daily_sales: Decimal | None
    coverage_days: Decimal | None
    risk: str
    suggested_replenishment: int | None
    reasons: list[str]

class OverviewSummary(BaseModel):
    net_revenue: Decimal | None
    contribution_profit: Decimal | None
    acos: Decimal | None
    inventory_risk_skus: int
    inventory_unknown_skus: int
    reasons: list[str]

class AnalysisResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    store_id: int
    currency: str
    start_date: date
    end_date: date
    units: dict[str,str] = Field(default_factory=lambda: {'money':'store currency','ratios':'fraction','inventory':'units','coverage':'days'})
    profit: list[ProfitItem] = Field(default_factory=list)
    advertising: list[AdvertisingItem] = Field(default_factory=list)
    inventory: list[InventoryItem] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    summary: OverviewSummary | None = None
    window: int | None = None
    safety_days: int | None = None
