"""
PublicationMarketDocumentProcessor for transforming ENTSO-E market documents.

Handles conversion from PublicationMarketDocument (market price data)
to EnergyPricePoint models for database storage.
"""

import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, ClassVar

from app.exceptions.processor_exceptions import (
    DocumentParsingError,
    MappingError,
    TimestampCalculationError,
    TransformationError,
)
from app.models.load_data import EnergyDataType
from app.models.price_data import EnergyPricePoint
from app.processors.base_processor import BaseProcessor
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

from entsoe_client.model.common.document_type import DocumentType
from entsoe_client.model.common.process_type import ProcessType
from entsoe_client.model.market.publication_market_document import (
    PublicationMarketDocument,
)

log = logging.getLogger(__name__)


class DurationComponents:
    """Components for representing ISO 8601 duration."""

    def __init__(
        self,
        years: int = 0,
        months: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
    ) -> None:
        self.years = years
        self.months = months
        self.days = days
        self.hours = hours
        self.minutes = minutes


class PublicationMarketDocumentProcessor(
    BaseProcessor[PublicationMarketDocument, EnergyPricePoint]
):
    """
    Processor for transforming ENTSO-E PublicationMarketDocument into EnergyPricePoint models.

    Handles the complex transformation from nested ENTSO-E market XML structure to
    database-ready price data points with proper timestamp calculation,
    currency handling, and market type mapping.
    """

    _TYPE_MAPPING: ClassVar[dict[tuple[ProcessType, DocumentType], EnergyDataType]] = {
        (ProcessType.DAY_AHEAD, DocumentType.PRICE_DOCUMENT): EnergyDataType.DAY_AHEAD,
        # Add more price-specific mappings as needed
    }

    async def process(
        self, raw_data: list[PublicationMarketDocument]
    ) -> list[EnergyPricePoint]:
        """
        Transform PublicationMarketDocument objects into EnergyPricePoint models.

        Args:
            raw_data: List of PublicationMarketDocument objects from ENTSO-E API

        Returns:
            List of EnergyPricePoint models ready for database storage

        Raises:
            DocumentParsingError: When document structure is invalid
            MappingError: When ProcessType mapping fails
            TimestampCalculationError: When timestamp calculation fails
            TransformationError: When data transformation fails
        """
        await self.validate_input(raw_data)

        energy_price_points: list[EnergyPricePoint] = []

        for document in raw_data:
            try:
                document_points = await self._process_document(document)
                energy_price_points.extend(document_points)
            except Exception as e:
                msg = f"Failed to process document {document.mRID}"
                raise TransformationError(
                    msg,
                    processor_type=self.__class__.__name__,
                    operation="document_processing",
                    context={"document_mrid": document.mRID},
                ) from e

        await self.validate_output(energy_price_points)
        return energy_price_points

    async def _process_document(
        self, document: PublicationMarketDocument
    ) -> list[EnergyPricePoint]:
        """
        Process a single PublicationMarketDocument into EnergyPricePoint models.

        Args:
            document: PublicationMarketDocument to transform

        Returns:
            List of EnergyPricePoint models from the document

        Raises:
            DocumentParsingError: When document structure parsing fails
            MappingError: When ProcessType mapping fails
            TimestampCalculationError: When timestamp calculation fails
        """
        points: list[EnergyPricePoint] = []

        try:
            # Map ProcessType + DocumentType combination to EnergyDataType
            # For now, assume DAY_AHEAD process type for price documents
            data_type = self._map_document_to_energy_data_type(
                ProcessType.DAY_AHEAD, document.type
            )

            log.info(
                "Processing document %s with %d TimeSeries",
                document.mRID,
                len(document.timeSeries),
            )

            for time_series in document.timeSeries:
                if time_series.period is None:
                    continue

                series_points = await self._process_time_series(
                    document=document, data_type=data_type, time_series=time_series
                )
                points.extend(series_points)

        except Exception as e:
            if isinstance(e, MappingError | TimestampCalculationError):
                raise
            msg = f"Failed to parse document structure: {e}"
            raise DocumentParsingError(
                msg,
                document_type="PublicationMarketDocument",
                document_id=document.mRID,
                parsing_stage="document_processing",
            ) from e
        else:
            return points

    async def _process_time_series(
        self,
        document: PublicationMarketDocument,
        data_type: EnergyDataType,
        time_series: Any,  # MarketTimeSeries type
    ) -> list[EnergyPricePoint]:
        """
        Process a single TimeSeries within a PublicationMarketDocument.

        Args:
            document: The parent PublicationMarketDocument
            data_type: Mapped EnergyDataType for this document
            time_series: Individual TimeSeries to process

        Returns:
            List of EnergyPricePoint models from this TimeSeries
        """
        # Extract area code from domain MRID
        area_code = self._extract_area_code(time_series.out_domain_mRID)

        points: list[EnergyPricePoint] = []
        period = time_series.period

        log.debug(
            "Processing TimeSeries %s: period from %s to %s with resolution %s",
            time_series.mRID,
            period.timeInterval.start,
            period.timeInterval.end,
            period.resolution,
        )

        for point in period.points:
            if point.position is None or point.price_amount is None:
                continue

            # Calculate timestamp for this price point
            timestamp = self._calculate_point_timestamp(
                period_start=period.timeInterval.start,
                resolution=period.resolution,
                position=point.position,
            )

            price_point = EnergyPricePoint(
                timestamp=timestamp,
                area_code=area_code,
                data_type=data_type,
                business_type=time_series.businessType.code,
                price_amount=Decimal(str(point.price_amount)),
                currency_unit_name=time_series.currency_unit_name or "EUR",
                price_measure_unit_name=time_series.price_measure_unit_name
                or "EUR/MWh",
                auction_type=time_series.auction_type.code
                if time_series.auction_type
                else None,
                contract_market_agreement_type=(
                    time_series.contract_market_agreement_type.code
                    if time_series.contract_market_agreement_type
                    else None
                ),
                # Add missing required fields
                document_mrid=document.mRID,
                time_series_mrid=time_series.mRID,
                resolution=period.resolution,
                document_created_at=document.createdDateTime,  # Fixed: use correct field name
                position=point.position,
                period_start=period.timeInterval.start,
                period_end=period.timeInterval.end,
            )
            points.append(price_point)

        log.debug(
            "Processed TimeSeries %s: %d points from %s to %s",
            time_series.mRID,
            len(points),
            period.timeInterval.start,
            period.timeInterval.end,
        )

        return points

    def _map_document_to_energy_data_type(
        self, process_type: ProcessType, document_type: DocumentType
    ) -> EnergyDataType:
        """
        Map ENTSO-E ProcessType + DocumentType combination to internal EnergyDataType enum.

        Args:
            process_type: ENTSO-E ProcessType enum value
            document_type: ENTSO-E DocumentType enum value

        Returns:
            Corresponding EnergyDataType enum value

        Raises:
            MappingError: When combination is not supported
        """
        type_key = (process_type, document_type)

        if type_key not in self._TYPE_MAPPING:
            available_mappings = [
                f"{pt.code}+{dt.code}" for pt, dt in self._TYPE_MAPPING
            ]
            source_code = f"{process_type.code}+{document_type.code}"
            msg = f"Unsupported ProcessType+DocumentType combination: {source_code}"
            raise MappingError(
                msg,
                source_code=source_code,
                source_type="ProcessType+DocumentType",
                target_type="EnergyDataType",
                available_mappings=available_mappings,
            )

        return self._TYPE_MAPPING[type_key]

    def _extract_area_code(self, domain_mrid: Any) -> str:
        """
        Extract clean area code from ENTSO-E domain MRID.

        Args:
            domain_mrid: ENTSO-E domain MRID object containing area code

        Returns:
            Clean area code string (e.g., "DE", "FR")

        Raises:
            TransformationError: When area code extraction fails
        """
        try:
            if domain_mrid is None:
                return "UNKNOWN"

            country_code = domain_mrid.area_code.area_code
            if country_code:
                return str(country_code)
            # Fallback to description parsing if area_code is not available
            area_code_desc = str(domain_mrid.area_code.description).strip()
            if area_code_desc:
                area_match = re.search(r"\(([A-Z]{2})\)", area_code_desc)
                if area_match:
                    return area_match.group(1)

                return area_code_desc.replace(" ", "")[:10]

        except Exception as e:
            domain_value = getattr(domain_mrid, "value", str(domain_mrid))
            msg = f"Failed to extract area code from domain MRID: {domain_value}"
            raise TransformationError(
                msg,
                transformation_type="area_code_extraction",
                source_value=domain_value,
                target_type="str",
            ) from e
        else:
            return str(domain_mrid.area_code.area_code)

    def _calculate_point_timestamp(
        self,
        period_start: datetime,
        resolution: str,
        position: int,
    ) -> datetime:
        """
        Calculate timestamp for a price point based on period start, resolution, and position.

        Uses native datetime operations for accuracy with years, months, and days.
        Properly handles leap years and variable month lengths.

        Args:
            period_start: Start time of the period
            resolution: ISO 8601 duration string (e.g., "PT15M", "PT60M", "P1D")
            position: Position of the point in the time series (1-based)

        Returns:
            Calculated timestamp for the price point

        Raises:
            TimestampCalculationError: When timestamp calculation fails
        """
        try:
            duration = self._parse_iso_duration_to_components(resolution)
            offset = position - 1
            timestamp = period_start

            if duration.years > 0 or duration.months > 0:
                timestamp += relativedelta(
                    years=duration.years * offset, months=duration.months * offset
                )

            if duration.days > 0 or duration.hours > 0 or duration.minutes > 0:
                timestamp += timedelta(
                    days=duration.days * offset,
                    hours=duration.hours * offset,
                    minutes=duration.minutes * offset,
                )

        except Exception as e:
            msg = f"Failed to calculate timestamp for position {position}"
            raise TimestampCalculationError(
                msg,
                resolution=resolution,
                period_start=period_start.isoformat() if period_start else None,
                position=position,
            ) from e
        else:
            return timestamp

    def _parse_date_components(self, date_part: str) -> tuple[int, int, int]:
        """Parse date components from ISO 8601 duration date part."""
        years = months = days = 0

        year_match = re.search(r"(\d+)Y", date_part)
        if year_match:
            years = int(year_match.group(1))

        month_match = re.search(r"(\d+)M", date_part)
        if month_match:
            months = int(month_match.group(1))

        day_match = re.search(r"(\d+)D", date_part)
        if day_match:
            days = int(day_match.group(1))

        return years, months, days

    def _parse_time_components(self, time_part: str) -> tuple[int, int]:
        """Parse time components from ISO 8601 duration time part."""
        hours = minutes = 0

        hour_match = re.search(r"(\d+)H", time_part)
        if hour_match:
            hours = int(hour_match.group(1))

        minute_match = re.search(r"(\d+)M", time_part)
        if minute_match:
            minutes = int(minute_match.group(1))

        return hours, minutes

    def _parse_iso_duration_to_components(self, duration: str) -> DurationComponents:
        """
        Parse ISO 8601 duration string to component values.

        Args:
            duration: ISO 8601 duration string (e.g., "PT15M", "PT60M")

        Returns:
            DurationComponents with parsed values

        Raises:
            ValueError: When duration format is invalid
        """
        if not duration.startswith("P"):
            msg = f"Invalid ISO 8601 duration format: {duration}"
            raise ValueError(msg)

        if "T" in duration:
            date_part, time_part = duration.split("T", 1)
            date_part = date_part[1:]
        else:
            date_part = duration[1:]
            time_part = ""

        years, months, days = (
            self._parse_date_components(date_part) if date_part else (0, 0, 0)
        )
        hours, minutes = self._parse_time_components(time_part) if time_part else (0, 0)

        if years == months == days == hours == minutes == 0:
            msg = f"Could not parse any duration components from: {duration}"
            raise ValueError(msg)

        return DurationComponents(
            years=years, months=months, days=days, hours=hours, minutes=minutes
        )
