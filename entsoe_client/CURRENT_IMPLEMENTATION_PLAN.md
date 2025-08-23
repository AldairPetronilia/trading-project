# Current Implementation Plan - Market Domain (Day Ahead Prices [12.1.D])

## Next Atomic Step: Market Domain Implementation for Publication Market Documents

Based on the existing load domain patterns, the next step is implementing market domain support for handling Day Ahead Prices [12.1.D] and other Publication_MarketDocument types used by ENTSO-E.

### What to implement next:

1. **Market Domain Models** (`entsoe_client/src/entsoe_client/model/market/`)
   - `PublicationMarketDocument` for XML response parsing
   - `MarketTimeSeries` for time series data with price information
   - `MarketPeriod` and `MarketPoint` for data structure
   - `MarketTimeInterval` for time period definitions

2. **Market Domain Request Builder** (`entsoe_client/src/entsoe_client/api/market_domain_request_builder.py`)
   - Domain validation for in_Domain and out_Domain (must be equal)
   - Day-ahead prices request building with DocumentType A44
   - BusinessType A62 support for day-ahead prices
   - Date range and bidding zone validation

3. **Client Integration Updates** (`entsoe_client/src/entsoe_client/client/default_entsoe_client.py`)
   - `get_day_ahead_prices()` method implementation
   - XML document type detection for Publication_MarketDocument
   - Integration with existing `_execute_request()` pattern
   - Proper error handling and logging

4. **Common Enum Extensions** (`entsoe_client/src/entsoe_client/model/common/`)
   - Add `DAY_AHEAD_PRICES = ("A62", "Day-ahead prices")` to BusinessType
   - Update XmlDocumentType enum for Publication_MarketDocument detection
   - Ensure DocumentType.PRICE_DOCUMENT (A44) is available

### Implementation Requirements:

#### Market Domain Models Features:
- **XML Parsing**: Full pydantic-xml BaseXmlModel integration with ENTSO-E namespaces
- **Price Data Structure**: Support for price.amount, currency_Unit.name, price_Measure_Unit.name
- **Domain Validation**: Ensure in_Domain equals out_Domain for price requests
- **Time Series Handling**: MarketTimeSeries with businessType A62 and curveType A01
- **Type Safety**: Complete type annotations following mypy strict mode
- **Field Serialization**: Custom serializers/validators for all enum types

#### Market Domain Request Builder Features:
- Domain validation ensuring in_domain equals out_domain for prices
- Date range validation (one year maximum)
- Fluent interface pattern matching LoadDomainRequestBuilder
- DocumentType A44 and BusinessType A62 configuration
- Support for offset parameter for pagination
- Comprehensive error handling with domain-specific exceptions

#### Client Integration Features:
- **Method Implementation**: `get_day_ahead_prices(in_domain, out_domain, period_start, period_end, offset?)`
- **Document Detection**: Update XmlDocumentDetector for Publication_MarketDocument
- **Response Handling**: Parse PublicationMarketDocument alongside existing GlMarketDocument
- **Error Integration**: Chain MarketDomainRequestBuilderError with EntsoEClientError
- **Logging**: Debug logging for price data requests and responses
- **Async Context**: Full async/await support matching existing patterns

### Test Coverage Requirements:

1. **Market Domain Model Tests** (`entsoe_client/tests/entsoe_client/model/market/`)
   - XML parsing tests with real ENTSO-E price response samples
   - Field validation and serialization tests for all models
   - BusinessType A62 and DocumentType A44 integration tests
   - Error scenarios for malformed XML and invalid data

2. **Market Domain Request Builder Tests** (`entsoe_client/tests/entsoe_client/api/test_market_domain_request_builder.py`)
   - Domain validation tests (in_domain != out_domain should fail)
   - Date range validation tests (> 1 year should fail)
   - Fluent interface pattern tests with method chaining
   - EntsoEApiRequest generation validation for day-ahead prices

3. **Client Integration Unit Tests** (`entsoe_client/tests/entsoe_client/client/test_default_entsoe_client.py`)
   - `get_day_ahead_prices()` method success scenarios
   - HTTP error handling and exception chaining tests
   - XML parsing error scenarios and recovery
   - Parameter validation and logging verification

4. **Market Domain Integration Tests** (`entsoe_client/tests/entsoe_client/client/test_default_entsoe_client_market_integration.py`)
   - End-to-end price data retrieval with real XML responses
   - Document type detection integration with XmlDocumentDetector
   - Acknowledgement document handling for price requests
   - Pagination support testing with offset parameter

5. **XML Document Detector Tests** (`entsoe_client/tests/entsoe_client/client/test_xml_document_detector.py`)
   - Publication_MarketDocument detection from XML content
   - Differentiation between GL_MarketDocument and Publication_MarketDocument
   - Error handling for ambiguous or malformed XML

