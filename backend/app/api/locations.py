from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane, Location, RefillOrder, Sale
from app.services.current import (
    get_current_location,
    get_current_location_id,
    set_current_location_id,
)
router = APIRouter(prefix="/locations", tags=["locations"])


def _loc_dict(r: Location) -> dict:
    return {"id": r.id, "code": r.code, "name": r.name, "address": r.address}


class LocationIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    address: str = Field(default="", max_length=256)


class CurrentIn(BaseModel):
    location_id: int


@router.get("")
def list_locations(db: Session = Depends(get_db)):
    return [_loc_dict(r) for r in db.scalars(select(Location).order_by(Location.id)).all()]


@router.post("", status_code=201)
def create_location(body: LocationIn, db: Session = Depends(get_db)):
    dup = db.scalars(select(Location).where(Location.code == body.code)).first()
    if dup is not None:
        raise HTTPException(409, f"点位编码已存在：{body.code}")
    loc = Location(code=body.code, name=body.name, address=body.address)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return _loc_dict(loc)


@router.get("/current")
def read_current(db: Session = Depends(get_db)):
    return _loc_dict(get_current_location(db))


@router.put("/current")
@router.post("/current")
def switch_current(body: CurrentIn, db: Session = Depends(get_db)):
    """切换当前点位；此后五处列表与生成只作用于该点。"""
    return _loc_dict(set_current_location_id(db, body.location_id))


@router.delete("/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db)):
    """删除点位：当前点位不可删；仍有未作废补货单时拒绝并保留数据；无单才可删。"""
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(404, "点位不存在")
    if location_id == get_current_location_id(db):
        raise HTTPException(409, "当前点位不可删除，请先切换到其他点位")
    active = db.scalar(
        select(func.count()).select_from(RefillOrder)
        .where(RefillOrder.location_id == location_id, RefillOrder.status != "void")
    ) or 0
    if active > 0:
        raise HTTPException(409, f"点位仍有 {active} 张未作废补货单，禁止删除，数据已保留")
    lane_ids = select(Lane.id).where(Lane.location_id == location_id)
    db.execute(delete(Sale).where(Sale.lane_id.in_(lane_ids)))
    db.execute(delete(Lane).where(Lane.location_id == location_id))
    db.execute(delete(RefillOrder).where(RefillOrder.location_id == location_id))
    db.delete(loc)
    db.commit()
    return {"deleted": location_id}
