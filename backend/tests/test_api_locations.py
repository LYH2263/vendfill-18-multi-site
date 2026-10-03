from app.models.models import Lane, Location, RefillOrder, RefillOrderLine, Sale
from tests.conftest import count_rows, make_lane, make_location


def test_create_and_duplicate_conflict(client, db):
    r = client.post("/locations", json={"code": "VM-02", "name": "二号点", "address": "x"})
    assert r.status_code == 201
    assert r.json()["lane_count"] == 0

    r = client.post("/locations", json={"code": "VM-02", "name": "重复"})
    assert r.status_code == 409
    assert count_rows(db, Location) == 1


def test_list_has_counts(client, db):
    loc = make_location(db)
    make_lane(db, loc.id)
    # 直接造一笔 active 单（不走引擎，只为计数）
    db.add(RefillOrder(location_id=loc.id, status="active"))
    db.commit()

    r = client.get("/locations")
    assert r.status_code == 200
    row = [x for x in r.json() if x["id"] == loc.id][0]
    assert row["lane_count"] == 1
    assert row["active_order_count"] == 1


def test_delete_unknown_404(client):
    assert client.delete("/locations/999").status_code == 404


def test_delete_blocked_by_active_order_and_keeps_all_rows(client, db):
    loc = make_location(db, code="VM-02")
    lane = make_lane(db, loc.id)
    from tests.conftest import make_sale
    make_sale(db, loc.id, lane.id)
    run = client.post(f"/refills/run?location_id={loc.id}")
    assert run.status_code == 201

    before = {
        "locations": count_rows(db, Location),
        "lanes": count_rows(db, Lane),
        "sales": count_rows(db, Sale),
        "orders": count_rows(db, RefillOrder),
        "lines": count_rows(db, RefillOrderLine),
    }
    r = client.delete(f"/locations/{loc.id}")
    assert r.status_code == 409
    after = {
        "locations": count_rows(db, Location),
        "lanes": count_rows(db, Lane),
        "sales": count_rows(db, Sale),
        "orders": count_rows(db, RefillOrder),
        "lines": count_rows(db, RefillOrderLine),
    }
    assert before == after
    # 数据仍可读
    assert db.get(Lane, lane.id) is not None


def test_delete_after_void_removes_everything_other_location_intact(client, db):
    a = make_location(db, code="VM-01", name="A")
    b = make_location(db, code="VM-02", name="B")
    la = make_lane(db, a.id, slot_no="A1")
    lb = make_lane(db, b.id, slot_no="A1")
    from tests.conftest import make_sale
    make_sale(db, a.id, la.id)
    make_sale(db, b.id, lb.id)
    run_a = client.post(f"/refills/run?location_id={a.id}").json()
    run_b = client.post(f"/refills/run?location_id={b.id}").json()
    client.post(f"/refills/{run_b['id']}/void?location_id={b.id}")

    assert client.delete(f"/locations/{b.id}").status_code == 204

    # B 的所有从属行消失
    assert count_rows(db, Lane, location_id=b.id) == 0
    assert count_rows(db, Sale, location_id=b.id) == 0
    assert count_rows(db, RefillOrder, location_id=b.id) == 0
    # 只剩 A 订单的行
    assert count_rows(db, RefillOrderLine, order_id=run_a["id"]) == 1
    assert count_rows(db, RefillOrderLine) == 1
    assert db.get(Location, b.id) is None
    # A 原封不动
    assert db.get(Location, a.id) is not None
    assert count_rows(db, Lane, location_id=a.id) == 1
    assert count_rows(db, Sale, location_id=a.id) == 1
    assert count_rows(db, RefillOrder, location_id=a.id) == 1