### Dependencies:

- Builds on existing BaseXmlModel from `entsoe_client/model/load/gl_market_document.py`
- Uses EntsoEApiRequest from `entsoe_client/model/common/entsoe_api_request.py`
- Uses AreaCode and domain validation from `entsoe_client/model/common/area_code.py`
- Requires pydantic-xml (already in pyproject.toml)
- Integration with XmlDocumentDetector from `entsoe_client/client/xml_document_detector.py`
- Future integration capability for other Publication_MarketDocument types

### Success Criteria:

- **Primary Success Metric**: Successfully fetch and parse day-ahead prices for any valid area code and date range
- **Testing Success Metric**: 100% coverage for market domain models and request builder, 95% for client integration
- **Integration Success Metric**: Seamless integration with existing client patterns and error handling
- **Performance Success Metric**: XML parsing performance comparable to existing GL_MarketDocument
- **Error Handling Success Metric**: All validation errors provide clear, actionable error messages
- **Code Quality Success Metric**: Passes all checks (ruff, mypy, pre-commit) with zero warnings
- **Architecture Success Metric**: Extensible design supports future Publication_MarketDocument types (capacity prices, etc.)
- **Pattern Consistency Success Metric**: Follows identical patterns to load domain with appropriate adaptations

This market domain implementation establishes the foundation for accessing ENTSO-E price data needed for energy trading applications and future market document types.

---

## Further Implementation Details

### 🔍 **Problem/Technical Debt Analysis Section**

#### **Current Gap in Market Data Access:**
The ENTSO-E client currently only supports load-related data through the GL_MarketDocument structure. However, ENTSO-E provides critical market pricing data through Publication_MarketDocument format, specifically:
- Day-ahead electricity prices (DocumentType A44, BusinessType A62)
- Other market pricing information using the same document structure
- Different XML schema requiring separate parsing models

**Current Missing Capability:**
```python
# ❌ MISSING: No way to fetch price data
client = DefaultEntsoEClient(http_client, base_url)
# This doesn't exist yet:
# prices = await client.get_day_ahead_prices(
#     in_domain=AreaCode.CZECH_REPUBLIC,
#     out_domain=AreaCode.CZECH_REPUBLIC,
#     period_start=datetime(2024, 1, 1),
#     period_end=datetime(2024, 1, 31)
# )
```

**Why This is Technical Debt/Problem:**
1. **Incomplete ENTSO-E Coverage**: Missing critical market pricing data needed for trading applications
2. **Pattern Inconsistency**: Load domain has full support while market pricing has none
3. **Business Impact**: Cannot access day-ahead prices essential for energy trading decisions

### 🛠️ **Detailed Implementation Strategy Section**

#### **Core Solution Approach:**
Create a parallel market domain following the proven load domain patterns, adapted for Publication_MarketDocument structure and price data requirements.

**New Market Domain Pattern:**
```python
# ✅ CORRECT: Complete market domain implementation
@dataclass
class MarketDomainRequestBuilder:
    in_domain: AreaCode
    out_domain: AreaCode
    period_start: datetime
    period_end: datetime

    def build_day_ahead_prices(self) -> EntsoEApiRequest:
        return EntsoEApiRequest(
            document_type=DocumentType.PRICE_DOCUMENT,  # A44
            business_type=BusinessType.DAY_AHEAD_PRICES,  # A62
            in_domain=self.in_domain,
            out_domain=self.out_domain,
            period_start=self.period_start,
            period_end=self.period_end,
        )
```

#### **Detailed Component Implementation:**

**PublicationMarketDocument Implementation:**
```python
class PublicationMarketDocument(BaseXmlModel, tag="Publication_MarketDocument"):
    mRID: str = element(tag="mRID")
    type: DocumentType = element(tag="type")
    sender_market_participant_mRID: MarketParticipantMRID = element(tag="sender_MarketParticipant.mRID")
    receiver_market_participant_mRID: MarketParticipantMRID = element(tag="receiver_MarketParticipant.mRID")
    created_date_time: datetime = element(tag="createdDateTime")
    period_time_interval: MarketTimeInterval = element(tag="period.timeInterval")
    time_series: list[MarketTimeSeries]
```

**MarketTimeSeries Implementation:**
```python
class MarketTimeSeries(BaseXmlModel, tag="TimeSeries"):
    mRID: str = element(tag="mRID")
    business_type: BusinessType = element(tag="businessType")  # A62
    in_domain_mRID: DomainMRID = element(tag="in_Domain.mRID")
    out_domain_mRID: DomainMRID = element(tag="out_Domain.mRID")
    currency_unit_name: str = element(tag="currency_Unit.name")  # EUR
    price_measure_unit_name: str = element(tag="price_Measure_Unit.name")  # MWH
    curve_type: CurveType = element(tag="curveType")  # A01
    period: MarketPeriod
```

