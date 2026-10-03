from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Lane, Sale
from app.services.current import resolve_location_id
router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("")
def list_sales(location_id: int | None = None, db: Session = Depends(get_db)):
    loc_id = resolve_location_id(db, location_id)
    lanes = {l.id: l for l in db.scalars(select(Lane).where(Lane.location_id == loc_id)).all()}
    rows = db.scalars(
        select(Sale).join(Lane, Sale.lane_id == Lane.id)
        .where(Lane.location_id == loc_id)
        .order_by(Sale.sold_at.desc(), Sale.id.desc())
    ).all()
    return [{"id": r.id, "lane_id": r.lane_id, "location_id": loc_id,
             "slot_no": lanes[r.lane_id].slot_no if r.lane_id in lanes else "",
             "sku_name": lanes[r.lane_id].sku_name if r.lane_id in lanes else "",
             "qty": r.qty, "sold_at": r.sold_at.isoformat()} for r in rows]
