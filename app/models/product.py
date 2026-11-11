from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            "unit_price_cents >= 0",
            name="ck_products_unit_price_nonnegative",
        ),
    )

    sku: Mapped[str] = mapped_column(String(32), primary_key=True)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    inventory: Mapped["Inventory"] = relationship(
        back_populates="product",
        uselist=False,
    )