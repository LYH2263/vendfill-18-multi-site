from app.models.models import RefillOrder, RefillOrderLine
from tests.conftest import count_rows, make_lane, make_location


def _two_points_with_lanes(db):
    a = make_location(db, code="VM-01", name="A")
    b = make_location(db, code="VM-02", name="B")
    # A: gap=15 需要补
    la = make_lane(db, a.id, slot_no="A1", capacity=20, stock=5, in_transit=0)
    # B: 两个货道，一个满仓一个待补
    lb1 = make_lane(db, b.id, slot_no="B1", capacity=10, stock=10, in_transit=0)
    lb2 = make_lane(db, b.id, slot_no="B2", capacity=12, stock=3, in_transit=2)
    return a, b, la, lb1, lb2


def test_run_creates_header_and_lines(client, db):
    loc = make_location(db)
    make_lane(db, loc.id, slot_no="A1", capacity=20, stock=5)
    make_lane(db, loc.id, slot_no="A2", capacity=10, stock=10)
    r = client.post(f"/refills/run?location_id={loc.id}")
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert len(body["lines"]) == 2
    assert count_rows(db, RefillOrder, location_id=loc.id) == 1
    assert count_rows(db, RefillOrderLine) == 2
    assert body["total_fill"] == 15
    assert body["full_count"] == 1


def test_cross_location_write_rejected_zero_delta_both_sides(client, db):
    a, b, la, lb1, lb2 = _two_points_with_lanes(db)

    def counts():
        return (
            count_rows(db, RefillOrder, location_id=a.id),
            count_rows(db, RefillOrder, location_id=b.id),
            count_rows(db, RefillOrderLine),
        )

    # 对 B 生成，却夹带 A 的货道 —— 拒绝，两侧订单/行数都不增
    r = client.post(
        f"/refills/run?location_id={b.id}",
        json={"lines": [{"lane_id": la.id, "requested_qty": 1}]},
    )
    assert r.status_code == 400
    assert counts() == (0, 0, 0)

    # 混合：一个合法 B 货道 + 一个 A 货道，仍整体拒绝、无半套行
    r = client.post(
        f"/refills/run?location_id={b.id}",
        json={"lines": [
            {"lane_id": lb2.id, "requested_qty": 1},
            {"lane_id": la.id, "requested_qty": 1},
        ]},
    )
    assert r.status_code == 400
    assert counts() == (0, 0, 0)


def test_run_empty_location_400(client, db):
    loc = make_location(db)
    r = client.post(f"/refills/run?location_id={loc.id}")
    assert r.status_code == 400
    assert count_rows(db, RefillOrder) == 0


def test_get_endpoints_never_write_and_404_when_empty(client, db):
    loc = make_location(db)
    for path in ("latest", "full", "summary"):
        r = client.get(f"/refills/{path}?location_id={loc.id}")
        assert r.status_code == 404
    assert count_rows(db, RefillOrder) == 0


def test_views_isolated_after_each_location_generates(client, db):
    a, b, la, lb1, lb2 = _two_points_with_lanes(db)
    oa = client.post(f"/refills/run?location_id={a.id}").json()
    ob = client.post(f"/refills/run?location_id={b.id}").json()

    latest_a = client.get(f"/refills/latest?location_id={a.id}").json()
    latest_b = client.get(f"/refills/latest?location_id={b.id}").json()
    assert latest_a["id"] == oa["id"]
    assert latest_b["id"] == ob["id"]
    a_lane_ids = {la.id}
    b_lane_ids = {lb1.id, lb2.id}
    assert {l["lane_id"] for l in latest_a["lines"]} == a_lane_ids
    assert {l["lane_id"] for l in latest_b["lines"]} == b_lane_ids

    full_b = client.get(f"/refills/full?location_id={b.id}").json()
    assert {l["lane_id"] for l in full_b["lanes"]} == {lb1.id}

    summary_a = client.get(f"/refills/summary?location_id={a.id}").json()
    assert summary_a["order_id"] == oa["id"]
    assert summary_a["total_fill"] == 15

    # 列表也不串
    list_a = client.get(f"/refills?location_id={a.id}").json()
    list_b = client.get(f"/refills?location_id={b.id}").json()
    assert len(list_a) == 1 and len(list_b) == 1


def test_void_lifecycle_and_latest_skips_void(client, db):
    loc = make_location(db)
    make_lane(db, loc.id, slot_no="A1", capacity=5, stock=0)
    first = client.post(f"/refills/run?location_id={loc.id}").json()
    second = client.post(f"/refills/run?location_id={loc.id}").json()

    r1 = client.post(f"/refills/{second['id']}/void?location_id={loc.id}")
    assert r1.status_code == 200
    assert r1.json()["status"] == "void"
    r2 = client.post(f"/refills/{second['id']}/void?location_id={loc.id}")
    assert r2.status_code == 409

    # 最新单作废后，latest 回退到更早的 active 单
    latest = client.get(f"/refills/latest?location_id={loc.id}").json()
    assert latest["id"] == first["id"]

    # 全部作废后 404
    client.post(f"/refills/{first['id']}/void?location_id={loc.id}")
    assert client.get(f"/refills/latest?location_id={loc.id}").status_code == 404


def test_void_other_locations_order_404(client, db):
    a, b, *_ = _two_points_with_lanes(db)
    ob = client.post(f"/refills/run?location_id={b.id}").json()
    # 持 A 点位上下文去作废 B 的单 —— 不泄露存在性
    r = client.post(f"/refills/{ob['id']}/void?location_id={a.id}")
    assert r.status_code == 404
    # B 的单仍是 active
    assert client.get(f"/refills/latest?location_id={b.id}").status_code == 200


def test_requested_qty_capped_by_gap(client, db):
    loc = make_location(db)
    lane = make_lane(db, loc.id, capacity=20, stock=5, in_transit=0)
    r = client.post(
        f"/refills/run?location_id={loc.id}",
        json={"lines": [{"lane_id": lane.id, "requested_qty": 100}]},
    )
    assert r.status_code == 201
    assert r.json()["lines"][0]["fill_qty"] == 15


def test_duplicate_lane_in_payload_400(client, db):
    loc = make_location(db)
    lane = make_lane(db, loc.id)
    r = client.post(
        f"/refills/run?location_id={loc.id}",
        json={"lines": [
            {"lane_id": lane.id, "requested_qty": 1},
            {"lane_id": lane.id, "requested_qty": 2},
        ]},
    )
    assert r.status_code == 400
    assert count_rows(db, RefillOrder) == 0
