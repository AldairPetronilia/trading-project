from enum import Enum


class CollectionStatus(Enum):
    """Status of data collection attempts"""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    NO_DATA_AVAILABLE = "no_data_available"
