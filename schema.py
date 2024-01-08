"""DB Models for the app."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HistoryRecord:
    id: int  # primary key (auto-incremented)
    sku: str
    retailer: str
    price: float
    timestamp: datetime
    fromdate: datetime | None = None
    todate: datetime | None = None
    url: str | None = None


@dataclass(frozen=True)
class LatestPriceRecord:
    sku: str  # composite primary key + composite index
    retailer: str  # composite primary key
    price: float  # composite index
    fromdate: datetime | None = None
    todate: datetime | None = None
    url: str | None = None


@dataclass(frozen=True)
class LowestPriceRecord:
    sku: str  # primary key (index)
    retailer: str
    price: float
    fromdate: datetime | None = None
    todate: datetime | None = None
    url: str | None = None


@dataclass(frozen=True)
class APIRecord:
    sku: str
    retailer: str
    price: float
    fromdate: datetime | None = None
    todate: datetime | None = None
    url: str | None = None
