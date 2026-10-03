from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_location_or_404
from app.database import get_db
from app.schemas import RunRefillBody
from app.services.refill_service import (
    create_refill_order,
    get_latest_active,
    list_orders,
    order_dto,
    void_order,
)
router = APIRouter(prefix="/refills", tags=["refills"])


@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_refill(location_id: int, body: RunRefillBody | None = None, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    order = create_refill_order(
        db, location_id=location_id, requested_lines=body.lines if body else []
    )
    return order_dto(order)


@router.get("")
def refill_list(location_id: int, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    return [order_dto(o) for o in list_orders(db, location_id)]


@router.get("/latest")
def latest(location_id: int, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    return order_dto(get_latest_active(db, location_id))


@router.get("/full")
def full_lanes(location_id: int, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    order = get_latest_active(db, location_id)
    data = order_dto(order)
    return {"location_id": location_id, "order_id": order.id,
            "lanes": [l for l in data["lines"] if l["status"] == "full"]}


@router.get("/summary")
def refill_summary(location_id: int, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    order = get_latest_active(db, location_id)
    return {
        "location_id": location_id,
        "order_id": order.id,
        "total_fill": order.total_fill,
        "need_fill_count": order.need_fill_count,
        "full_count": order.full_count,
        "overbooked_count": order.overbooked_count,
    }


@router.post("/{order_id}/void")
def void_refill(order_id: int, location_id: int, db: Session = Depends(get_db)):
    get_location_or_404(location_id, db)
    return order_dto(void_order(db, order_id=order_id, location_id=location_id))
