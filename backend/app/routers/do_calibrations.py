from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.do_calibration import DoCalibration
from app.models.pond import Pond
from app.models.user import User
from app.schemas.do_calibration import DoCalibrationCreate, DoCalibrationOut
from app.services.calibration import READING_TOLERANCE, is_calibration_valid

router = APIRouter(prefix="/api/do-calibrations", tags=["do-calibrations"])


@router.get("", response_model=List[DoCalibrationOut])
def list_calibrations(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(DoCalibration)
    if pond_id is not None:
        q = q.filter(DoCalibration.pond_id == pond_id)
    rows = q.order_by(
        DoCalibration.calibrated_at.desc(), DoCalibration.id.desc()
    ).all()
    return [
        DoCalibrationOut.model_validate(cal).model_copy(
            update={"valid": is_calibration_valid(cal)}
        )
        for cal in rows
    ]


@router.post("", response_model=DoCalibrationOut, status_code=status.HTTP_201_CREATED)
def create_calibration(
    payload: DoCalibrationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")
    if abs(payload.device_reading - payload.standard_reading) > READING_TOLERANCE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"实机读数与标准液读数偏差 "
                f"{abs(payload.device_reading - payload.standard_reading):.2f} mg/L "
                f"超过 ±{READING_TOLERANCE}，校准失败"
            ),
        )
    item = DoCalibration(
        pond_id=payload.pond_id,
        calibrated_at=payload.calibrated_at,
        standard_reading=payload.standard_reading,
        device_reading=payload.device_reading,
        valid_hours=payload.valid_hours,
        operator_name=payload.operator_name,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    out = DoCalibrationOut.model_validate(item)
    return out.model_copy(update={"valid": is_calibration_valid(item)})


@router.delete("/{calibration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calibration(
    calibration_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(DoCalibration).filter(DoCalibration.id == calibration_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="校准票不存在")
    db.delete(item)
    db.commit()
