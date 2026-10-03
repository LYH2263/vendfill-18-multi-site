"""点位删除：有未作废补货单时拒绝；放行时在单事务内显式级联删除全部从属数据。"""
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.models import (
    ORDER_ACTIVE,
    Lane,
    Location,
    RefillOrder,
    RefillOrderLine,
    Sale,
)


def delete_location_cascade(db: Session, location_id: int) -> None:
    try:
        location = db.get(Location, location_id)
        if location is None:
            raise HTTPException(status_code=404, detail="点位不存在")

        active_count = db.scalar(
            select(func.count())
            .select_from(RefillOrder)
            .where(RefillOrder.location_id == location_id,
                   RefillOrder.status == ORDER_ACTIVE)
        ) or 0
        if active_count > 0:
            raise HTTPException(status_code=409, detail="存在未作废补货单，不能删除点位")

        order_ids = db.scalars(
            select(RefillOrder.id).where(RefillOrder.location_id == location_id)
        ).all()
        if order_ids:
            db.execute(delete(RefillOrderLine).where(RefillOrderLine.order_id.in_(order_ids)))
            db.execute(delete(RefillOrder).where(RefillOrder.id.in_(order_ids)))
        db.execute(delete(Sale).where(Sale.location_id == location_id))
        db.execute(delete(Lane).where(Lane.location_id == location_id))
        db.delete(location)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除点位失败，已回滚")