### 🔄 **Before/After Transformation Section**

#### **Before (Missing Market Domain):**
```python
# ❌ Current limitation - only load data available
async def get_energy_data(area: AreaCode, start: datetime, end: datetime):
    # Can only get load data
    load_data = await client.get_actual_total_load(area, start, end)

    # No pricing information available
    # Cannot make informed trading decisions
    # Missing critical market data component
    return {"load": load_data, "prices": None}  # Incomplete data
```

#### **After (Complete Market Data Access):**
```python
# ✅ Complete energy market data access
async def get_energy_data(area: AreaCode, start: datetime, end: datetime):
    # Get both load and pricing data
    load_data = await client.get_actual_total_load(area, start, end)
    price_data = await client.get_day_ahead_prices(
        in_domain=area, out_domain=area,
        period_start=start, period_end=end
    )

    # Complete market picture for trading decisions
    return {"load": load_data, "prices": price_data}
```

### 📊 **Benefits Quantification Section**

#### **Market Data Coverage Improvements:**
- **Data Completeness**: 100% increase in ENTSO-E API coverage for market pricing
- **Trading Capability**: Enables price-aware energy trading strategies
- **API Utilization**: Doubles the useful ENTSO-E endpoints accessible through client

#### **Code Quality Improvements:**
- **Pattern Consistency**: Market domain follows identical structure to load domain
- **Type Safety**: Full mypy strict compliance with comprehensive type annotations
- **Error Handling**: Domain-specific validation with clear error messages

#### **Architectural Improvements:**
- **Extensibility**: Foundation supports future Publication_MarketDocument types
- **Separation of Concerns**: Clean domain separation between load and market data
- **Testing Coverage**: Complete test suite following established patterns

### 🧪 **Comprehensive Testing Strategy Section**

#### **Unit Tests Details:**
```python
class TestMarketDomainRequestBuilder:
    async def test_build_day_ahead_prices_success(self):
        builder = MarketDomainRequestBuilder(
            in_domain=AreaCode.CZECH_REPUBLIC,
            out_domain=AreaCode.CZECH_REPUBLIC,
            period_start=datetime(2024, 1, 1, tzinfo=UTC),
            period_end=datetime(2024, 1, 31, tzinfo=UTC),
        )

        request = builder.build_day_ahead_prices()
        assert request.document_type == DocumentType.PRICE_DOCUMENT
        assert request.business_type == BusinessType.DAY_AHEAD_PRICES

    async def test_domain_validation_failure(self):
        with pytest.raises(MarketDomainRequestBuilderError):
            MarketDomainRequestBuilder(
                in_domain=AreaCode.CZECH_REPUBLIC,
                out_domain=AreaCode.FINLAND,  # Different domains not allowed
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 31, tzinfo=UTC),
            )
```

#### **Integration Tests Details:**
```python
class TestDefaultEntsoEClientMarketIntegration:
    async def test_get_day_ahead_prices_end_to_end(self):
        # Test with real Publication_MarketDocument XML response
        mock_xml = """<Publication_MarketDocument>...</Publication_MarketDocument>"""

        with patch.object(http_client, 'get', return_value=mock_xml):
            result = await client.get_day_ahead_prices(
                in_domain=AreaCode.CZECH_REPUBLIC,
                out_domain=AreaCode.CZECH_REPUBLIC,
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 31, tzinfo=UTC)
            )

        assert isinstance(result, PublicationMarketDocument)
        assert len(result.time_series) > 0
```

#### **Performance/Load Tests:**
- **XML Parsing Performance**: Publication_MarketDocument parsing should match GL_MarketDocument speed
- **Memory Usage**: Time series data handling should be efficient for large date ranges

### 🎯 **Migration/Rollout Strategy Section**

#### **Implementation Phases:**
1. **Phase 1**: Core models (PublicationMarketDocument, MarketTimeSeries, MarketPeriod, MarketPoint)
2. **Phase 2**: Request builder and validation (MarketDomainRequestBuilder, enum additions)
3. **Phase 3**: Client integration and document detection (get_day_ahead_prices, XmlDocumentDetector updates)

#### **Backwards Compatibility:**
- **No Breaking Changes**: All additions are net-new functionality
- **Existing API Preserved**: Load domain methods remain unchanged
- **Dependency Stability**: No changes to existing dependencies

#### **Risk Mitigation:**
- **Incremental Testing**: Each phase has comprehensive test coverage before proceeding
- **Pattern Replication**: Following proven load domain patterns reduces implementation risk
- **XML Schema Validation**: Thorough testing with real ENTSO-E response samples
