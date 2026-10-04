from decimal import Decimal
from unittest.mock import patch

import pytest

from portfolio_rebalancer import Allocation, Portfolio, Position, Stock


def test_rebalance_example_preserves_inputs_and_reads_each_price_once():
    meta = Stock("META", Decimal("100"))
    aapl = Stock("AAPL", Decimal("200"))
    positions = [Position(meta, Decimal("10")), Position(aapl, Decimal("5"))]
    allocations = [Allocation(meta, Decimal("0.4")), Allocation(aapl, Decimal("0.6"))]
    portfolio = Portfolio(positions, allocations)
    original_positions = positions.copy()
    original_allocations = allocations.copy()

    with patch.object(
        Stock, "current_price", autospec=True, side_effect=lambda stock: stock.price
    ) as quote:
        assert portfolio.rebalance() == {"META": Decimal("-2"), "AAPL": Decimal("1")}

    assert quote.call_count == 2
    assert {call.args[0].symbol for call in quote.call_args_list} == {"META", "AAPL"}
    assert portfolio.positions == original_positions
    assert portfolio.allocations == original_allocations


def test_already_balanced_portfolio_has_no_trades():
    meta = Stock("META", Decimal("100"))
    aapl = Stock("AAPL", Decimal("200"))
    portfolio = Portfolio(
        [Position(meta, Decimal("8")), Position(aapl, Decimal("6"))],
        [Allocation(meta, Decimal("0.4")), Allocation(aapl, Decimal("0.6"))],
    )
    assert portfolio.rebalance() == {}


@pytest.mark.parametrize("purchase_price", [Decimal("8"), Decimal("3")])
def test_sell_removed_stock_and_buy_target_only_stock_with_fractional_shares(purchase_price):
    old = Stock("OLD", Decimal("10"))
    new = Stock("NEW", purchase_price)
    portfolio = Portfolio(
        [Position(old, Decimal("1.25"))],
        [Allocation(new, Decimal("1"))],
    )

    with patch.object(
        Stock, "current_price", autospec=True, side_effect=lambda stock: stock.price
    ) as quote:
        trades = portfolio.rebalance()

    assert trades == {"OLD": Decimal("-1.25"), "NEW": Decimal("12.5") / purchase_price}
    assert quote.call_count == 2
    # Repeating divisions can leave a tiny residual at Decimal's working precision.
    assert abs(trades["NEW"] * purchase_price - Decimal("12.5")) <= Decimal("1e-20")
    net_trade_value = sum(
        (trades[stock.symbol] * stock.price for stock in (old, new)), Decimal("0")
    )
    assert abs(net_trade_value) <= Decimal("1e-20")


@pytest.mark.parametrize("has_position", [False, True])
def test_zero_capital_needs_no_prices(has_position):
    stock = Stock("META", Decimal("100"))
    positions = [Position(stock, Decimal("0"))] if has_position else []
    portfolio = Portfolio(positions, [Allocation(stock, Decimal("1"))])
    with patch.object(Stock, "current_price", side_effect=AssertionError("Unneeded price fetch")):
        assert portfolio.rebalance() == {}


@pytest.mark.parametrize(
    "quantity", [Decimal("1"), Decimal("1.00000000000000000000000000001")]
)
def test_zero_target_liquidates_and_unused_zero_position_needs_no_price(quantity):
    old = Stock("OLD", Decimal("10"))
    new = Stock("NEW", Decimal("5"))
    unused = Stock("UNUSED", Decimal("0"))
    portfolio = Portfolio(
        [Position(old, quantity), Position(unused, Decimal("0"))],
        [Allocation(old, Decimal("0")), Allocation(new, Decimal("1"))],
    )
    assert portfolio.rebalance() == {
        "OLD": quantity.copy_negate(), "NEW": quantity * Decimal("2")
    }


@pytest.mark.parametrize("weights", [[], [Decimal("0.9")], [Decimal("1.1")]])
def test_rejects_allocations_that_do_not_sum_to_one(weights):
    allocations = [
        Allocation(Stock(str(index), Decimal("10")), weight)
        for index, weight in enumerate(weights)
    ]
    with pytest.raises(ValueError, match="sum to 1"):
        Portfolio([], allocations).rebalance()


@pytest.mark.parametrize("value", [Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), 0.5])
@pytest.mark.parametrize("field", ["quantity", "weight"])
def test_rejects_invalid_quantities_and_weights(field, value):
    stock = Stock("META", Decimal("100"))
    quantity = value if field == "quantity" else Decimal("1")
    weight = value if field == "weight" else Decimal("1")
    portfolio = Portfolio([Position(stock, quantity)], [Allocation(stock, weight)])
    with pytest.raises(ValueError, match="finite, nonnegative Decimals"):
        portfolio.rebalance()


@pytest.mark.parametrize("field", ["positions", "allocations"])
def test_rejects_duplicate_symbols(field):
    stock = Stock("META", Decimal("100"))
    positions = [Position(stock, Decimal("1"))]
    allocations = [Allocation(stock, Decimal("1"))]
    if field == "positions":
        positions *= 2
    else:
        allocations *= 2
    with pytest.raises(ValueError, match=f"Duplicate stock symbol in {field}"):
        Portfolio(positions, allocations).rebalance()


@pytest.mark.parametrize(
    "price", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), None]
)
@pytest.mark.parametrize("target_only", [False, True])
def test_rejects_invalid_required_prices(price, target_only):
    invalid = Stock("INVALID", price)
    held = Stock("HELD", Decimal("10")) if target_only else invalid
    portfolio = Portfolio(
        [Position(held, Decimal("1"))],
        [Allocation(invalid, Decimal("1"))],
    )
    with pytest.raises(ValueError, match="Price for INVALID"):
        portfolio.rebalance()
