"""多点位隔离：五处只服务当前点位，跨点写与本点写互斥。"""
import pytest

from tests.conftest import add_lane, make_location, order_count, switch


def test_seed_current_is_vm01(client, vm01_id):
    cur = client.get("/api/locations/current").json()
    assert cur["id"] == vm01_id
    assert cur["code"] == "VM-01"


def test_five_views_scoped_to_current(client, vm01_id):
    b = make_location(client)
    switch(client, b["id"])
    assert add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=8).status_code == 201
    assert add_lane(client, slot="D2", sku="红茶", capacity=10, stock=2).status_code == 201
    assert client.post("/api/refills/run").status_code == 200
    switch(client, vm01_id)

    # 货道：看不到 B 的货道
    lanes = client.get("/api/lanes").json()
    assert lanes and all(l["location_id"] == vm01_id for l in lanes)
    assert {l["slot_no"] for l in lanes}.isdisjoint({"D1", "D2"})
    # 销量：全部属于 VM-01 的货道
    sales = client.get("/api/sales").json()
    assert sales and all(s["location_id"] == vm01_id for s in sales)
    # 补货单：B 的单不得出现在 VM-01 视图
    assert client.get("/api/refills").json() == []
    # 满仓：只列 VM-01 满仓货道（A2 可乐 18/18、B2 巧克力 15=10+5）
    full = client.get("/api/refills/full").json()
    assert full["location_id"] == vm01_id
    assert {l["slot_no"] for l in full["lanes"]} == {"A2", "B2"}
    # 汇总：只统计 VM-01
    s = client.get("/api/refills/summary").json()
    assert s["location_id"] == vm01_id
    assert s["full_count"] == 2 and s["overbooked_count"] == 1

    # 切到 B：五处只看到 B
    switch(client, b["id"])
    assert {l["slot_no"] for l in client.get("/api/lanes").json()} == {"D1", "D2"}
    assert client.get("/api/sales").json() == []
    orders = client.get("/api/refills").json()
    assert len(orders) == 1 and orders[0]["location_id"] == b["id"]
    assert {l["slot_no"] for l in client.get("/api/refills/full").json()["lanes"]} == {"D1"}
    assert client.get("/api/refills/summary").json()["location_id"] == b["id"]


@pytest.mark.parametrize("path", [
    "/api/lanes", "/api/sales", "/api/refills",
    "/api/refills/latest", "/api/refills/full", "/api/refills/summary",
])
def test_explicit_cross_location_read_rejected(client, vm01_id, path):
    b = make_location(client)
    r = client.get(path, params={"location_id": b["id"]})  # 当前仍是 VM-01
    assert r.status_code == 409, f"{path} 串点应拒绝"
    r = client.get(path, params={"location_id": vm01_id})
    assert r.status_code in (200, 404), f"{path} 本点应放行"


def test_cross_location_run_rejected_both_counts_unchanged(client, vm01_id):
    b = make_location(client)
    switch(client, b["id"])
    add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=1)
    switch(client, vm01_id)
    before_a, before_b = order_count(client, vm01_id), order_count(client, b["id"])

    # 当前点位是 VM-01，却冒充向 B 生成补货单 → 必须拒绝
    r = client.post("/api/refills/run", params={"location_id": b["id"]})
    assert r.status_code == 409
    assert order_count(client, vm01_id) == before_a  # A 行数不增
    assert order_count(client, b["id"]) == before_b  # B 行数不增


def test_latest_never_writes(client, vm01_id):
    b = make_location(client)
    switch(client, b["id"])
    add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=1)
    before_a, before_b = order_count(client, vm01_id), order_count(client, b["id"])

    assert client.get("/api/refills/latest").status_code == 404  # 无单不代写
    assert client.get("/api/refills/full").status_code == 200
    assert client.get("/api/refills/summary").status_code == 200
    assert client.get("/api/refills/latest", params={"location_id": vm01_id}).status_code == 409
    assert order_count(client, vm01_id) == before_a
    assert order_count(client, b["id"]) == before_b


def test_run_and_void_happy_path(client, vm01_id):
    b = make_location(client)
    switch(client, b["id"])
    add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=1)
    before_a = order_count(client, vm01_id)

    r = client.post("/api/refills/run")
    assert r.status_code == 200
    body = r.json()
    assert body["location_id"] == b["id"] and body["status"] == "active"
    assert order_count(client, b["id"]) == 1
    assert order_count(client, vm01_id) == before_a

    latest = client.get("/api/refills/latest").json()
    assert latest["id"] == body["id"]

    v = client.post(f"/api/refills/{body['id']}/void")
    assert v.status_code == 200 and v.json()["status"] == "void"


def test_void_cross_location_rejected(client, vm01_id):
    b = make_location(client)
    switch(client, b["id"])
    add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=1)
    oid = client.post("/api/refills/run").json()["id"]
    switch(client, vm01_id)
    r = client.post(f"/api/refills/{oid}/void")  # 当前 VM-01，单属于 B
    assert r.status_code == 409
    assert client.get("/api/refills", params={"location_id": vm01_id}).status_code == 200


