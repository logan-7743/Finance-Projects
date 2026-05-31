"""Abstract broker interface for order execution.

Concrete implementations:
- alpaca_broker.py  — Alpaca paper and live trading (TODO: Phase 2)
- paper_broker.py   — In-memory paper broker for backtesting (TODO: Phase 1)

All execution goes through this interface so strategies never depend on a
specific broker, and switching between paper/live is a config change only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: float
    limit_price: float | None = None  # None = market order


@dataclass
class Fill:
    order: Order
    filled_price: float
    filled_quantity: float
    timestamp: str
    fees: float


class BaseBroker(ABC):
    """Abstract interface for any broker / execution venue."""

    @abstractmethod
    def submit_order(self, order: Order) -> str:
        """Submit an order. Returns an order ID."""
        ...

    @abstractmethod
    def get_fill(self, order_id: str) -> Fill | None:
        """Return the fill for a completed order, or None if pending."""
        ...

    @abstractmethod
    def get_positions(self) -> dict[str, float]:
        """Return current positions as {symbol: quantity}."""
        ...

    @abstractmethod
    def get_account_value(self) -> float:
        """Return total account value (cash + positions at market value)."""
        ...
