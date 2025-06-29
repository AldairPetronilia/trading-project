from enum import Enum


class DataType(Enum):
    """Standardized data type classifications for energy market data"""

    SPOT_PRICE = "spot_price"
    DAY_AHEAD_PRICE = "day_ahead_price"
    INTRADAY_PRICE = "intraday_price"
    FUTURES_PRICE = "futures_price"

    # Generation data
    ACTUAL_GENERATION = "actual_generation"
    FORECASTED_GENERATION = "forecasted_generation"

    # Demand data
    ACTUAL_LOAD = "actual_load"
    FORECASTED_LOAD = "forecasted_load"

    # Infrastructure
    CROSS_BORDER_FLOW = "cross_border_flow"
    GRID_CONGESTION = "grid_congestion"
    REDISPATCH_VOLUME = "redispatch_volume"

    # Fundamentals
    GAS_STORAGE_LEVEL = "gas_storage_level"
    LNG_TANKER_ARRIVAL = "lng_tanker_arrival"

    # Weather
    WIND_FORECAST = "wind_forecast"
    SOLAR_FORECAST = "solar_forecast"
    TEMPERATURE_FORECAST = "temperature_forecast"
