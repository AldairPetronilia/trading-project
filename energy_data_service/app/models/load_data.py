from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import TimestampedModel


class EnergyDataType(str, Enum):
    ACTUAL = "actual"
    DAY_AHEAD = "day_ahead"
    WEEK_AHEAD = "week_ahead"
    MONTH_AHEAD = "month_ahead"
    YEAR_AHEAD = "year_ahead"
    FORECAST_MARGIN = "forecast_margin"


class EnergyDataPoint(TimestampedModel):
    __tablename__ = "energy_data_points"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )

    area_code: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    data_type: Mapped[EnergyDataType] = mapped_column(
        primary_key=True,
    )

    business_type: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=3),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="MAW",
    )

    data_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="entsoe",
    )

    document_mrid: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    revision_number: Mapped[int | None] = mapped_column()

    document_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    time_series_mrid: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resolution: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    curve_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    object_aggregation: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(nullable=False)

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_energy_data_timestamp_area", "timestamp", "area_code"),
        Index("ix_energy_data_type_timestamp", "data_type", "timestamp"),
        Index("ix_energy_data_document_mrid", "document_mrid"),
        Index(
            "ix_energy_data_area_type_timestamp",
            "area_code",
            "data_type",
            "timestamp",
        ),
    )
