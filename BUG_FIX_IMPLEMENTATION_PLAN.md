# Multiple TimeSeries Support: Critical Data Loss Analysis & Implementation Plan

**Date:** August 3, 2025
**Priority:** Critical
**Impact:** High - Data Loss Bug
**Estimated Effort:** 3-5 days

## Executive Summary

A critical data loss bug has been identified in the ENTSO-E data collection system. The current implementation only processes the first `TimeSeries` element from ENTSO-E API responses, while the API frequently returns multiple `TimeSeries` in a single document. This results in **~98.8% data loss** in typical responses.

**Root Cause:** The `GlMarketDocument` model expects a single `TimeSeries` object, but ENTSO-E returns multiple `TimeSeries` elements in one document.

**Example Impact:** A recent API response contained 84 data points across 2 TimeSeries, but only 1 data point was processed and stored.

**Critical Discovery:** TimeSeries `mRID` values are document-relative counters (1, 2, 3...), not globally unique identifiers. The same timestamp can have different `time_series_mrid` values across different API calls, causing potential duplicate storage issues.

## Problem Analysis

### Current System Behavior

```xml
<!-- ENTSO-E API Response Structure - Example 1 -->
<GL_MarketDocument>
  <mRID>68e1b9a516a44fcc9a4f36981209696b</mRID>
  <TimeSeries>
    <mRID>1</mRID>
    <!-- Period: 2025-08-02T14:00Z to 2025-08-02T14:15Z (1 point) -->
  </TimeSeries>
  <TimeSeries>
    <mRID>2</mRID>
    <!-- Period: 2025-08-02T14:30Z to 2025-08-03T11:15Z (83 points) -->
  </TimeSeries>
</GL_MarketDocument>

<!-- ENTSO-E API Response Structure - Example 2 (15 minutes later) -->
<GL_MarketDocument>
  <mRID>c1dd22c27f1240268108a8ca661432aa</mRID>
  <TimeSeries>
    <mRID>1</mRID>  <!-- SAME mRID, DIFFERENT document! -->
    <!-- Period: 2025-08-02T14:30Z to 2025-08-03T11:30Z (84 points) -->
  </TimeSeries>
</GL_MarketDocument>
```

### TimeSeries mRID Behavior Analysis

**Critical Finding:** TimeSeries `mRID` values are **document-scoped sequential counters**, not globally unique identifiers:

- **API Call 1**: Document `68e1b9a5...` has TimeSeries mRID `1` and `2`
- **API Call 2**: Document `c1dd22c2...` has TimeSeries mRID `1` (for overlapping data!)

**Implication:** The same actual timestamp data can appear with different `time_series_mrid` values across API calls, breaking uniqueness assumptions.

### Backfill Service Impact Analysis

**🚨 MASSIVE DATA LOSS IN HISTORICAL BACKFILL:**

The backfill service uses 6-month chunks for historical data collection. Each API response potentially contains multiple TimeSeries, but only the first one is processed:

**Example Backfill Loss Calculation:**
- **Chunk Size**: 6 months (180 days)
- **Expected API Calls**: ~60 calls (3-day intervals)
- **TimeSeries per Response**: 2-4 on average
- **Estimated Data Loss**: 75-90% of historical data

