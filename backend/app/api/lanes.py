from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_location_or_404
from app.database import get_db
from app.models.models import ORDER_ACTIVE, Lane, RefillOrder, RefillOrderLine, Sale
from app.schemas import LaneCreate
from app.services.fill_engine import compute_gap
router = APIRouter(prefix="/lanes", tags=["lanes"])


def _lane_dto(r: Lane) -> dict:
    gap = compute_gap(r.capacity, r.stock, r.in_transit)
    return {"id": r.id, "location_id": r.location_id, "slot_no": r.slot_no,
            "sku_name": r.sku_name, "capacity": r.capacity, "stock": r.stock,
            "in_transit": r.in_transit, "gap": gap,
            "fill_pct": round(r.stock / r.capacity * 100, 1) if r.capacity else 0}


@router.get("")
def list_lanes(location_id: int, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    rows = db.scalars(
        select(Lane).where(Lane.location_id == location_id).order_by(Lane.slot_no)
    ).all()
    return [_lane_dto(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_lane(body: LaneCreate, db: Session = Depends(get_db)):
    get_location_or_404(body.location_id, db)
    lane = Lane(location_id=body.location_id, slot_no=body.slot_no, sku_name=body.sku_name,
                capacity=body.capacity, stock=body.stock, in_transit=body.in_transit)
    db.add(lane)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该点位已存在同编号货道")
    db.refresh(lane)
    return _lane_dto(lane)


@router.delete("/{lane_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lane(lane_id: int, db: Session = Depends(get_db)):
    lane = db.get(Lane, lane_id)
    if lane is None:
        raise HTTPException(status_code=404, detail="货道不存在")

    referenced = db.scalar(
        select(exists().where(
            RefillOrderLine.lane_id == lane_id,
            RefillOrder.id == RefillOrderLine.order_id,
            RefillOrder.status == ORDER_ACTIVE,
        ))
    )
    if referenced:
        raise HTTPException(status_code=409, detail="货道存在未作废补货单，请先作废")

    try:
        # 作废单保留快照文本，仅摘掉货道引用；该货道销量随货道删除。
        db.execute(delete(Sale).where(Sale.lane_id == lane_id))
        db.query(RefillOrderLine).filter(RefillOrderLine.lane_id == lane_id).update(
            {RefillOrderLine.lane_id: None}, synchronize_session=False
        )
        db.delete(lane)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除货道失败，已回滚")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
