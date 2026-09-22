"""溶氧探头校准时间窗判定。

有效性口径（删除或作废以外，唯一以本时间窗函数判定）：
取塘口最近一张校准票（按校准时刻倒序），当前时刻落在
[校准时刻, 校准时刻 + 有效小时数] 之内即为有效；无票、未来票、过期票均无效。
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.do_calibration import DoCalibration

READING_TOLERANCE = 0.5


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_latest_calibration(db: Session, pond_id: int) -> Optional[DoCalibration]:
    """塘口最近一张校准票；无票返回 None。"""
    return (
        db.query(DoCalibration)
        .filter(DoCalibration.pond_id == pond_id)
        .order_by(DoCalibration.calibrated_at.desc(), DoCalibration.id.desc())
        .first()
    )


def is_within_window(ticket: DoCalibration, now: datetime) -> bool:
    calibrated_at = ticket.calibrated_at
    if calibrated_at.tzinfo is None:
        calibrated_at = calibrated_at.replace(tzinfo=timezone.utc)
    if calibrated_at > now:
        # 校准时刻尚在未来，时间窗还未起算
        return False
    return now <= calibrated_at + timedelta(hours=ticket.valid_hours)


def get_pond_validity(db: Session, pond_id: int, now: Optional[datetime] = None) -> bool:
    now = now or utcnow()
    ticket = get_latest_calibration(db, pond_id)
    return ticket is not None and is_within_window(ticket, now)


def get_latest_map(db: Session, pond_ids: Iterable[int]) -> Dict[int, DoCalibration]:
    """批量取每个塘口最近一张校准票（单条 SQL，排序口径同 get_latest_calibration）。"""
    ids = list(pond_ids)
    if not ids:
        return {}
    tickets = (
        db.query(DoCalibration)
        .filter(DoCalibration.pond_id.in_(ids))
        .order_by(DoCalibration.calibrated_at.desc(), DoCalibration.id.desc())
        .all()
    )
    grouped: Dict[int, DoCalibration] = {}
    for ticket in tickets:
        if ticket.pond_id not in grouped:
            grouped[ticket.pond_id] = ticket
    return grouped


def get_validity_map(
    db: Session, pond_ids: Iterable[int], now: Optional[datetime] = None
) -> Dict[int, bool]:
    """批量判定塘口校准是否有效；无票塘口显式为 False。"""
    now = now or utcnow()
    ids = list(pond_ids)
    latest = get_latest_map(db, ids)
    return {pid: pid in latest and is_within_window(latest[pid], now) for pid in ids}
