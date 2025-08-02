"""
Alert system enumerations for type-safe alert management.

This module provides all enumeration types used throughout the alert system,
ensuring consistent categorization and status tracking across alert rules,
alerts, and delivery mechanisms. All enums extend str to maintain SQLAlchemy
compatibility and provide clear string representations.

Key Features:
- Alert type categorization for different monitoring scenarios
- Severity levels for alert prioritization and escalation
- Delivery status tracking for reliable notification management
- Multi-channel delivery support for flexible alert routing
- Rule status management for operational control
"""

from enum import Enum


class AlertType(str, Enum):
    """
    Enumeration of alert types for categorizing different monitoring scenarios.

    This enum defines the various types of alerts that can be triggered within
    the energy data system, allowing for proper categorization and handling
    of different monitoring conditions.

    Values:
        PRICE_THRESHOLD: Alerts triggered when energy prices exceed defined thresholds
        DATA_QUALITY: Alerts for data integrity issues, missing data, or validation failures
        SYSTEM_HEALTH: Alerts for system performance, availability, and operational issues
        COLLECTION_FAILURE: Alerts for data collection failures and API connectivity issues
        PERFORMANCE: Alerts for performance-related issues, such as high latency or low throughput
    """

    PRICE_THRESHOLD = "price_threshold"
    DATA_QUALITY = "data_quality"
    SYSTEM_HEALTH = "system_health"
    COLLECTION_FAILURE = "collection_failure"
    PERFORMANCE = "performance"


class AlertSeverity(str, Enum):
    """
    Enumeration of alert severity levels for prioritization and escalation.

    This enum defines severity levels that determine the urgency and priority
    of alerts, enabling proper escalation and response handling based on
    the impact and criticality of the monitored condition.

    Values:
        LOW: Informational alerts that require awareness but no immediate action
        MEDIUM: Moderate priority alerts that should be addressed during business hours
        HIGH: High priority alerts requiring prompt attention and investigation
        CRITICAL: Critical alerts requiring immediate action and escalation
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertDeliveryStatus(str, Enum):
    """
    Enumeration of alert delivery status for tracking notification progress.

    This enum tracks the delivery status of alerts through various notification
    channels, enabling reliable delivery monitoring and retry mechanisms for
    failed notifications.

    Values:
        PENDING: Alert is queued for delivery but not yet sent
        DELIVERED: Alert has been successfully delivered to the target channel
        FAILED: Alert delivery failed and may require manual intervention
        RETRYING: Alert delivery is being retried after an initial failure
    """

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class AlertDeliveryChannel(str, Enum):
    """
    Enumeration of available alert delivery channels for flexible notification routing.

    This enum defines the supported delivery mechanisms for alerts, allowing
    for flexible notification routing based on alert type, severity, and
    recipient preferences.

    Values:
        EMAIL: Email-based alert delivery for detailed notifications
        WEBHOOK: HTTP webhook delivery for system-to-system integration
    """

    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertRuleStatus(str, Enum):
    """
    Enumeration of alert rule operational status for lifecycle management.

    This enum defines the operational status of alert rules, enabling
    dynamic control over rule evaluation and alert generation without
    requiring rule deletion.

    Values:
        ACTIVE: Rule is active and being evaluated for alert conditions
        INACTIVE: Rule is inactive and will not generate alerts
        PAUSED: Rule is temporarily paused but can be reactivated
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
