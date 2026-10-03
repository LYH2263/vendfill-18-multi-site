from app.models.models import RefillOrder, RefillOrderLine, Sale
from tests.conftest import count_rows, make_lane, make_location, make_sale


def test_create_lane(client, db):
    loc = make_location(db)
    r = client.post("/lanes", json={
        "location_id": loc.id, "slot_no": "B1", "sku_name": "薯片",
        "capacity": 12, "stock": 3, "in_transit": 2})
    assert r.status_code == 201
    body = r.json()
    assert body["gap"] == 7
    assert body["location_id"] == loc.id


def test_duplicate_slot_conflict(client, db):
    loc = make_location(db)
    make_lane(db, loc.id, slot_no="A1")
    r = client.post("/lanes", json={
        "location_id": loc.id, "slot_no": "A1", "sku_name": "x", "capacity": 1})
    assert r.status_code == 409
    assert count_rows(db, RefillOrder) == 0  # 无关表保持干净


def test_create_lane_unknown_location_404(client):
    r = client.post("/lanes", json={
        "location_id": 999, "slot_no": "A1", "sku_name": "x", "capacity": 1})
    assert r.status_code == 404


def test_invalid_body_422(client, db):
    loc = make_location(db)
    r = client.post("/lanes", json={
        "location_id": loc.id, "slot_no": "A1", "sku_name": "x",
        "capacity": 0, "stock": -1})
    assert r.status_code == 422


def test_list_requires_location_id(client):
    assert client.get("/lanes").status_code == 422


def test_list_unknown_location_404(client):
    assert client.get("/lanes?location_id=999").status_code == 404


def test_list_scoped_per_location(client, db):
    a = make_location(db, code="VM-01", name="A")
    b = make_location(db, code="VM-02", name="B")
    make_lane(db, a.id, slot_no="A1")
    make_lane(db, b.id, slot_no="A1")
    make_lane(db, b.id, slot_no="A2")

    ra = client.get(f"/lanes?location_id={a.id}").json()
    rb = client.get(f"/lanes?location_id={b.id}").json()
    assert len(ra) == 1
    assert len(rb) == 2
    assert all(x["location_id"] == a.id for x in ra)
    assert all(x["location_id"] == b.id for x in rb)


def test_delete_lane_blocked_by_active_order(client, db):
    loc = make_location(db)
    lane = make_lane(db, loc.id)
    client.post(f"/refills/run?location_id={loc.id}")

    r = client.delete(f"/lanes/{lane.id}")
    assert r.status_code == 409
    assert db.get(type(lane), lane.id) is not None


def test_delete_lane_after_void_keeps_snapshot(client, db):
    loc = make_location(db)
    lane = make_lane(db, loc.id)
    make_sale(db, loc.id, lane.id, qty=3)
    run = client.post(f"/refills/run?location_id={loc.id}").json()
    client.post(f"/refills/{run['id']}/void?location_id={loc.id}")

    assert client.delete(f"/lanes/{lane.id}").status_code == 204
    # 货道销量随货道删除
    assert count_rows(db, Sale, lane_id=lane.id) == 0
    # 作废单仍在，行快照仍在，lane_id 被置空
    assert count_rows(db, RefillOrder, location_id=loc.id) == 1
    line = db.query(RefillOrderLine).filter_by(order_id=run["id"]).first()
    assert line is not None
    assert line.lane_id is None
    assert line.slot_no == "A1"
    assert line.sku_name == "水"


def test_delete_unknown_lane_404(client):
    assert client.delete("/lanes/999").status_code == 404
