from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DoCalibrationCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    calibrated_at: datetime = Field(..., alias="calibratedAt")
    standard_reading: float = Field(..., alias="standardReading")
    device_reading: float = Field(..., alias="deviceReading")
    valid_hours: int = Field(..., gt=0, alias="validHours")
    calibrator: str = Field(..., min_length=1, max_length=64)

    model_config = ConfigDict(populate_by_name=True)


class DoCalibrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    calibrated_at: datetime = Field(serialization_alias="calibratedAt")
    standard_reading: float = Field(serialization_alias="standardReading")
    device_reading: float = Field(serialization_alias="deviceReading")
    valid_hours: int = Field(serialization_alias="validHours")
    calibrator: str
