"""Bound demo amounts; SQLite Numeric is not an exact decimal ledger."""
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator

QUANTUM = Decimal('0.0001')
MAX_AMOUNT = Decimal('999999.9999')

def normalize_money(value):
    if isinstance(value, (float, bool)) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('money requires Decimal, string or integer')
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
        raise ValueError('money must be finite and between 0 and 999999.9999')
    return amount.quantize(QUANTUM, rounding=ROUND_HALF_UP)

class Money(TypeDecorator):
    impl = Numeric(18, 4)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else normalize_money(value)
