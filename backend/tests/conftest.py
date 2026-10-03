import os
import tempfile

# 在导入 app 之前指向独立的 sqlite 测试库，避免触碰真实 Postgres。
_TMPDIR = tempfile.mkdtemp(prefix="vendfill_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db?check_same_thread=false"
os.environ["SEED_ON_EMPTY"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.services.seed import seed_if_empty


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def vm01_id(client) -> int:
    return client.get("/api/locations/current").json()["id"]


def make_location(client, code="VM-02", name="商场 B 点位") -> dict:
    r = client.post("/api/locations", json={"code": code, "name": name, "address": "城西商场"})
    assert r.status_code == 201, r.text
    return r.json()


def switch(client, location_id: int):
    r = client.put("/api/locations/current", json={"location_id": location_id})
    assert r.status_code == 200, r.text
    return r.json()


def add_lane(client, slot="A1", sku="果汁", capacity=10, stock=4, transit=0, location_id=None):
    body = {"slot_no": slot, "sku_name": sku, "capacity": capacity,
            "stock": stock, "in_transit": transit}
    if location_id is not None:
        body["location_id"] = location_id
    return client.post("/api/lanes", json=body)


def order_count(client, location_id: int) -> int:
    """直接数库里的单，绕过作用域接口。"""
    from app.models.models import RefillOrder
    from sqlalchemy import func, select
    db = SessionLocal()
    try:
        return db.scalar(
            select(func.count()).select_from(RefillOrder)
            .where(RefillOrder.location_id == location_id)
        ) or 0
    finally:
        db.close()
