import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


# 单连接内存库：ASGI 应用与测试代码共享同一份 schema/数据。
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            # 不在此关闭 session：db fixture 统一管理生命周期。
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # 不使用 with：避免触发 lifespan（连 postgres / 自动种子）。
    from fastapi.testclient import TestClient

    class ApiClient:
        def __init__(self):
            self._c = TestClient(app)

        def get(self, path, **kw):
            return self._c.get("/api" + path, **kw)

        def post(self, path, **kw):
            return self._c.post("/api" + path, **kw)

        def delete(self, path, **kw):
            return self._c.delete("/api" + path, **kw)

    yield ApiClient()
    app.dependency_overrides.clear()


def make_location(db, code="VM-02", name="二号点", address=""):
    from app.models.models import Location
    loc = Location(code=code, name=name, address=address)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def make_lane(db, location_id, slot_no="A1", sku_name="水",
              capacity=20, stock=5, in_transit=0):
    from app.models.models import Lane
    lane = Lane(location_id=location_id, slot_no=slot_no, sku_name=sku_name,
                capacity=capacity, stock=stock, in_transit=in_transit)
    db.add(lane)
    db.commit()
    db.refresh(lane)
    return lane


def make_sale(db, location_id, lane_id, qty=1):
    from datetime import datetime
    from app.models.models import Sale
    sale = Sale(location_id=location_id, lane_id=lane_id, qty=qty,
                sold_at=datetime.utcnow())
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


def count_rows(db, model, **filters):
    from sqlalchemy import func, select
    return db.scalar(select(func.count()).select_from(model).filter_by(**filters)) or 0
