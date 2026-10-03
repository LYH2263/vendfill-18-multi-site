from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# 补货单生命周期状态：行内状态（need_fill/full/overbooked）在 fill_engine 中。
ORDER_ACTIVE = "active"
ORDER_VOID = "void"


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    address: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lane(Base):
    __tablename__ = "lanes"
    __table_args__ = (
        UniqueConstraint("location_id", "slot_no", name="uq_lane_location_slot"),
        Index("ix_lanes_location_id", "location_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    slot_no: Mapped[str] = mapped_column(String(16))
    sku_name: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    in_transit: Mapped[int] = mapped_column(Integer, default=0)


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (Index("ix_sales_location_id", "location_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    lane_id: Mapped[int] = mapped_column(ForeignKey("lanes.id"))
    qty: Mapped[int] = mapped_column(Integer)
    sold_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RefillOrder(Base):
    __tablename__ = "refill_orders"
    __table_args__ = (
        Index("ix_refill_orders_loc_status_id", "location_id", "status", "id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(16), default=ORDER_ACTIVE)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_fill: Mapped[int] = mapped_column(Integer, default=0)
    need_fill_count: Mapped[int] = mapped_column(Integer, default=0)
    full_count: Mapped[int] = mapped_column(Integer, default=0)
    overbooked_count: Mapped[int] = mapped_column(Integer, default=0)

    lines: Mapped[list["RefillOrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class RefillOrderLine(Base):
    """生成时的货道快照：货道日后被改/删，历史单仍可读。"""
    __tablename__ = "refill_order_lines"
    __table_args__ = (Index("ix_refill_order_lines_order_id", "order_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("refill_orders.id"))
    lane_id: Mapped[int | None] = mapped_column(ForeignKey("lanes.id"), nullable=True)
    slot_no: Mapped[str] = mapped_column(String(16))
    sku_name: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    in_transit: Mapped[int] = mapped_column(Integer)
    gap: Mapped[int] = mapped_column(Integer)
    fill_qty: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))  # need_fill | full | overbooked

    order: Mapped["RefillOrder"] = relationship(back_populates="lines")
