from datetime import datetime

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DoCalibration(Base):
    """溶氧探头校准票：以校准时刻 + 有效小时数构成的时间窗判定有效性。"""

    __tablename__ = "do_calibrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(ForeignKey("ponds.id"), nullable=False, index=True)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    standard_reading: Mapped[float] = mapped_column(Float, nullable=False)
    device_reading: Mapped[float] = mapped_column(Float, nullable=False)
    valid_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    calibrator: Mapped[str] = mapped_column(String(64), nullable=False)

    pond: Mapped["Pond"] = relationship("Pond", back_populates="do_calibrations")
