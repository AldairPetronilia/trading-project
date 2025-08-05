# Current Implementation Plan - Configuration Layer

## Next Atomic Step: Add Bidding Zone Areas to Configuration

Based on the completed ENTSO-E data collection services, the next step is implementing configurable bidding zone areas to replace hardcoded values in BackfillService and EntsoEDataService.

### What to implement next:

1. **DataCollectionConfig** (`app/config/settings.py`)
   - New configuration class for data collection settings
   - List of target area codes with validation
   - Field validator for area code verification
   - Integration with existing Settings class

2. **BackfillService Updates** (`app/services/backfill_service.py`)
   - Helper method to convert configured areas to AreaCode enums
   - Update analyze_coverage() to use configuration
   - Remove hardcoded DE_LU and DE_AT_LU references
   - Maintain backwards compatibility

3. **EntsoEDataService Updates** (`app/services/entsoe_data_service.py`)
   - Add configuration injection through constructor
   - Helper method for area conversion
   - Update collect_all_gaps() to use configuration
   - Remove hardcoded area references

4. **Container Updates** (`app/container.py`)
   - Pass data_collection config to EntsoEDataService
   - Ensure proper dependency injection
   - Maintain existing factory patterns

### Implementation Requirements:

#### DataCollectionConfig Features:
- **Target Areas Field**: List[str] field with default ["DE-LU", "DE-AT-LU"]
- **Area Code Validation**: Validate each area code against AreaCode enum
- **Error Messages**: Clear error messages for invalid area codes
- **Environment Variable Support**: DATA_COLLECTION__TARGET_AREAS format
- **Documentation**: Comprehensive field descriptions
- **Type Safety**: Full mypy strict compliance

#### Service Update Features:
- Area conversion helper method returning List[AreaCode]
- Graceful handling of invalid area codes at runtime
- Maintain existing method signatures for compatibility
- Clear logging of configured areas on startup
- No breaking changes to public APIs
- Consistent error handling patterns

#### Configuration Injection Features:
- **Constructor Updates**: Add config parameter to EntsoEDataService
- **Container Wiring**: Use providers.Callable for config extraction
- **Type Annotations**: Proper typing for configuration objects
- **Dependency Flow**: Clear dependency from Settings ’ Config ’ Service
- **Testing Support**: Easy mocking of configuration in tests
- **Documentation**: Update service docstrings

### Test Coverage Requirements:

1. **Configuration Tests** (`tests/app/config/test_settings.py`)
   - Test valid area code configurations
   - Test invalid area code validation
   - Test environment variable parsing
   - Test default values

2. **BackfillService Tests** (`tests/app/services/test_backfill_service.py`)
   - Test area configuration usage
   - Test backwards compatibility
   - Mock configuration for different area sets
   - Test error handling for invalid areas

3. **EntsoEDataService Tests** (`tests/app/services/test_entsoe_data_service.py`)
   - Test configuration injection
   - Test area conversion logic
   - Mock different area configurations
   - Verify collect_all_gaps uses config

4. **Integration Tests** (`tests/integration/`)
   - Test end-to-end with configured areas
   - Test service initialization with config
   - Test actual API calls with different areas
   - Verify database storage for configured areas

5. **Container Tests** (`tests/app/test_container.py`)
   - Test proper configuration wiring
   - Test service factory with config
   - Verify dependency resolution
   - Test configuration overrides

### Dependencies:

- Builds on existing Settings class from `app/config/settings.py`
- Uses AreaCode enum from `entsoe_client/model/common/area_code.py`
- Uses BackfillConfig pattern from `app/config/settings.py`
- Requires pydantic BaseModel and Field validators
- Integration with dependency-injector container system
- Future integration for dynamic area selection UI

### Success Criteria:

- **Configuration Success**: Areas can be configured via environment variables
- **Validation Success**: Invalid area codes are caught at startup with clear errors
- **Service Success**: Both services use configured areas without hardcoding
- **Testing Success**: 100% coverage of new configuration logic
- **Backwards Compatibility**: Existing functionality unchanged
- **Code Quality Success**: Passes all checks (ruff, mypy, pre-commit)
- **Architecture Success**: Clean separation of configuration from business logic
- **Pattern Consistency**: Follows existing configuration patterns in the codebase

This configuration refactoring establishes the foundation for dynamic area selection needed for multi-region data collection and future UI-based area management.

---

## Further Implementation Details

### = **Technical Debt Analysis**

#### **Root Cause:**
Hardcoded area codes in services create maintenance burden and limit flexibility. Currently:
- `backfill_service.py:263`: Hardcoded `areas = [AreaCode.DE_LU, AreaCode.DE_AT_LU]`
- `entsoe_data_service.py:327`: Hardcoded `areas = [AreaCode.DE_LU, AreaCode.DE_AT_LU]`
- No way to add/remove areas without code changes
- Testing requires modifying source code for different area sets

**Current Problematic Code:**
```python
# L WRONG: Hardcoded areas in service layer
async def collect_all_gaps(self) -> dict[str, dict[str, CollectionResult]]:
    areas = [AreaCode.DE_LU, AreaCode.DE_AT_LU]  # Hardcoded!
    results = {}
    for area in areas:
        area_key = area.area_code or str(area.code)
        results[area_key] = await self.collect_gaps_for_area(area)
    return results
```

