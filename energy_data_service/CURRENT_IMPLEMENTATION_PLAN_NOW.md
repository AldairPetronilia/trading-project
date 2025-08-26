# Physical Flows Integration - Detailed Implementation Plan

## Overview

Integration of ENTSO-E Physical Flows endpoint [12.1.G] into the energy data service. Physical flows use the same `PublicationMarketDocument` structure as prices but with `quantity` data instead of `price_amount`, requiring a hybrid approach that maintains compatibility with existing services.

## Key Challenges & Solutions

### 1. Bidirectional Data Handling
**Challenge**: Physical flows are directional (DE→FR ≠ FR→DE) while existing services expect single `area_code` lookups.

**Solution**: "Virtual area" approach - repositories handle bidirectional logic internally while maintaining identical method signatures for service compatibility.

### 2. Repository Compatibility
**Challenge**: EntsoEDataService and BackfillService expect consistent repository interfaces.

**Solution**: Flow repository implements same methods (`get_latest_for_area_and_type`, etc.) but queries both directions internally.

### 3. Data Type Detection
**Challenge**: Same document structure (PublicationMarketDocument) contains different data types.

**Solution**: Enhanced processor detects data type based on point content (`quantity` vs `price_amount` fields).

## Implementation Plan

### Phase 1: Core Model & Repository

#### New Files
- `energy_data_service/app/models/flow_data.py` - Flow model with directional primary key
- `energy_data_service/app/repositories/energy_flow_repository.py` - Compatible repository with bidirectional logic

#### Model Design
```python
class EnergyFlowPoint(TimestampedModel):
    __tablename__ = "energy_flow_points"

    # Directional composite primary key
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    in_area_code: Mapped[str] = mapped_column(String(50), primary_key=True)  # Source
    out_area_code: Mapped[str] = mapped_column(String(50), primary_key=True)  # Destination
    data_type: Mapped[EnergyDataType] = mapped_column(primary_key=True)
    business_type: Mapped[str] = mapped_column(String(10), primary_key=True)

    # Flow quantity data
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=3), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="MAW")

    # Standard document metadata (matching existing patterns)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="entsoe")
    document_mrid: Mapped[str] = mapped_column(String(100), nullable=False)
    revision_number: Mapped[int | None] = mapped_column()
    document_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_series_mrid: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution: Mapped[str] = mapped_column(String(10), nullable=False)
    curve_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    position: Mapped[int] = mapped_column(nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Optimized indexes for flow queries
    __table_args__ = (
        Index("ix_flow_timestamp_areas", "timestamp", "in_area_code", "out_area_code"),
        Index("ix_flow_type_timestamp", "data_type", "timestamp"),
        Index("ix_flow_document_mrid", "document_mrid"),
        Index("ix_flow_direction", "in_area_code", "out_area_code", "timestamp"),
    )
```

#### Repository Compatibility Pattern
```python
class EnergyFlowRepository(BaseRepository[EnergyFlowPoint]):
    """Repository with compatible method signatures for service integration."""

    async def get_latest_for_area_and_type(
        self, area_code: str, data_type: EnergyDataType
    ) -> EnergyFlowPoint | None:
        """Get latest flow where area is source OR destination (compatibility method)."""
        async with self.database.session_factory() as session:
            stmt = (
                select(EnergyFlowPoint)
                .where(
                    and_(
                        or_(
                            EnergyFlowPoint.in_area_code == area_code,
                            EnergyFlowPoint.out_area_code == area_code,
                        ),
                        EnergyFlowPoint.data_type == data_type,
                    )
                )
                .order_by(desc(EnergyFlowPoint.timestamp))
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_flows_by_direction(
        self,
        in_area_code: str,
        out_area_code: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[EnergyFlowPoint]:
        """Get flows for specific direction (flow-specific method)."""
        # Implementation for directional flow queries
```

### Phase 2: Enhanced Processor

