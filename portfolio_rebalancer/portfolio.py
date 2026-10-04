"""Calculate rebalance proposals without executing trades."""

from dataclasses import dataclass
from decimal import Decimal

from .models import Allocation, Position


@dataclass
class Portfolio:
    positions: list[Position]
    allocations: list[Allocation]

    def rebalance(self) -> dict[str, Decimal]:
        """Return share deltas: positive to buy, negative to sell.

        Allocations describe fractions of total monetary value. Prices are
        read once per symbol and reused throughout this calculation. Holdings
        and targets are unchanged; zero trades are omitted.
        """
        positions = {position.stock.symbol: position for position in self.positions}
        allocations = {
            allocation.stock.symbol: allocation for allocation in self.allocations
        }
        if len(positions) != len(self.positions):
            raise ValueError("Duplicate stock symbol in positions")
        if len(allocations) != len(self.allocations):
            raise ValueError("Duplicate stock symbol in allocations")

        for position in self.positions:
            quantity = position.quantity
            if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity < 0:
                raise ValueError("Position quantities must be finite, nonnegative Decimals")
        for allocation in self.allocations:
            weight = allocation.weight
            if not isinstance(weight, Decimal) or not weight.is_finite() or weight < 0:
                raise ValueError("Allocation weights must be finite, nonnegative Decimals")
        if sum((allocation.weight for allocation in self.allocations), Decimal("0")) != 1:
            raise ValueError("Allocation weights must sum to 1")

        stocks = {
            symbol: position.stock
            for symbol, position in positions.items()
            if position.quantity > 0
        }
        if not stocks:
            # Targets alone do not provide capital to invest.
            return {}
        stocks.update(
            {
                symbol: allocation.stock
                for symbol, allocation in allocations.items()
                if allocation.weight > 0
            }
        )

        prices: dict[str, Decimal] = {}
        for symbol, stock in stocks.items():
            price = stock.current_price()
            if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
                raise ValueError(f"Price for {symbol} must be a finite, positive Decimal")
            prices[symbol] = price

        total_value = sum(
            (
                position.quantity * prices[symbol]
                for symbol, position in positions.items()
                if position.quantity > 0
            ),
            Decimal("0"),
        )

        trades: dict[str, Decimal] = {}
        for symbol, price in prices.items():
            quantity = positions[symbol].quantity if symbol in positions else Decimal("0")
            weight = allocations[symbol].weight if symbol in allocations else Decimal("0")
            if weight == 0:
                # Negate without rounding, so the entire holding is sold exactly.
                delta = quantity.copy_negate()
            else:
                target_value = total_value * weight
                delta = (target_value - quantity * price) / price
            if delta != 0:
                trades[symbol] = delta
        return trades