def test_run_rolls_back_when_location_switches_mid_generation(client, vm01_id, monkeypatch):
    """生成过程中点位被切换：半套单必须回滚，不留跨点脏行。"""
    b = make_location(client)
    switch(client, b["id"])
    add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=1)
    before_a, before_b = order_count(client, vm01_id), order_count(client, b["id"])

    # 模拟“提交前一刻当前点位被切走”：复核读到的当前点位不再是目标点位
    import app.api.refills as refills_api
    monkeypatch.setattr(refills_api, "peek_current_location_id", lambda db: vm01_id)

    r = client.post("/api/refills/run")
    assert r.status_code == 409
    assert order_count(client, vm01_id) == before_a
    assert order_count(client, b["id"]) == before_b  # 无脏行残留


def test_delete_location_guards(client, vm01_id):
    b = make_location(client)
    switch(client, b["id"])
    add_lane(client, slot="D1", sku="苏打水", capacity=8, stock=1)
    oid = client.post("/api/refills/run").json()["id"]
    switch(client, vm01_id)

    # 仍有未作废补货单 → 拒绝删除并保留数据
    r = client.delete(f"/api/locations/{b['id']}")
    assert r.status_code == 409
    assert any(l["id"] == b["id"] for l in client.get("/api/locations").json())
    assert order_count(client, b["id"]) == 1

    # 作废后无有效单 → 可删，货道与单随点位清除
    switch(client, b["id"])
    assert client.post(f"/api/refills/{oid}/void").status_code == 200
    switch(client, vm01_id)
    r = client.delete(f"/api/locations/{b['id']}")
    assert r.status_code == 200
    assert all(l["id"] != b["id"] for l in client.get("/api/locations").json())
    assert order_count(client, b["id"]) == 0

    # 无单点位直接可删
    c = make_location(client, code="VM-03", name="公园 C 点位")
    assert client.delete(f"/api/locations/{c['id']}").status_code == 200


def test_delete_current_location_rejected(client, vm01_id):
    assert client.delete(f"/api/locations/{vm01_id}").status_code == 409
    assert client.get("/api/locations/current").json()["id"] == vm01_id


def test_delete_missing_location_404(client):
    assert client.delete("/api/locations/9999").status_code == 404


def test_location_create_and_switch_validation(client, vm01_id):
    assert client.post("/api/locations", json={"code": "VM-01", "name": "重复"}).status_code == 409
    assert client.put("/api/locations/current", json={"location_id": 9999}).status_code == 404
    b = make_location(client)
    assert client.get("/api/locations/current").json()["id"] == vm01_id  # 新建不自动切换
    switch(client, b["id"])
    assert client.get("/api/locations/current").json()["id"] == b["id"]


def test_lane_maintenance_scoped_to_current(client, vm01_id):
    b = make_location(client)
    # 显式跨点建货道 → 409
    r = add_lane(client, slot="X1", sku="薯片", location_id=b["id"])
    assert r.status_code == 409
    # 缺省落到当前点位
    r = add_lane(client, slot="X1", sku="薯片", capacity=5, stock=2)
    assert r.status_code == 201
    lane = r.json()
    assert lane["location_id"] == vm01_id and lane["gap"] == 3
    # 同点位货道号唯一
    assert add_lane(client, slot="X1", sku="别的").status_code == 409
    # 改 / 删本点货道
    r = client.patch(f"/api/lanes/{lane['id']}", json={"stock": 5})
    assert r.status_code == 200 and r.json()["gap"] == 0
    assert client.delete(f"/api/lanes/{lane['id']}").status_code == 200

    # B 的货道：切走后就碰不到
    switch(client, b["id"])
    r = add_lane(client, slot="D1", sku="苏打水")
    assert r.status_code == 201
    b_lane = r.json()
    switch(client, vm01_id)
    assert client.patch(f"/api/lanes/{b_lane['id']}", json={"stock": 1}).status_code == 409
    assert client.delete(f"/api/lanes/{b_lane['id']}").status_code == 409


def test_seeded_second_location_invisible_from_vm01(client, vm01_id):
    """验收场景：新建点位生成后切回 VM-01，不得看见新点货道或单据；冒充写入失败且 VM-01 单数不变。"""
    b = make_location(client, code="VM-02", name="商场 B 点位")
    switch(client, b["id"])
    add_lane(client, slot="E1", sku="咖啡", capacity=12, stock=3)
    add_lane(client, slot="E2", sku="奶茶", capacity=12, stock=12)
    assert client.post("/api/refills/run").status_code == 200
    switch(client, vm01_id)

    lanes = client.get("/api/lanes").json()
    assert {l["slot_no"] for l in lanes}.isdisjoint({"E1", "E2"})
    assert client.get("/api/refills").json() == []
    assert client.get("/api/refills/latest").status_code == 404

    before = order_count(client, vm01_id)
    r = client.post("/api/refills/run", params={"location_id": b["id"]})
    assert r.status_code == 409
    assert order_count(client, vm01_id) == before
    assert order_count(client, b["id"]) == 1