#### Modified Files
- `energy_data_service/app/processors/publication_market_document_processor.py`

#### Data Type Detection Logic
```python
async def _process_time_series(
    self, document, data_type, time_series
) -> list[EnergyPricePoint | EnergyFlowPoint]:  # Enhanced return type
    """Process time series into appropriate model type based on data content."""

    # Determine model type from point data
    points = time_series.period.points
    has_price_data = any(p.price_amount is not None for p in points)
    has_quantity_data = any(p.quantity is not None for p in points)

    if has_quantity_data and not has_price_data:
        # Physical flows: use quantity field, extract both area codes
        return self._create_flow_points(document, data_type, time_series)
    elif has_price_data:
        # Price data: existing logic
        return self._create_price_points(document, data_type, time_series)
    else:
        raise TransformationError("Cannot determine data type: no price or quantity data")

def _create_flow_points(self, document, data_type, time_series) -> list[EnergyFlowPoint]:
    """Create flow points from quantity-based time series."""
    in_area_code = self._extract_area_code(time_series.in_domain_mRID)
    out_area_code = self._extract_area_code(time_series.out_domain_mRID)

    flow_points = []
    for point in time_series.period.points:
        if point.quantity is None:
            continue

        flow_point = EnergyFlowPoint(
            timestamp=self._calculate_point_timestamp(...),
            in_area_code=in_area_code,
            out_area_code=out_area_code,
            data_type=data_type,
            business_type=time_series.businessType.code,
            quantity=Decimal(str(point.quantity)),
            unit=time_series.quantity_measure_unit_name or "MAW",
            # ... rest of standard fields
        )
        flow_points.append(flow_point)
    return flow_points
```

### Phase 3: Configuration & Service Integration

#### Modified Files
- `energy_data_service/app/config/settings.py`
- `energy_data_service/app/services/entsoe_data_service.py`
- `energy_data_service/app/services/backfill_service.py`
- `energy_data_service/app/container.py`

#### Enhanced Configuration
```python
# In EntsoEDataCollectionConfig
class EntsoEDataCollectionConfig(BaseModel):
    target_areas: list[str] = Field(default=["DE-LU", "DE-AT-LU"])

    # NEW: Directional flow pairs
    target_flow_pairs: list[tuple[str, str]] = Field(
        default=[
            ("DE-LU", "DE-AT-LU"),  # Germany to Austria
            ("DE-AT-LU", "CZ"),     # Austria to Czech Republic
            ("DE-LU", "FR"),        # Germany to France
            ("FR", "DE-LU"),        # France to Germany (reverse)
        ],
        description="Directional area code pairs for physical flows (in_domain, out_domain)"
    )
```

#### Enhanced EntsoEDataService
```python
class EntsoEDataService:
    # Flow endpoint handling
    FLOW_ENDPOINTS: ClassVar[frozenset[EndpointNames]] = frozenset({
        EndpointNames.PHYSICAL_FLOWS,
    })

    # Enhanced method selection
    def _get_processor_for_endpoint(self, endpoint: EndpointNames):
        if endpoint in self.PRICE_ENDPOINTS:
            return self._price_processor
        elif endpoint in self.FLOW_ENDPOINTS:
            return self._publication_processor  # Same processor, different logic
        return self._load_processor

    def _get_repository_for_endpoint(self, endpoint: EndpointNames):
        if endpoint in self.PRICE_ENDPOINTS:
            return self._price_repository
        elif endpoint in self.FLOW_ENDPOINTS:
            return self._flow_repository  # NEW
        return self._load_repository

    # Flow-specific collection method
    async def collect_gaps_for_flow_pairs(self) -> dict[str, CollectionResult]:
        """Collect physical flows for all configured directional pairs."""
        results = {}

        for in_area, out_area in self._get_configured_flow_pairs():
            pair_key = f"{in_area}→{out_area}"
            try:
                # Convert to AreaCode objects
                in_domain = AreaCode.from_code(in_area)
                out_domain = AreaCode.from_code(out_area)

                # Detect gaps using "virtual" area approach
                gap_start, gap_end = await self._detect_gap_for_flow_pair(
                    in_domain, out_domain, EndpointNames.PHYSICAL_FLOWS
                )

                # Collect and process
                result = await self.collect_with_chunking(
                    in_domain, EndpointNames.PHYSICAL_FLOWS, gap_start, gap_end,
                    out_domain=out_domain  # Pass out_domain
                )
                results[pair_key] = result

            except Exception as e:
                results[pair_key] = CollectionResult(
                    area=in_domain, data_type=EnergyDataType.PHYSICAL_FLOWS,
                    success=False, error_message=str(e)
                )
        return results
```

