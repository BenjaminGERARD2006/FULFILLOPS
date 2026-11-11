from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    __table_args__ = (
        CheckConstraint(
            "length(payload_hash) = 64",
            name="ck_idempotency_hash_length",
        ),
        CheckConstraint(
            "length(idempotency_key) BETWEEN 8 AND 128",
            name="ck_idempotency_key_length",
        ),
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )

    payload_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    order_id: Mapped[Uuid] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped["Order"] = relationship(
        back_populates="idempotency_record",
    )