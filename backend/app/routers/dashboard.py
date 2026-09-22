from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.feed_event import FeedEvent
from app.models.pond import Pond
from app.models.user import User
from app.models.water_sample import WaterSample
from app.schemas.dashboard import DashboardStats
from app.services.calibration import calibration_map

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    pond_total = db.query(func.count(Pond.id)).scalar() or 0
    quarantine_count = (
        db.query(func.count(Pond.id)).filter(Pond.status == "quarantine").scalar() or 0
    )
    samples_last_24h = (
        db.query(func.count(WaterSample.id))
        .filter(WaterSample.sampled_at >= now - timedelta(hours=24))
        .scalar()
        or 0
    )
    feed_kg_last_7d = (
        db.query(func.coalesce(func.sum(FeedEvent.amount_kg), 0.0))
        .filter(FeedEvent.fed_at >= now - timedelta(days=7))
        .scalar()
        or 0.0
    )
    # 校准失效塘数：与塘口列表 calibrationValid=false 行同一口径。
    pond_ids = [row[0] for row in db.query(Pond.id).order_by(Pond.id).all()]
    cal = calibration_map(db, pond_ids, now)
    calibration_invalid_count = sum(1 for _, valid in cal.values() if not valid)
    return DashboardStats(
        pond_total=pond_total,
        quarantine_count=quarantine_count,
        samples_last_24h=samples_last_24h,
        feed_kg_last_7d=float(feed_kg_last_7d),
        calibration_invalid_count=calibration_invalid_count,
    )
