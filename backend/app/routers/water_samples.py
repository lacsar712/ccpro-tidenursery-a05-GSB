from datetime import timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.pond import Pond
from app.models.user import User
from app.models.water_sample import WaterSample
from app.schemas.water_sample import WaterSampleCreate, WaterSampleOut
from app.services.calibration import get_latest_calibration, is_within_window, utcnow

router = APIRouter(prefix="/api/water-samples", tags=["water-samples"])


@router.get("", response_model=List[WaterSampleOut])
def list_samples(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(WaterSample)
    if pond_id is not None:
        q = q.filter(WaterSample.pond_id == pond_id)
    return q.order_by(WaterSample.sampled_at.desc()).all()


@router.post("", response_model=WaterSampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(
    payload: WaterSampleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")
    # 溶氧探头有效校准是新建水质样的前置条件，服务端强制拦截
    now = utcnow()
    latest = get_latest_calibration(db, payload.pond_id)
    if latest is None or not is_within_window(latest, now):
        if latest is None:
            reason = "该塘口无溶氧探头校准票"
        else:
            calibrated_at = latest.calibrated_at
            if calibrated_at.tzinfo is None:
                calibrated_at = calibrated_at.replace(tzinfo=timezone.utc)
            if calibrated_at > now:
                reason = f"该塘口最近校准票 #{latest.id} 的校准时刻尚未到达"
            else:
                reason = f"该塘口最近校准票 #{latest.id} 已过有效期"
        raise HTTPException(
            status_code=409,
            detail=f"{reason}，禁止新建水质样，请先完成溶氧探头校准",
        )
    item = WaterSample(
        pond_id=payload.pond_id,
        sampled_at=payload.sampled_at,
        temp_c=payload.temp_c,
        salinity_ppt=payload.salinity_ppt,
        do_mg_l=payload.do_mg_l,
        ph=payload.ph,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(WaterSample).filter(WaterSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="水质样不存在")
    db.delete(item)
    db.commit()
