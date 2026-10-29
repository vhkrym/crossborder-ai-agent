from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import CostRecord


def get_applicable_cost(session: Session, store_id: int, sku: str, business_date: date) -> CostRecord | None:
    """Latest cost effective on or before business_date; None means missing cost."""
    return session.scalar(select(CostRecord).where(
        CostRecord.store_id == store_id, CostRecord.sku == sku,
        CostRecord.effective_from <= business_date,
    ).order_by(CostRecord.effective_from.desc()).limit(1))
