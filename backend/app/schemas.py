from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    address: str = Field(default="", max_length=256)


class LaneCreate(BaseModel):
    location_id: int
    slot_no: str = Field(min_length=1, max_length=16)
    sku_name: str = Field(min_length=1, max_length=64)
    capacity: int = Field(ge=1)
    stock: int = Field(default=0, ge=0)
    in_transit: int = Field(default=0, ge=0)


class RequestedLine(BaseModel):
    lane_id: int
    requested_qty: int = Field(ge=0)


class RunRefillBody(BaseModel):
    # 可选：只对部分货道给出期望补货量；缺省按缺口全补。
    lines: list[RequestedLine] = Field(default_factory=list)
