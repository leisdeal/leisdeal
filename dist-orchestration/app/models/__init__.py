"""Import all models so Base.metadata is fully populated."""

from app.db import Base
from app.models.catalog import ComplianceRecord, Product, SKU, WholesalePrice
from app.models.distributor import CategorySeat, Distributor, WalletTransaction
from app.models.drop import DailySkuDrop, DropAssignment
from app.models.fulfillment import Fulfillment, Return
from app.models.sales import SalesOrder
from app.models.show import Show

__all__ = [
    "Base",
    "CategorySeat",
    "ComplianceRecord",
    "DailySkuDrop",
    "Distributor",
    "DropAssignment",
    "Fulfillment",
    "Product",
    "Return",
    "SKU",
    "SalesOrder",
    "Show",
    "WalletTransaction",
    "WholesalePrice",
]