### Phase 4: Testing & Integration

#### Test Files (New)
- `energy_data_service/tests/app/models/test_flow_data.py`
- `energy_data_service/tests/app/repositories/test_energy_flow_repository.py`
- `energy_data_service/tests/integration/test_energy_flow_repository_integration.py`

## Complete File Change List

### New Files (6)
1. `energy_data_service/app/models/flow_data.py` - Flow model
2. `energy_data_service/app/repositories/energy_flow_repository.py` - Flow repository
3. `energy_data_service/tests/app/models/test_flow_data.py` - Model tests
4. `energy_data_service/tests/app/repositories/test_energy_flow_repository.py` - Repository tests
5. `energy_data_service/tests/integration/test_energy_flow_repository_integration.py` - Integration tests
6. `energy_data_service/tests/app/processors/test_physical_flows_processor.py` - Processor tests

### Modified Files (6)
1. `energy_data_service/app/models/__init__.py` - Add flow model imports
2. `energy_data_service/app/repositories/__init__.py` - Add flow repository imports
3. `energy_data_service/app/processors/publication_market_document_processor.py` - Add hybrid processing
4. `energy_data_service/app/config/settings.py` - Add flow pairs configuration
5. `energy_data_service/app/services/entsoe_data_service.py` - Add flow service logic
6. `energy_data_service/app/container.py` - Add flow repository injection

## Implementation Priority

### Phase 1: Foundation (Week 1)
- Create `EnergyFlowPoint` model
- Add `EnergyDataType.PHYSICAL_FLOWS` enum value
- Create basic `EnergyFlowRepository` with compatible methods
- Unit tests for model and repository

### Phase 2: Processing Logic (Week 2)
- Enhance `PublicationMarketDocumentProcessor` with data type detection
- Add `_create_flow_points` method
- Integration tests with flow document processing
- Add mapping for physical flows document type

### Phase 3: Service Integration (Week 3)
- Add `target_flow_pairs` configuration
- Update `EntsoEDataService` with flow endpoint handling
- Add flow repository to dependency injection
- Integration tests with full data collection pipeline

### Phase 4: Testing & Validation (Week 4)
- Comprehensive test suite
- Real ENTSO-E API integration tests
- Performance testing with directional queries
- Documentation and deployment

## Architecture Benefits

1. **Backward Compatibility**: All existing method signatures remain unchanged
2. **Service Integration**: Existing gap detection and backfill services work without modification
3. **Type Safety**: Union return types maintain compile-time safety
4. **Performance**: Optimized indexes for directional flow queries
5. **Extensibility**: Pattern supports future quantity-based market document types

## Critical Success Factors

1. **Repository Compatibility**: Flow repository must implement identical interface for service integration
2. **Data Type Detection**: Processor must reliably distinguish between price and quantity data
3. **Bidirectional Handling**: Gap detection must work with "virtual area" approach
4. **Configuration Management**: Flow pairs must be easily configurable and validated
5. **Testing Coverage**: Comprehensive tests including real API integration

This implementation leverages all existing architecture patterns while cleanly extending the system to support directional physical flows data.
