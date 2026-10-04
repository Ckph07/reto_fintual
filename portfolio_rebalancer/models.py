"""Assets, current holdings, and desired allocations."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Stock:
    symbol: str
    price: Decimal

    def current_price(self) -> Decimal:
        """Return the latest available price (stored locally for this exercise)."""
        return self.price


@dataclass(frozen=True)
class Position:
    stock: Stock
    quantity: Decimal


@dataclass(frozen=True)
class Allocation:
    stock: Stock
    weight: Decimal
