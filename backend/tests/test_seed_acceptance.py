from app.models.models import Lane, Location, RefillOrder, Sale
from app.services.seed import seed_if_empty
from tests.conftest import count_rows, make_lane


def _seed_vm01(client, db):
    seed_if_empty(db)

    locs = client.get("/locations").json()
    assert [(x["code"], x["lane_count"], x["active_order_count"]) for x in locs] == [
        ("VM-01", 6, 0)]
    vm01 = locs[0]

    lanes = client.get(f"/lanes?location_id={vm01['id']}").json()
    sales = client.get(f"/sales?location_id={vm01['id']}").json()
    assert len(lanes) == 6
    assert len(sales) == 6
    assert all(x["location_id"] == vm01["id"] for x in lanes)
    assert all(x["location_id"] == vm01["id"] for x in sales)
    assert count_rows(db, RefillOrder) == 0
    return vm01


def test_seed_creates_only_vm01_scoped_rows(client, db):
    _seed_vm01(client, db)


def test_switch_back_to_vm01_sees_no_new_location_data(client, db):
    vm01 = _seed_vm01(client, db)

    # 新建第二点位、维护货道、生成补货单
    r = client.post("/locations", json={"code": "VM-02", "name": "地铁口 B 点位"})
    assert r.status_code == 201
    vm02 = r.json()
    lane_b = client.post("/lanes", json={
        "location_id": vm02["id"], "slot_no": "D1", "sku_name": "苏打水",
        "capacity": 10, "stock": 2}).json()
    assert client.post(f"/refills/run?location_id={vm02['id']}").status_code == 201

    # 切回 VM-01：货道/销量/单据都不含 VM-02
    lanes_01 = client.get(f"/lanes?location_id={vm01['id']}").json()
    sales_01 = client.get(f"/sales?location_id={vm01['id']}").json()
    orders_01 = client.get(f"/refills?location_id={vm01['id']}").json()
    assert lane_b["id"] not in {x["id"] for x in lanes_01}
    assert len(lanes_01) == 6
    assert len(sales_01) == 6
    assert orders_01 == []
    assert client.get(f"/refills/latest?location_id={vm01['id']}").status_code == 404


def test_impersonated_cross_write_fails_and_counts_unchanged(client, db):
    vm01 = _seed_vm01(client, db)
    vm02 = client.post("/locations", json={"code": "VM-02", "name": "B"}).json()
    make_lane(db, vm02["id"], slot_no="D1", sku_name="苏打水", capacity=10, stock=2)
    lane_a = client.get(f"/lanes?location_id={vm01['id']}").json()[0]

    before = (count_rows(db, RefillOrder, location_id=vm01["id"]),
              count_rows(db, RefillOrder, location_id=vm02["id"]))

    # 以 VM-02 为目标，夹带 VM-01 的货道 —— 冒充写入必须失败
    r = client.post(
        f"/refills/run?location_id={vm02['id']}",
        json={"lines": [{"lane_id": lane_a["id"], "requested_qty": 1}]},
    )
    assert r.status_code == 400

    after = (count_rows(db, RefillOrder, location_id=vm01["id"]),
             count_rows(db, RefillOrder, location_id=vm02["id"]))
    assert before == after == (0, 0)

    # 反向同理：持 VM-01 上下文夹带 VM-02 货道
    lane_b = client.get(f"/lanes?location_id={vm02['id']}").json()[0]
    r = client.post(
        f"/refills/run?location_id={vm01['id']}",
        json={"lines": [{"lane_id": lane_b["id"], "requested_qty": 1}]},
    )
    assert r.status_code == 400
    assert (count_rows(db, RefillOrder, location_id=vm01["id"]),
            count_rows(db, RefillOrder, location_id=vm02["id"])) == (0, 0)
