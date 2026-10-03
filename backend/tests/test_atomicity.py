import app.services.refill_service as svc
from app.models.models import RefillOrder, RefillOrderLine
from tests.conftest import count_rows, make_lane, make_location


def test_header_and_lines_rollback_together(client, db, monkeypatch):
    """头 flush 成功后、行提交时失败：整笔回滚，不留头也不留半套行。"""
    real_summarize = svc.summarize

    def broken_summarize(lines):
        data = real_summarize(lines)
        for row in data["lines"]:
            row["status"] = None  # 触发 NOT NULL 约束
        return data

    monkeypatch.setattr(svc, "summarize", broken_summarize)

    loc = make_location(db)
    make_lane(db, loc.id)
    r = client.post(f"/refills/run?location_id={loc.id}")
    assert r.status_code == 500
    assert count_rows(db, RefillOrder, location_id=loc.id) == 0
    assert count_rows(db, RefillOrderLine) == 0


def test_sequential_runs_for_different_locations_commit_independently(client, db):
    a = make_location(db, code="VM-01", name="A")
    b = make_location(db, code="VM-02", name="B")
    make_lane(db, a.id, slot_no="A1")
    make_lane(db, b.id, slot_no="B1")
    assert client.post(f"/refills/run?location_id={a.id}").status_code == 201
    assert client.post(f"/refills/run?location_id={b.id}").status_code == 201
    assert count_rows(db, RefillOrder, location_id=a.id) == 1
    assert count_rows(db, RefillOrder, location_id=b.id) == 1
