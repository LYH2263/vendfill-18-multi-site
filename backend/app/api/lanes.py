from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane, Sale
from app.services.current import require_current_location, resolve_location_id
from app.services.fill_engine import compute_gap
router = APIRouter(prefix="/lanes", tags=["lanes"])


def _lane_dict(r: Lane) -> dict:
    return {"id": r.id, "location_id": r.location_id, "slot_no": r.slot_no, "sku_name": r.sku_name,
            "capacity": r.capacity, "stock": r.stock, "in_transit": r.in_transit,
            "gap": compute_gap(r.capacity, r.stock, r.in_transit),
            "fill_pct": round(r.stock / r.capacity * 100, 1) if r.capacity else 0}


def _get_own_lane(db: Session, lane_id: int) -> Lane:
    lane = db.get(Lane, lane_id)
    if lane is None:
        raise HTTPException(404, "货道不存在")
    require_current_location(db, lane.location_id)  # 跨点写互斥
    return lane


class LaneIn(BaseModel):
    slot_no: str = Field(min_length=1, max_length=16)
    sku_name: str = Field(min_length=1, max_length=64)
    capacity: int = Field(ge=1)
    stock: int = Field(default=0, ge=0)
    in_transit: int = Field(default=0, ge=0)
    location_id: int | None = None  # 缺省 = 当前点位；显式跨点 = 409


class LanePatch(BaseModel):
    slot_no: str | None = Field(default=None, min_length=1, max_length=16)
    sku_name: str | None = Field(default=None, min_length=1, max_length=64)
    capacity: int | None = Field(default=None, ge=1)
    stock: int | None = Field(default=None, ge=0)
    in_transit: int | None = Field(default=None, ge=0)


@router.get("")
def list_lanes(location_id: int | None = None, db: Session = Depends(get_db)):
    loc_id = resolve_location_id(db, location_id)
    q = select(Lane).where(Lane.location_id == loc_id).order_by(Lane.slot_no)
    return [_lane_dict(r) for r in db.scalars(q).all()]


@router.post("", status_code=201)
def create_lane(body: LaneIn, db: Session = Depends(get_db)):
    loc_id = resolve_location_id(db, body.location_id)
    dup = db.scalars(select(Lane).where(Lane.location_id == loc_id, Lane.slot_no == body.slot_no)).first()
    if dup is not None:
        raise HTTPException(409, f"货道号已存在：{body.slot_no}")
    lane = Lane(location_id=loc_id, slot_no=body.slot_no, sku_name=body.sku_name,
                capacity=body.capacity, stock=body.stock, in_transit=body.in_transit)
    db.add(lane)
    db.commit()
    db.refresh(lane)
    return _lane_dict(lane)


@router.patch("/{lane_id}")
def update_lane(lane_id: int, body: LanePatch, db: Session = Depends(get_db)):
    lane = _get_own_lane(db, lane_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lane, field, value)
    db.commit()
    db.refresh(lane)
    return _lane_dict(lane)


@router.delete("/{lane_id}")
def delete_lane(lane_id: int, db: Session = Depends(get_db)):
    lane = _get_own_lane(db, lane_id)
    db.execute(delete(Sale).where(Sale.lane_id == lane.id))
    db.delete(lane)
    db.commit()
    return {"deleted": lane_id}
