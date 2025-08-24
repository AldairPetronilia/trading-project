"""Price data models for energy market pricing information."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import TimestampedModel
from .load_data import EnergyDataType


class EnergyPricePoint(TimestampedModel):
    """
    Energy price data model for time-series market pricing information.

    Stores day-ahead and other market price data with currency support
    and market context information. Uses the same composite primary key
    pattern as EnergyDataPoint for consistency.
    """

    __tablename__ = "energy_price_points"

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

    price_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=6),
        nullable=False,
    )

    currency_unit_name: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    price_measure_unit_name: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    auction_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    contract_market_agreement_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
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

    curve_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
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
        Index("ix_energy_price_timestamp_area", "timestamp", "area_code"),
        Index("ix_energy_price_type_timestamp", "data_type", "timestamp"),
        Index("ix_energy_price_document_mrid", "document_mrid"),
        Index(
            "ix_energy_price_area_type_timestamp",
            "area_code",
            "data_type",
            "timestamp",
        ),
        Index("ix_energy_price_currency", "currency_unit_name"),
        Index("ix_energy_price_auction_type", "auction_type"),
    )
