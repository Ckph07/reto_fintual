# Portfolio rebalancer

A small Python solution to a portfolio management technical challenge. It
calculates which shares to buy or sell to reach desired allocations, without
changing holdings or executing trades.

## Run the tests

Requires Python 3.10 or newer. There are no runtime dependencies; pytest is the
only test dependency.

```sh
python3 -m pip install -e '.[test]'
python3 -m pytest
```

If pytest is already available, run `python3 -m pytest` directly from the project
directory without installing the package.

## Example

```python
from decimal import Decimal

from portfolio_rebalancer import Allocation, Portfolio, Position, Stock

meta = Stock("META", Decimal("100"))
aapl = Stock("AAPL", Decimal("200"))

portfolio = Portfolio(
    positions=[Position(meta, Decimal("10")), Position(aapl, Decimal("5"))],
    allocations=[Allocation(meta, Decimal("0.4")), Allocation(aapl, Decimal("0.6"))],
)

print(portfolio.rebalance())
# {'META': Decimal('-2'), 'AAPL': Decimal('1')}
```

The portfolio is worth $2,000. META's target value is $800 and AAPL's is $1,200,
so the proposal sells two META shares and buys one AAPL share. Positive values
mean buy, negative values mean sell; zero trades are omitted.

## Model and algorithm

- `Stock` identifies an asset and exposes `current_price()`. This exercise uses
  a stored price; no external pricing integration is needed.
- `Position` associates a stock with the quantity currently owned.
- `Allocation` associates a stock with its desired fraction of portfolio value.
  It can reference a stock that is not currently owned.
- `Portfolio` keeps positions separate from allocations and calculates trades.

For each stock, using current quantity `q`, price `p`, and target weight `w`:

```text
total_value = sum(quantity * price for each holding)
target_value = total_value * weight
share_delta = (target_value - quantity * price) / price
```

Allocations apply to monetary value, so valuation comes before share conversion.
An absent position has zero quantity. An absent target has zero weight, so its
holding is sold in full. Full liquidation returns exactly the negative quantity.
Each relevant stock's price is fetched once per symbol and reused throughout
the calculation. Time and space complexity are O(n + m), where n is the number
of positions and m the number of allocations.

## Assumptions and trade-offs

- All assets use one currency. There is no cash balance, new capital, shorting,
  leverage, fee, tax, spread, or execution delay.
- Fractional shares are allowed. The output is a calculation proposal, not a
  broker order; whole shares would require rounding and a leftover-cash policy.
- Prices, quantities, and weights must be `Decimal` values. Construct them from
  strings to avoid importing binary floating-point representation errors.
- Ordinary `Decimal` arithmetic is used, without changing the caller's context.
  Repeating divisions are approximate at the working precision. Intermediate
  amounts are not rounded to cents and no broker-specific share increment is
  imposed; a tiny residual can remain when applying a proposal.
- Weights must be finite, nonnegative, and sum to exactly 1. Incorrect totals
  raise `ValueError` instead of being silently normalized. Empty targets are
  invalid; zero individual weights are allowed.
- Quantities must be finite and nonnegative. Required prices must be finite and
  positive. Invalid inputs raise `ValueError`; a pricing-method exception
  propagates to the caller rather than producing a partial proposal.
- Symbols identify assets and must be unique within positions and within
  allocations. Use consistent stock data for a symbol shared by both collections
  (as in the example); symbol normalization and identity resolution are outside
  this exercise.
- An empty portfolio or one with only zero quantities returns no trades after
  validating inputs. With no capital to redistribute, no prices are needed.
  An asset with both zero quantity and zero target weight also needs no price.
- Positions, allocations, and stocks are immutable value objects. `rebalance()`
  leaves the portfolio's collections unchanged and validates them on each call.
- Reading prices once makes reuse consistent within a calculation, but does not
  guarantee that different assets' prices share a market timestamp.

Tests cover exact and fractional trades, a balanced portfolio, target-only and
removed assets, zero capital, concise validation cases, nonmutation, and price
fetch counts. The fractional tests also check value conservation within a small
decimal tolerance.
