"""溶氧探头校准票有效性判定。

唯一口径：以该塘口「最近一张校准票」的校准时刻为起点，
在其有效小时数窗口内（含端点）视为有效；无票或窗口已过均为失效。
删除票即删除记录本身，不另设作废标志。
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.do_calibration import DoCalibration

READING_TOLERANCE = 0.5


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    # PostgreSQL 驱动返回带时区时间；SQLite 等可能返回 naive 时间，按 UTC 处理。
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def latest_calibration(db: Session, pond_id: int) -> Optional[DoCalibration]:
    return (
        db.query(DoCalibration)
        .filter(DoCalibration.pond_id == pond_id)
        .order_by(DoCalibration.calibrated_at.desc(), DoCalibration.id.desc())
        .first()
    )


def is_calibration_valid(cal: Optional[DoCalibration], now: Optional[datetime] = None) -> bool:
    """时间窗判定：calibrated_at <= now <= calibrated_at + valid_hours。"""
    if cal is None:
        return False
    now = now or utcnow()
    start = _as_aware(cal.calibrated_at)
    end = start + timedelta(hours=cal.valid_hours)
    return start <= now <= end


def calibration_map(
    db: Session, pond_ids: Iterable[int], now: Optional[datetime] = None
) -> Dict[int, Tuple[Optional[DoCalibration], bool]]:
    """批量取每个塘口的最近票及有效性，供塘口列表与仪表盘共用。"""
    now = now or utcnow()
    ids = list(pond_ids)
    result: Dict[int, Tuple[Optional[DoCalibration], bool]] = {
        pid: (None, False) for pid in ids
    }
    if not ids:
        return result

    # 每塘口取校准时刻最新的一张票（允许补录历史票，按时刻而非 id 判定）。
    rows = (
        db.query(DoCalibration)
        .filter(DoCalibration.pond_id.in_(ids))
        .order_by(DoCalibration.calibrated_at.desc(), DoCalibration.id.desc())
        .all()
    )
    by_pond: Dict[int, DoCalibration] = {}
    for cal in rows:
        if cal.pond_id not in by_pond:
            by_pond[cal.pond_id] = cal

    for pid in ids:
        cal = by_pond.get(pid)
        result[pid] = (cal, is_calibration_valid(cal, now))
    return result
