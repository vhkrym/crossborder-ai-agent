"""Commerce facts use store-local business dates and Decimal monetary values."""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.core.money import Money

class Store(Base):
    __tablename__ = 'stores'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    marketplace: Mapped[str] = mapped_column(String(50))
    market: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3))

class Product(Base):
    __tablename__ = 'products'
    __table_args__ = (UniqueConstraint('store_id', 'sku', name='uq_products_store_sku'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey('stores.id', ondelete='RESTRICT'))
    sku: Mapped[str] = mapped_column(String(100))

class ProductFact:
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey('stores.id', ondelete='RESTRICT'))
    sku: Mapped[str] = mapped_column(String(100))


def product_fk(name):
    return ForeignKeyConstraint(['store_id', 'sku'], ['products.store_id', 'products.sku'], name=name, ondelete='RESTRICT')

class SalesRecord(ProductFact, Base):
    __tablename__ = 'sales_records'
    __table_args__ = (product_fk('fk_sales_product'),
        CheckConstraint('quantity >= 0 AND gross_sales >= 0 AND refund_amount >= 0', name='ck_sales_nonnegative'),
        Index('ix_sales_store_sku_date', 'store_id', 'sku', 'record_date'),
        Index('ix_sales_store_date', 'store_id', 'record_date'))
    record_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[int] = mapped_column(Integer)
    gross_sales: Mapped[Decimal] = mapped_column(Money())
    refund_amount: Mapped[Decimal] = mapped_column(Money())
    currency: Mapped[str] = mapped_column(String(3))

class AdRecord(ProductFact, Base):
    __tablename__ = 'ad_records'
    __table_args__ = (product_fk('fk_ads_product'),
        CheckConstraint('spend >= 0 AND attributed_sales >= 0 AND clicks >= 0 AND orders >= 0', name='ck_ads_nonnegative'),
        Index('ix_ads_store_sku_date', 'store_id', 'sku', 'record_date'))
    record_date: Mapped[date] = mapped_column(Date)
    spend: Mapped[Decimal] = mapped_column(Money())
    attributed_sales: Mapped[Decimal] = mapped_column(Money())
    clicks: Mapped[int] = mapped_column(Integer)
    orders: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))

class InventorySnapshot(ProductFact, Base):
    __tablename__ = 'inventory_snapshots'
    __table_args__ = (product_fk('fk_inventory_product'),
        UniqueConstraint('store_id', 'sku', 'snapshot_date', name='uq_inventory_product_date'),
        CheckConstraint('on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand AND inbound >= 0 AND lead_time_days >= 0', name='ck_inventory_valid'))
    snapshot_date: Mapped[date] = mapped_column(Date)
    on_hand: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer)
    inbound: Mapped[int] = mapped_column(Integer)
    lead_time_days: Mapped[int] = mapped_column(Integer)

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved

class CostRecord(ProductFact, Base):
    __tablename__ = 'cost_records'
    __table_args__ = (product_fk('fk_cost_product'),
        UniqueConstraint('store_id', 'sku', 'effective_from', name='uq_cost_product_effective'),
        CheckConstraint('purchase_cost >= 0 AND logistics_cost >= 0 AND platform_fee_per_unit >= 0', name='ck_cost_nonnegative'))
    effective_from: Mapped[date] = mapped_column(Date)
    purchase_cost: Mapped[Decimal] = mapped_column(Money())
    logistics_cost: Mapped[Decimal] = mapped_column(Money())
    platform_fee_per_unit: Mapped[Decimal] = mapped_column(Money())
    currency: Mapped[str] = mapped_column(String(3))

class DataImport(Base):
    __tablename__ = 'data_imports'
    __table_args__ = (
        UniqueConstraint('store_id', 'source_type', 'data_type', 'file_hash', name='uq_import_identity'),
        CheckConstraint("source_type IN ('file', 'api')", name='ck_import_source'),
        CheckConstraint("length(file_hash) = 64 AND file_hash NOT GLOB '*[^0-9a-f]*'", name='ck_import_hash'),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='ck_import_status'),
        CheckConstraint("data_type IN ('stores', 'products', 'sales_records', 'ad_records', 'inventory_snapshots', 'cost_records')", name='ck_import_type'),
        CheckConstraint('total_rows >= 0 AND success_rows >= 0 AND failed_rows >= 0 AND success_rows + failed_rows <= total_rows', name='ck_import_counts'))
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey('stores.id', ondelete='RESTRICT'))
    source_type: Mapped[str] = mapped_column(String(20), default='file')
    file_hash: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    total_rows: Mapped[int] = mapped_column(default=0)
    success_rows: Mapped[int] = mapped_column(default=0)
    failed_rows: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
