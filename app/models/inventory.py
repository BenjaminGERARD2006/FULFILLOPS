from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        CheckConstraint(
            "available >= 0",
            name="ck_inventory_available_nonnegative",
        ),
    )

    sku: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("products.sku", ondelete="RESTRICT"),
        primary_key=True,
    )

    available: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    product: Mapped["Product"] = relationship(
        back_populates="inventory",
    )