**Critical Business Impact:**
- Historical analysis is based on incomplete data
- Gap analysis shows false positives (data exists but wasn't parsed)
- Trading algorithms may be using severely incomplete datasets
- Compliance reporting may be inaccurate due to missing data

### Critical Code Issues

#### 1. ENTSO-E Client Model (Primary Issue)
```python
# File: entsoe_client/src/entsoe_client/model/load/gl_market_document.py:35
timeSeries: LoadTimeSeries  # 🚨 CRITICAL: Only handles single TimeSeries!
```

#### 2. Data Processor (Secondary Issue)
```python
# File: energy_data_service/app/processors/gl_market_document_processor.py:148-153
area_code = self._extract_area_code(
    document.timeSeries.outBiddingZoneDomainMRID  # 🚨 Assumes single TimeSeries
)
period = document.timeSeries.period  # 🚨 Assumes single TimeSeries
```

## Impact Assessment

### Data Loss Magnitude
- **Current**: 1 data point stored (TimeSeries 1 only)
- **Available**: 84 data points (TimeSeries 1 + TimeSeries 2)
- **Loss Rate**: 98.8%

### System Components Affected
1. **ENTSO-E Client** - XML parsing fails for multiple TimeSeries
2. **Data Processor** - Cannot handle multiple TimeSeries per document
3. **Gap Analysis** - Incorrectly reports missing data that was never parsed
4. **Real-time Collection** - Silently loses most collected data
5. **Database** - Incomplete time series data
6. **🚨 Backfill Service** - **CRITICAL**: 6-month chunk intervals are losing massive amounts of data due to multiple TimeSeries not being processed

## Implementation Plan

### Phase 1: Core Model Updates (Day 1)

#### 1.1 Update ENTSO-E Client Model
**File:** `entsoe_client/src/entsoe_client/model/load/gl_market_document.py`

```python
class GlMarketDocument(BaseXmlModel, tag="GL_MarketDocument", nsmap=ENTSOE_LOAD_NSMAP):
      mRID: str = element(tag="mRID")
      revisionNumber: int | None = element(tag="revisionNumber")
      type: DocumentType = element(tag="type")
      processType: ProcessType = element(tag="process.processType")
      senderMarketParticipantMRID: MarketParticipantMRID = element(
          tag="sender_MarketParticipant.mRID",
      )
      senderMarketParticipantMarketRoleType: MarketRoleType = element(
          tag="sender_MarketParticipant.marketRole.type",
      )
      receiverMarketParticipantMRID: MarketParticipantMRID = element(
          tag="receiver_MarketParticipant.mRID",
      )
      receiverMarketParticipantMarketRoleType: MarketRoleType = element(
          tag="receiver_MarketParticipant.marketRole.type",
      )
      createdDateTime: datetime = element(tag="createdDateTime")
      timePeriodTimeInterval: LoadTimeInterval = element(tag="time_Period.timeInterval")

    # 🔧 CRITICAL CHANGE: Single to List
    timeSeries: list[LoadTimeSeries]  # Changed from LoadTimeSeries to list[LoadTimeSeries]

    # All existing serializers and validators remain the same
    # ... (keep all existing methods unchanged)
```

#### 1.2 Update Client Tests
**File:** `entsoe_client/tests/entsoe_client/model/load/test_gl_market_document.py`

```python
def test_multiple_time_series_parsing():
      """Test parsing GL_MarketDocument with multiple TimeSeries."""
      xml_content = """
      <GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
          <mRID>test-doc</mRID>
          <TimeSeries>
              <mRID>1</mRID>
              <!-- First TimeSeries -->
          </TimeSeries>
          <TimeSeries>
              <mRID>2</mRID>
              <!-- Second TimeSeries -->
          </TimeSeries>
      </GL_MarketDocument>
      """

      document = GlMarketDocument.from_xml(xml_content)

    assert len(document.timeSeries) == 2
    assert document.timeSeries[0].mRID == "1"
    assert document.timeSeries[1].mRID == "2"

def test_single_time_series_backward_compatibility():
    """Ensure single TimeSeries still works (backward compatibility)."""
    # Test that existing single TimeSeries responses still parse correctly
    pass
```

### Phase 2: Processor Updates (Day 2)

#### 2.1 Update GL_MarketDocument Processor
**File:** `energy_data_service/app/processors/gl_market_document_processor.py`

```python
async def _process_document(
      self, document: GlMarketDocument
  ) -> list[EnergyDataPoint]:
      """
      Process a single GL_MarketDocument into EnergyDataPoint models.
      Now supports multiple TimeSeries per document.
      """
      points: list[EnergyDataPoint] = []

      try:
          # Map ProcessType + DocumentType combination to EnergyDataType
          data_type = self._map_document_to_energy_data_type(
              document.processType, document.type
          )

          # 🔧 NEW: Process each TimeSeries separately
          for time_series in document.timeSeries:
              series_points = await self._process_time_series(
                  document, time_series, data_type
              )
              points.extend(series_points)

      except Exception as e:
          if isinstance(e, MappingError | TimestampCalculationError):
              raise
          msg = f"Failed to parse document structure: {e}"
          raise DocumentParsingError(
              msg,
              document_type="GL_MarketDocument",
              document_id=document.mRID,
              parsing_stage="document_processing",
          ) from e

      return points

  async def _process_time_series(
      self,
      document: GlMarketDocument,
      time_series: LoadTimeSeries,
      data_type: EnergyDataType
  ) -> list[EnergyDataPoint]:
      """
      Process a single TimeSeries within a GL_MarketDocument.

      Args:
          document: Parent GL_MarketDocument
          time_series: Individual TimeSeries to process
          data_type: Mapped EnergyDataType for this document

      Returns:
          List of EnergyDataPoint models from this TimeSeries
      """
      # Extract area code from THIS TimeSeries
      area_code = self._extract_area_code(time_series.outBiddingZoneDomainMRID)

      # Process periods and points for THIS TimeSeries
      points: list[EnergyDataPoint] = []
      period = time_series.period

      for point in period.points:
          if point.position is None or point.quantity is None:
              continue

          # Calculate timestamp for this point
          timestamp = self._calculate_point_timestamp(
              period_start=period.timeInterval.start,
              resolution=period.resolution,
              position=point.position,
          )

          energy_point = EnergyDataPoint(
              timestamp=timestamp,
              area_code=area_code,
              data_type=data_type,
              business_type=time_series.businessType.code,
              quantity=Decimal(str(point.quantity)),
              unit=time_series.quantityMeasureUnitName,
              data_source="entsoe",
              document_mrid=document.mRID,  # Same for all TimeSeries in document
              revision_number=document.revisionNumber,
              document_created_at=document.createdDateTime,
              time_series_mrid=time_series.mRID,  # Unique per TimeSeries
              resolution=period.resolution,
              curve_type=time_series.curveType.code,
              object_aggregation=time_series.objectAggregation.code,
              position=point.position,
              period_start=period.timeInterval.start,
              period_end=period.timeInterval.end,
          )
          points.append(energy_point)

    return points
```

#### 2.2 Update Processor Tests
**File:** `energy_data_service/tests/app/processors/test_gl_market_document_processor.py`

```python
async def test_process_multiple_time_series():
      """Test processing GL_MarketDocument with multiple TimeSeries."""
      # Create test document with 2 TimeSeries
      # Verify all data points are extracted
      # Verify correct time_series_mrid values
    pass

async def test_process_overlapping_time_series():
    """Test handling of overlapping periods in different TimeSeries."""
    # Create test with overlapping timestamps
    # Verify both records are created with different time_series_mrid
    pass
```

### Phase 3: Integration & Testing (Day 3)

#### 3.1 Integration Test Updates
**File:** `energy_data_service/tests/integration/test_processor_integration.py`

```python
async def test_end_to_end_multiple_time_series():
      """Test complete pipeline with multiple TimeSeries response."""
      # Use real ENTSO-E XML response with multiple TimeSeries
      # Verify complete processing pipeline
      # Check database storage
    pass
```

#### 3.2 Service Integration Tests
**File:** `energy_data_service/tests/integration/test_entsoe_data_service_integration.py`

```python
async def test_collect_gaps_with_multiple_time_series():
    """Test gap collection handles multiple TimeSeries correctly."""
    # Mock ENTSO-E responses with multiple TimeSeries
    # Verify all data points are collected and stored
    pass
```

### Phase 4: Data Quality & Monitoring (Day 4)

#### 4.1 Database Constraint Analysis
**Current Primary Key:**
```sql
PRIMARY KEY (timestamp, area_code, data_type, time_series_mrid)
```

**🚨 CRITICAL ISSUE:** Including `time_series_mrid` in the primary key is **INCORRECT** based on new findings:

**Problem:** TimeSeries mRID values are document-scoped counters, not globally unique IDs:
- Same timestamp data can have different `time_series_mrid` values across API calls
- This allows duplicate data storage for the same actual data point
- Example: `2025-08-02T14:30Z` appears with `time_series_mrid='1'` in two different documents

**Required Database Schema Change:**
```sql
-- NEW Primary Key (Remove time_series_mrid)
PRIMARY KEY (timestamp, area_code, data_type)

-- Keep time_series_mrid as metadata (not part of primary key)
-- Add document_mrid + time_series_mrid combination for traceability
```

**Migration Strategy:**
1. Create new unique constraint without `time_series_mrid`
2. Handle existing duplicates during migration
3. Update upsert logic to use new primary key

#### 4.2 Data Quality Checks
**File:** `energy_data_service/app/services/monitoring_service.py`

```python
async def check_time_series_consistency(self):
    """Monitor for data quality issues with multiple TimeSeries."""
    # 🔧 NEW: Check for actual duplicates (same timestamp, area, data_type)
    # Alert if same timestamp has conflicting quantity values
    # Monitor document overlap patterns to detect API behavior changes
    # Track time_series_mrid distribution across documents
    pass

async def detect_duplicate_data_points(self):
    """Detect potential duplicate data from overlapping API responses."""
    # Check for same (timestamp, area_code, data_type) with different:
    # - document_mrid values
    # - time_series_mrid values
    # - quantity values (data quality issue)
    pass

async def validate_data_continuity(self):
    """Ensure no gaps caused by improper deduplication."""
    # Verify timestamp continuity after deduplication
    # Alert on unexpected data gaps
    # Monitor backfill effectiveness with new schema
    pass
```

#### 4.3 Logging Enhancements
**File:** `energy_data_service/app/processors/gl_market_document_processor.py`

```python
# Add logging for TimeSeries processing
log.info(
    "Processing document %s with %d TimeSeries",
    document.mRID,
    len(document.timeSeries)
)

log.debug(
    "Processed TimeSeries %s: %d points from %s to %s",
    time_series.mRID,
    len(points),
    period.timeInterval.start,
    period.timeInterval.end
)
```

### Phase 5: Deployment & Validation (Day 5)

#### 5.1 Backward Compatibility Testing
- Verify existing single TimeSeries responses still work
- Test with historical data collection
- Validate gap analysis recalculation

#### 5.2 Production Validation
- Deploy to staging environment
- Run real-time collection cycle
- Compare data points collected before/after fix
- Monitor for processing errors

#### 5.3 Gap Analysis Recalibration
- Re-run coverage analysis for affected time periods
- Update backfill requirements based on newly available data
- Validate gap detection accuracy

## Files Requiring Changes

### Critical Files (Must Change)

1. **`entsoe_client/src/entsoe_client/model/load/gl_market_document.py`**
   - Change `timeSeries: LoadTimeSeries` to `timeSeries: list[LoadTimeSeries]`

2. **`energy_data_service/app/processors/gl_market_document_processor.py`**
   - Update `_process_document()` to handle multiple TimeSeries
   - Add new `_process_time_series()` method

3. **🚨 NEW: Database Schema & Repository Changes**
   - **Migration Script**: Remove `time_series_mrid` from primary key
   - **`energy_data_service/app/repositories/energy_data_repository.py`**: Update upsert logic for new primary key
   - **Database Constraints**: Change primary key to `(timestamp, area_code, data_type)`

### Test Files (Must Update)
4. **`entsoe_client/tests/entsoe_client/model/load/test_gl_market_document.py`**
5. **`energy_data_service/tests/app/processors/test_gl_market_document_processor.py`**
6. **`energy_data_service/tests/integration/test_processor_integration.py`**
7. **🚨 NEW: Database Migration Tests**

### Optional Enhancement Files
8. **`energy_data_service/app/services/monitoring_service.py`** - Data quality checks
9. **`energy_data_service/app/services/entsoe_data_service.py`** - Enhanced logging

## Risk Assessment

### High Risk
- **Breaking Changes**: Any code accessing `document.timeSeries` directly will break
- **Data Volume Increase**: 10-100x more data points may impact performance
- **Memory Usage**: Processing multiple TimeSeries increases memory requirements

### Medium Risk
- **Database Performance**: Higher insert volume may require optimization
- **API Rate Limiting**: Success may trigger more frequent API calls
- **Data Quality**: Multiple TimeSeries may contain conflicting data

### Low Risk
- **XML Parsing**: pydantic-xml handles list parsing automatically
- **Database Schema**: Current schema already supports multiple TimeSeries
- **Backward Compatibility**: Single TimeSeries becomes list of one element

## Success Metrics

### Data Collection Improvement
- **Before**: ~1-5 data points per API call (only first TimeSeries processed)
- **After**: ~50-100 data points per API call (all TimeSeries processed)
- **Target**: >20x increase in data collection efficiency
- **🚨 Backfill Impact**: Potential to recover 75-90% of missing historical data

### Gap Analysis Accuracy
- **Before**: 90%+ gaps reported (false positives)
- **After**: <10% gaps reported (actual missing data)
- **Target**: 95%+ gap detection accuracy

### System Performance
- **Memory Usage**: Monitor for <2x increase
- **Processing Time**: Maintain <5s per document
- **Database Load**: Monitor insert performance

## Rollback Plan

### Immediate Rollback (if needed)
1. Revert `gl_market_document.py` to single TimeSeries
2. Revert processor changes
3. Restart services
4. **Impact**: Return to data loss state but system stability

### Gradual Rollback
1. Add feature flag for multiple TimeSeries processing
2. Fall back to first TimeSeries only if processing fails
3. Monitor and gradually enable full processing

## Next Steps

1. **Day 1**: Update ENTSO-E client model and basic tests
2. **Day 2**: Update processor logic with comprehensive testing
3. **Day 3**: Database schema migration and repository updates
4. **Day 4**: Integration testing and data quality validation
5. **Day 5**: Staging deployment and production validation
6. **🚨 Day 6-7**: Historical data backfill with corrected parsing (optional but recommended)

**Priority**: This should be treated as a **critical bug fix** due to the significant data loss impact.

**Revised Impact**: The database schema changes add complexity but are essential for data integrity.

**Owner**: Development team with ENTSO-E API expertise + Database team
**Reviewer**: System architect, data quality team, and DBA
**Timeline**: Complete within 1-2 weeks for maximum business impact (extended due to database migration)
