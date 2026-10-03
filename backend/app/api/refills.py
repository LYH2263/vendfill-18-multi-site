import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane, Location, RefillOrder
from app.services.current import (
    peek_current_location_id,
    require_current_location,
    resolve_location_id,
)
from app.services.fill_engine import build_fill_lines, summarize
router = APIRouter(prefix="/refills", tags=["refills"])


def _lanes_payload(db: Session, location_id: int) -> list[dict]:
    lanes = db.scalars(select(Lane).where(Lane.location_id == location_id).order_by(Lane.slot_no)).all()
    return [{"id": l.id, "slot_no": l.slot_no, "sku_name": l.sku_name,
             "capacity": l.capacity, "stock": l.stock, "in_transit": l.in_transit} for l in lanes]


def _order_brief(o: RefillOrder) -> dict:
    data = json.loads(o.lines_json)
    return {"id": o.id, "location_id": o.location_id, "created_at": o.created_at.isoformat(),
            "status": o.status,
            "total_fill": data.get("total_fill", 0),
            "need_fill_count": data.get("need_fill_count", 0),
            "full_count": data.get("full_count", 0),
            "overbooked_count": data.get("overbooked_count", 0)}


def _order_detail(o: RefillOrder) -> dict:
    return {**_order_brief(o), "lines": json.loads(o.lines_json).get("lines", [])}


@router.post("/run")
def run_refill(location_id: int | None = None, db: Session = Depends(get_db)):
    """为当前点位生成补货单（单事务）。

    显式 location_id 非当前点位 → 409，两边行数都不增（跨点写与本点写互斥）。
    生成期间当前点位被切换 → 未提交的半套单回滚，不留跨点脏行。
    """
    target = resolve_location_id(db, location_id)
    if db.get(Location, target) is None:
        raise HTTPException(404, "点位不存在")
    summary = summarize(build_fill_lines(_lanes_payload(db, target)))
    order = RefillOrder(location_id=target, created_at=datetime.utcnow(),
                        lines_json=json.dumps(summary, ensure_ascii=False), status="active")
    db.add(order)
    db.flush()  # 半套单位于事务内，尚未提交
    if peek_current_location_id(db) != target:
        db.rollback()  # 生成过程中点位已切换：回滚，禁止跨点脏行
        raise HTTPException(409, "生成期间当前点位已切换，本次补货单已回滚")
    db.commit()
    db.refresh(order)
    return _order_detail(order)


@router.get("")
def list_refills(location_id: int | None = None, db: Session = Depends(get_db)):
    """当前点位的补货单列表（新→旧）。"""
    loc_id = resolve_location_id(db, location_id)
    orders = db.scalars(select(RefillOrder).where(RefillOrder.location_id == loc_id)
                        .order_by(RefillOrder.id.desc())).all()
    return [_order_brief(o) for o in orders]


@router.get("/latest")
def latest(location_id: int | None = None, db: Session = Depends(get_db)):
    """当前点位最新一张补货单。只读：无单时 404，绝不代写（写只走 POST /run）。"""
    loc_id = resolve_location_id(db, location_id)
    order = db.scalars(select(RefillOrder).where(RefillOrder.location_id == loc_id)
                       .order_by(RefillOrder.id.desc())).first()
    if order is None:
        raise HTTPException(404, "当前点位暂无补货单")
    return _order_detail(order)


@router.post("/{order_id}/void")
def void_refill(order_id: int, db: Session = Depends(get_db)):
    """作废补货单；只能作废当前点位的单。"""
    order = db.get(RefillOrder, order_id)
    if order is None:
        raise HTTPException(404, "补货单不存在")
    require_current_location(db, order.location_id)
    order.status = "void"
    db.commit()
    db.refresh(order)
    return _order_brief(order)


@router.get("/full")
def full_lanes(location_id: int | None = None, db: Session = Depends(get_db)):
    """当前点位满仓货道（缺口为 0），按实时库存计算。"""
    loc_id = resolve_location_id(db, location_id)
    data = summarize(build_fill_lines(_lanes_payload(db, loc_id)))
    return {"location_id": loc_id,
            "lanes": [l for l in data["lines"] if l["status"] == "full"]}


@router.get("/summary")
def refill_summary(location_id: int | None = None, db: Session = Depends(get_db)):
    """当前点位补货建议合计，按实时库存计算。"""
    loc_id = resolve_location_id(db, location_id)
    data = summarize(build_fill_lines(_lanes_payload(db, loc_id)))
    return {
        "location_id": loc_id,
        "total_fill": data["total_fill"],
        "need_fill_count": data["need_fill_count"],
        "full_count": data["full_count"],
        "overbooked_count": data["overbooked_count"],
    }