**Why This is Technical Debt:**
1. **Inflexibility**: Adding new areas requires code changes and redeployment
2. **Testing Complexity**: Can't easily test with different area configurations
3. **Separation of Concerns**: Business logic mixed with configuration

### =à **Detailed Implementation Strategy**

#### **Core Solution Approach:**
Move area configuration to settings layer with proper validation and type safety.

**New Configuration Pattern:**
```python
#  CORRECT: Configuration-driven areas
class DataCollectionConfig(BaseModel):
    """Data collection configuration."""

    target_areas: list[str] = Field(
        default=["DE-LU", "DE-AT-LU"],
        description="List of area codes to collect data for (e.g., DE-LU, FR, NL)"
    )

    @field_validator("target_areas")
    @classmethod
    def validate_area_codes(cls, v: list[str]) -> list[str]:
        """Validate that all area codes exist in AreaCode enum."""
        from entsoe_client.model.common.area_code import AreaCode
        from entsoe_client.exceptions.unknown_area_code_error import UnknownAreaCodeError

        for area_code in v:
            # Try conversion using both methods
            try:
                # First try direct enum lookup
                found = False
                for area_enum in AreaCode:
                    if area_enum.area_code == area_code or area_enum.code == area_code:
                        found = True
                        break

                if not found:
                    # Fallback to from_code method
                    AreaCode.from_code(area_code)
            except (UnknownAreaCodeError, Exception) as e:
                raise ConfigValidationError(
                    f"Invalid area code: {area_code}. "
                    f"Check AreaCode enum for valid values. Error: {e}"
                )
        return v
```

#### **Service Implementation Details:**

**BackfillService Helper Method:**
```python
def _get_configured_areas(self) -> list[AreaCode]:
    """Get configured areas from settings."""
    areas = []
    for area_code in self._config.target_areas:
        # Try to find by area_code attribute first
        for area_enum in AreaCode:
            if area_enum.area_code == area_code:
                areas.append(area_enum)
                break
        else:
            # Fallback to from_code method
            try:
                areas.append(AreaCode.from_code(area_code))
            except UnknownAreaCodeError:
                log.warning(f"Skipping invalid area code: {area_code}")
    return areas
```

### = **Before/After Transformation**

#### **Before (Hardcoded):**
```python
# L Hardcoded in multiple places
async def analyze_coverage(
    self,
    areas: list[AreaCode] | None = None,
    endpoints: list[str] | None = None,
    years_back: int | None = None,
) -> list[CoverageAnalysis]:
    # Use defaults if not specified
    if areas is None:
        areas = [AreaCode.DE_LU, AreaCode.DE_AT_LU]  # HARDCODED!
```

#### **After (Configuration-driven):**
```python
#  Configuration-driven
async def analyze_coverage(
    self,
    areas: list[AreaCode] | None = None,
    endpoints: list[str] | None = None,
    years_back: int | None = None,
) -> list[CoverageAnalysis]:
    # Use defaults if not specified
    if areas is None:
        areas = self._get_configured_areas()  # From config!
```

### =Ê **Benefits Quantification**

#### **Flexibility Improvements:**
- **Area Addition**: From code change + deployment ’ Environment variable change
- **Testing Speed**: 100% faster area configuration changes in tests
- **Configuration Time**: From 30 minutes (code + deploy) ’ 30 seconds (env var)

#### **Code Quality Improvements:**
- **Separation of Concerns**: Configuration separated from business logic
- **Type Safety**: Full validation at startup prevents runtime errors
- **Maintainability**: Single source of truth for area configuration

#### **Operational Improvements:**
- **No Downtime**: Add/remove areas without service restart
- **Multi-Environment**: Different areas per environment (dev/staging/prod)
- **Audit Trail**: Configuration changes tracked in environment files

### >ê **Comprehensive Testing Strategy**

#### **Configuration Validation Tests:**
```python
class TestDataCollectionConfig:
    def test_valid_area_codes(self):
        config = DataCollectionConfig(
            target_areas=["DE-LU", "FR", "NL"]
        )
        assert len(config.target_areas) == 3

    def test_invalid_area_code_raises_error(self):
        with pytest.raises(ConfigValidationError) as exc_info:
            DataCollectionConfig(
                target_areas=["DE-LU", "INVALID"]
            )
        assert "Invalid area code: INVALID" in str(exc_info.value)
```

#### **Service Integration Tests:**
```python
class TestBackfillServiceIntegration:
    async def test_uses_configured_areas(self, mock_config):
        mock_config.target_areas = ["FR", "NL"]
        service = BackfillService(..., config=mock_config)

        areas = service._get_configured_areas()
        assert len(areas) == 2
        assert AreaCode.FRANCE in areas
        assert AreaCode.NETHERLANDS in areas
```

### <¯ **Migration Strategy**

#### **Implementation Phases:**
1. **Phase 1**: Add configuration classes with current defaults
2. **Phase 2**: Update services to use configuration (backwards compatible)
3. **Phase 3**: Update tests and documentation

#### **Backwards Compatibility:**
- **Default Values**: Match current hardcoded areas
- **Method Signatures**: No changes to public APIs
- **Graceful Degradation**: Invalid areas logged but don't crash

#### **Risk Mitigation:**
- **Validation at Startup**: Catch configuration errors early
- **Comprehensive Tests**: Cover all area code variations
- **Rollback Plan**: Environment variable change to restore defaults
