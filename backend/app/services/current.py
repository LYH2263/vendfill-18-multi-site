"""当前点位（current location）状态与跨点位守卫。

多点位规则：货道、销量、补货单、满仓、汇总五处只服务当前点位；
任何显式指向非当前点位的读写一律 409 拒绝（跨点写与本点写互斥）。
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AppState, Location

CURRENT_LOCATION_KEY = "current_location_id"


def _stored_current_id(db: Session) -> int | None:
    row = db.scalars(
        select(AppState).where(AppState.key == CURRENT_LOCATION_KEY)
        .execution_options(populate_existing=True)
    ).first()
    if row is None or not row.value:
        return None
    try:
        return int(row.value)
    except ValueError:
        return None


def get_current_location_id(db: Session) -> int:
    """当前点位 id；未设置时回退到最小 id 点位并持久化。无点位时 404。"""
    loc_id = _stored_current_id(db)
    if loc_id is not None and db.get(Location, loc_id) is not None:
        return loc_id
    first = db.scalars(select(Location).order_by(Location.id)).first()
    if first is None:
        raise HTTPException(404, "无可用点位")
    _write_current(db, first.id)
    db.commit()
    return first.id


def get_current_location(db: Session) -> Location:
    loc = db.get(Location, get_current_location_id(db))
    if loc is None:  # pragma: no cover - get_current_location_id 已保证存在
        raise HTTPException(404, "无可用点位")
    return loc


def set_current_location_id(db: Session, location_id: int) -> Location:
    """切换当前点位。点位不存在时 404。"""
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(404, "点位不存在")
    _write_current(db, loc.id)
    db.commit()
    return loc


def _write_current(db: Session, location_id: int) -> None:
    row = db.get(AppState, CURRENT_LOCATION_KEY)
    if row is None:
        db.add(AppState(key=CURRENT_LOCATION_KEY, value=str(location_id)))
    else:
        row.value = str(location_id)


def peek_current_location_id(db: Session) -> int | None:
    """只读当前点位 id（不创建、不提交），用于提交前复核。"""
    return _stored_current_id(db)


def resolve_location_id(db: Session, location_id: int | None) -> int:
    """把可选的 location_id 解析为本次请求作用的点位。

    缺省 = 当前点位；显式给出但非当前点位 = 串点，409 拒绝。
    """
    current = get_current_location_id(db)
    if location_id is None:
        return current
    if location_id != current:
        raise HTTPException(409, f"跨点位操作被拒绝：当前点位为 #{current}，目标点位 #{location_id}")
    return location_id


def require_current_location(db: Session, location_id: int) -> None:
    """校验给定点位就是当前点位，否则 409（用于按记录归属校验写入）。"""
    current = get_current_location_id(db)
    if location_id != current:
        raise HTTPException(409, f"跨点位操作被拒绝：当前点位为 #{current}，目标点位 #{location_id}")
