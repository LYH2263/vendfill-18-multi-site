from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Lane, Location, RefillOrder
from app.schemas import LocationCreate
from app.services.location_service import delete_location_cascade
router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("")
def list_locations(db: Session = Depends(get_db)):
    locations = db.scalars(select(Location).order_by(Location.id)).all()
    lane_counts = dict(db.execute(
        select(Lane.location_id, func.count()).group_by(Lane.location_id)
    ).all())
    active_counts = dict(db.execute(
        select(RefillOrder.location_id, func.count())
        .where(RefillOrder.status == "active")
        .group_by(RefillOrder.location_id)
    ).all())
    return [
        {
            "id": r.id, "code": r.code, "name": r.name, "address": r.address,
            "lane_count": lane_counts.get(r.id, 0),
            "active_order_count": active_counts.get(r.id, 0),
        }
        for r in locations
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_location(body: LocationCreate, db: Session = Depends(get_db)):
    loc = Location(code=body.code, name=body.name, address=body.address)
    db.add(loc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="编码已存在")
    db.refresh(loc)
    return {"id": loc.id, "code": loc.code, "name": loc.name, "address": loc.address,
            "lane_count": 0, "active_order_count": 0}


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: int, db: Session = Depends(get_db)):
    delete_location_cascade(db, location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
