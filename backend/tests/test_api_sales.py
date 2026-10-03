from tests.conftest import make_lane, make_location, make_sale


def test_sales_scoped_per_location(client, db):
    a = make_location(db, code="VM-01", name="A")
    b = make_location(db, code="VM-02", name="B")
    la = make_lane(db, a.id, slot_no="A1")
    lb = make_lane(db, b.id, slot_no="A1")
    make_sale(db, a.id, la.id, qty=2)
    make_sale(db, a.id, la.id, qty=4)
    make_sale(db, b.id, lb.id, qty=9)

    ra = client.get(f"/sales?location_id={a.id}").json()
    rb = client.get(f"/sales?location_id={b.id}").json()
    assert len(ra) == 2
    assert len(rb) == 1
    assert {x["qty"] for x in ra} == {2, 4}
    assert rb[0]["qty"] == 9
    assert all(x["location_id"] == a.id for x in ra)
    assert rb[0]["slot_no"] == "A1"


def test_sales_missing_param_422(client):
    assert client.get("/sales").status_code == 422


def test_sales_unknown_location_404(client):
    assert client.get("/sales?location_id=999").status_code == 404
