"""补货单生成/查询/作废。生成是「头 + 多行」单事务：校验先于插入，任何失败整体回滚。"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.models import (
    ORDER_ACTIVE,
    ORDER_VOID,
    Lane,
    RefillOrder,
    RefillOrderLine,
)
from app.services.fill_engine import build_fill_lines, summarize


def _line_dto(line: RefillOrderLine) -> dict:
    return {
        "lane_id": line.lane_id,
        "slot_no": line.slot_no,
        "sku_name": line.sku_name,
        "capacity": line.capacity,
        "stock": line.stock,
        "in_transit": line.in_transit,
        "gap": line.gap,
        "fill_qty": line.fill_qty,
        "status": line.status,
    }


def order_dto(order: RefillOrder) -> dict:
    return {
        "id": order.id,
        "location_id": order.location_id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "status": order.status,
        "voided_at": order.voided_at.isoformat() if order.voided_at else None,
        "total_fill": order.total_fill,
        "need_fill_count": order.need_fill_count,
        "full_count": order.full_count,
        "overbooked_count": order.overbooked_count,
        "lines": [_line_dto(l) for l in order.lines],
    }


def create_refill_order(db: Session, location_id: int, requested_lines: list | None = None) -> RefillOrder:
    """requested_lines: RequestedLine 列表（lane_id/requested_qty）；为空按缺口全补。

    跨点 lane_id / 重复 lane_id 在任何插入前拒绝；头与行在同一事务内提交。
    """
    requested_lines = requested_lines or []
    lanes = db.scalars(
        select(Lane).where(Lane.location_id == location_id).order_by(Lane.slot_no)
    ).all()
    if not lanes:
        raise HTTPException(status_code=400, detail="点位尚无货道，无法生成补货单")

    valid_ids = {l.id for l in lanes}
    seen: set[int] = set()
    requested: dict[int, int] = {}
    for item in requested_lines:
        lane_id = item.lane_id
        if lane_id not in valid_ids:
            # 货道可能存在，但属于另一个点位 —— 跨点写入，拒绝且不落任何行。
            raise HTTPException(status_code=400, detail="货道不属于该点位（跨点位写入被拒绝）")
        if lane_id in seen:
            raise HTTPException(status_code=400, detail="同一货道的补货期望重复提交")
        seen.add(lane_id)
        requested[lane_id] = item.requested_qty
    payload = [
        {"id": l.id, "slot_no": l.slot_no, "sku_name": l.sku_name,
         "capacity": l.capacity, "stock": l.stock, "in_transit": l.in_transit}
        for l in lanes
    ]
    summary = summarize(build_fill_lines(payload, requested or None))

    order = RefillOrder(
        location_id=location_id,
        created_at=datetime.utcnow(),
        status=ORDER_ACTIVE,
        total_fill=summary["total_fill"],
        need_fill_count=summary["need_fill_count"],
        full_count=summary["full_count"],
        overbooked_count=summary["overbooked_count"],
    )
    try:
        db.add(order)
        db.flush()  # 取得 order.id；若头插入失败，下面的行无从挂接
        for row in summary["lines"]:
            db.add(RefillOrderLine(
                order_id=order.id,
                lane_id=row["lane_id"],
                slot_no=row["slot_no"],
                sku_name=row["sku_name"],
                capacity=row["capacity"],
                stock=row["stock"],
                in_transit=row["in_transit"],
                gap=row["gap"],
                fill_qty=row["fill_qty"],
                status=row["status"],
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="补货单生成失败，已回滚")

    db.refresh(order)
    return order


def list_orders(db: Session, location_id: int) -> list[RefillOrder]:
    return db.scalars(
        select(RefillOrder)
        .where(RefillOrder.location_id == location_id)
        .options(selectinload(RefillOrder.lines))
        .order_by(RefillOrder.id.desc())
    ).all()


def get_latest_active(db: Session, location_id: int) -> RefillOrder:
    order = db.scalars(
        select(RefillOrder)
        .where(RefillOrder.location_id == location_id, RefillOrder.status == ORDER_ACTIVE)
        .options(selectinload(RefillOrder.lines))
        .order_by(RefillOrder.id.desc())
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="暂无补货单")
    return order


def void_order(db: Session, order_id: int, location_id: int) -> RefillOrder:
    order = db.scalars(
        select(RefillOrder)
        .where(RefillOrder.id == order_id, RefillOrder.location_id == location_id)
        .options(selectinload(RefillOrder.lines))
    ).first()
    if not order:
        # 不区分「不存在」与「属于他点」，避免跨点探测单据存在性。
        raise HTTPException(status_code=404, detail="补货单不存在")
    if order.status == ORDER_VOID:
        raise HTTPException(status_code=409, detail="补货单已作废")
    order.status = ORDER_VOID
    order.voided_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order
