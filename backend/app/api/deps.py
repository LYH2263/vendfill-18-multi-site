from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Location


def get_location_or_404(location_id: int, db: Session) -> Location:
    loc = db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="点位不存在")
    return loc
