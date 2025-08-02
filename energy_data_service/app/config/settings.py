from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    SecretStr,
    ValidationInfo,
    computed_field,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions.config_validation_error import ConfigValidationError

# Constants
MIN_PORT = 1
MAX_PORT = 65535
MIN_API_TOKEN_LENGTH = 10
REDACTED_VALUE = "***REDACTED***"

# Time validation constants
MIN_HOUR = 0
MAX_HOUR = 23
MIN_MINUTE = 0
MAX_MINUTE = 59


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    host: str = Field(default="localhost", description="The database host address")
    port: int = Field(default=5432, description="The database port number")
    user: str = Field(default="energy_user", description="The database username")
    password: SecretStr = Field(
        default=SecretStr("dummy"),
        description="The database password",
    )
    name: str = Field(
        default="energy_data_service",
        description="The name of the database",
    )

    @computed_field  # type: ignore[misc]
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.name}"

    @field_validator("port")  # type: ignore[misc]
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not MIN_PORT <= v <= MAX_PORT:
            raise ConfigValidationError.invalid_database_port()
        return v


class HttpConfig(BaseModel):
    """HTTP configuration for FastAPI application."""

    connection_timeout: timedelta = Field(
        default=timedelta(seconds=30),
        description="HTTP connection timeout",
    )
    read_timeout: timedelta = Field(
        default=timedelta(seconds=60),
        description="HTTP read timeout",
    )
    write_timeout: timedelta = Field(
        default=timedelta(seconds=60),
        description="HTTP write timeout",
    )


class EntsoEClientConfig(BaseModel):
    """ENTSO-E client configuration settings."""

    api_token: SecretStr = Field(description="ENTSO-E API token for authentication")
    base_url: HttpUrl = Field(
        default=HttpUrl("https://web-api.tp.entsoe.eu/api"),
        description="ENTSO-E API base URL",
    )
    user_agent: str = Field(
        default="energy-data-service/1.0.0",
        description="User-Agent header for API requests",
    )

    @field_validator("api_token")  # type: ignore[misc]
    @classmethod
    def validate_api_token(cls, v: SecretStr) -> SecretStr:
        token = v.get_secret_value()
        if len(token) < MIN_API_TOKEN_LENGTH:
            raise ConfigValidationError.api_token_too_short()
        return v


class LoggingConfig(BaseModel):
    """Logging configuration settings."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format",
    )
    enable_request_logging: bool = Field(
        default=False,
        description="Log HTTP requests and responses",
    )


class BackfillConfig(BaseModel):
    """Historical data backfill configuration."""

    historical_years: int = Field(
        default=2,
        description="Years of historical data to backfill",
        ge=1,
        le=10,
    )
    chunk_months: int = Field(
        default=6,
        description="Months per backfill chunk (6-12 optimal for ENTSO-E)",
        ge=1,
        le=12,
    )
    rate_limit_delay: float = Field(
        default=2.0,
        description="Rate limiting delay for backfill (slower than real-time)",
        ge=0.5,
        le=10.0,
    )
    max_concurrent_areas: int = Field(
        default=1,
        description="Max concurrent area backfills",
        ge=1,
        le=5,
    )
    enable_progress_persistence: bool = Field(
        default=True,
        description="Save backfill progress to database",
    )
    resume_incomplete_backfills: bool = Field(
        default=True,
        description="Resume interrupted backfills on startup",
    )


class SchedulerConfig(BaseModel):
    """Scheduler configuration for automated data collection and analysis."""

    enabled: bool = Field(
        default=True,
        description="Enable the scheduler service",
    )

    # Real-time data collection
    real_time_collection_enabled: bool = Field(
        default=True,
        description="Enable real-time data collection jobs",
    )
    real_time_collection_interval_minutes: int = Field(
        default=30,
        description="Interval for real-time data collection in minutes",
        ge=5,
        le=120,
    )

    # Gap analysis
    gap_analysis_enabled: bool = Field(
        default=True,
        description="Enable gap analysis jobs",
    )
    gap_analysis_interval_hours: int = Field(
        default=4,
        description="Interval for gap analysis in hours",
        ge=1,
        le=24,
    )

    # Daily backfill analysis
    daily_backfill_analysis_enabled: bool = Field(
        default=True,
        description="Enable daily backfill analysis jobs",
    )
    daily_backfill_analysis_hour: int = Field(
        default=2,
        description="Hour of day to run daily backfill analysis (0-23)",
        ge=0,
        le=23,
    )
    daily_backfill_analysis_minute: int = Field(
        default=0,
        description="Minute of hour to run daily backfill analysis (0-59)",
        ge=0,
        le=59,
    )

    # Job persistence and recovery
    use_persistent_job_store: bool = Field(
        default=True,
        description="Use database for job persistence",
    )
    job_defaults_max_instances: int = Field(
        default=3,
        description="Maximum instances of any job that can run simultaneously",
        ge=1,
        le=10,
    )
    job_defaults_coalesce: bool = Field(
        default=True,
        description="Coalesce missed job executions",
    )
    job_defaults_misfire_grace_time_seconds: int = Field(
        default=300,
        description="Grace time for missed job executions in seconds",
        ge=60,
        le=3600,
    )

    # Retry and failure handling
    max_retry_attempts: int = Field(
        default=3,
        description="Maximum retry attempts for failed jobs",
        ge=1,
        le=10,
    )
    retry_backoff_base_seconds: float = Field(
        default=2.0,
        description="Base seconds for exponential backoff retry",
        ge=1.0,
        le=60.0,
    )
    retry_backoff_max_seconds: float = Field(
        default=300.0,
        description="Maximum seconds for exponential backoff retry",
        ge=60.0,
        le=3600.0,
    )

    # Health monitoring
    job_health_check_interval_minutes: int = Field(
        default=15,
        description="Interval for job health checks in minutes",
        ge=5,
        le=60,
    )
    failed_job_notification_threshold: int = Field(
        default=3,
        description="Number of consecutive failures before notification",
        ge=1,
        le=10,
    )

    # Performance settings
    thread_pool_max_workers: int = Field(
        default=5,
        description="Maximum number of threads for job execution",
        ge=1,
        le=20,
    )

    @field_validator("daily_backfill_analysis_hour")  # type: ignore[misc]
    @classmethod
    def validate_hour_range(cls, v: int) -> int:
        if not MIN_HOUR <= v <= MAX_HOUR:
            msg = f"Hour must be between {MIN_HOUR} and {MAX_HOUR}, got {v}"
            raise ConfigValidationError(msg)
        return v

    @field_validator("daily_backfill_analysis_minute")  # type: ignore[misc]
    @classmethod
    def validate_minute_range(cls, v: int) -> int:
        if not MIN_MINUTE <= v <= MAX_MINUTE:
            msg = f"Minute must be between {MIN_MINUTE} and {MAX_MINUTE}, got {v}"
            raise ConfigValidationError(msg)
        return v

    @field_validator("retry_backoff_max_seconds")  # type: ignore[misc]
    @classmethod
    def validate_backoff_max_greater_than_base(
        cls, v: float, info: ValidationInfo
    ) -> float:
        if info.data and "retry_backoff_base_seconds" in info.data:
            base = info.data["retry_backoff_base_seconds"]
            if v <= base:
                msg = (
                    f"retry_backoff_max_seconds ({v}) must be greater than "
                    f"retry_backoff_base_seconds ({base})"
                )
                raise ConfigValidationError(msg)
        return v


class MonitoringConfig(BaseModel):
    """Monitoring and performance tracking configuration."""

    metrics_retention_days: int = Field(
        default=90,
        description="Days to retain monitoring metrics",
        ge=7,
        le=365,
    )
    performance_threshold_ms: float = Field(
        default=5000.0,
        description="Performance threshold in milliseconds for alerts",
        ge=1000.0,
        le=30000.0,
    )
    success_rate_threshold: float = Field(
        default=0.95,
        description="Success rate threshold for service health alerts",
        ge=0.8,
        le=1.0,
    )
    anomaly_detection_enabled: bool = Field(
        default=True,
        description="Enable anomaly detection for monitoring metrics",
    )
    dashboard_update_interval_minutes: int = Field(
        default=5,
        description="Dashboard update interval in minutes",
        ge=1,
        le=60,
    )


class AlertConfig(BaseModel):
    """Alert system configuration."""

    # Alert evaluation settings
    evaluation_interval_minutes: int = Field(
        default=5,
        description="Interval for alert rule evaluation in minutes",
        ge=1,
        le=60,
    )
    max_rules_per_evaluation: int = Field(
        default=100,
        description="Maximum rules to evaluate per cycle",
        ge=10,
        le=1000,
    )

    # Alert delivery settings
    max_delivery_attempts: int = Field(
        default=3,
        description="Maximum delivery attempts for failed alerts",
        ge=1,
        le=10,
    )
    delivery_retry_delay_seconds: float = Field(
        default=60.0,
        description="Delay between retry attempts in seconds",
        ge=30.0,
        le=300.0,
    )
    delivery_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for delivery operations in seconds",
        ge=5.0,
        le=120.0,
    )

    # Rate limiting
    max_alerts_per_rule_per_hour: int = Field(
        default=10,
        description="Maximum alerts per rule per hour",
        ge=1,
        le=100,
    )
    max_total_alerts_per_hour: int = Field(
        default=1000,
        description="Maximum total alerts per hour",
        ge=100,
        le=10000,
    )
    cooldown_override_minutes: int = Field(
        default=5,
        description="Global cooldown override in minutes",
        ge=1,
        le=60,
    )

    # Data retention
    alert_retention_days: int = Field(
        default=90,
        description="Days to retain alert history",
        ge=7,
        le=365,
    )
    resolved_alert_retention_days: int = Field(
        default=30,
        description="Days to retain resolved alerts",
        ge=7,
        le=180,
    )

    # Delivery channels
    email_enabled: bool = Field(
        default=True,
        description="Enable email alert delivery",
    )
    webhook_enabled: bool = Field(
        default=True,
        description="Enable webhook alert delivery",
    )
    email_timeout_seconds: float = Field(
        default=30.0,
        description="Email delivery timeout in seconds",
        ge=10.0,
        le=120.0,
    )
    webhook_timeout_seconds: float = Field(
        default=10.0,
        description="Webhook delivery timeout in seconds",
        ge=5.0,
        le=30.0,
    )

    # SMTP configuration
    smtp_host: str = Field(
        default="localhost",
        description="SMTP server host",
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
        ge=25,
        le=65535,
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Use TLS for SMTP connection",
    )
    smtp_username: str | None = Field(
        default=None,
        description="SMTP username for authentication",
    )
    smtp_password: SecretStr | None = Field(
        default=None,
        description="SMTP password for authentication",
    )

    # Default recipients
    default_email_recipients: list[str] = Field(
        default_factory=list,
        description="List of default email recipients",
    )
    default_webhook_urls: list[str] = Field(
        default_factory=list,
        description="List of default webhook URLs",
    )

    @field_validator("smtp_port")  # type: ignore[misc]
    @classmethod
    def validate_smtp_port(cls, v: int) -> int:
        if not MIN_PORT <= v <= MAX_PORT:
            raise ConfigValidationError.invalid_database_port()
        return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent
        / ".env",  # energy_data_service root
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True,
    )

    # Application settings
    environment: str = Field(
        default="production",
        description="Application environment",
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database configuration",
    )
    entsoe_client: EntsoEClientConfig = Field(
        default_factory=EntsoEClientConfig,
        description="ENTSO-E client configuration",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )
    http: HttpConfig = Field(
        default_factory=HttpConfig,
        description="HTTP configuration",
    )
    backfill: BackfillConfig = Field(
        default_factory=BackfillConfig,
        description="Backfill configuration",
    )
    scheduler: SchedulerConfig = Field(
        default_factory=SchedulerConfig,
        description="Scheduler configuration",
    )
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig,
        description="Monitoring configuration",
    )
    alert: AlertConfig = Field(
        default_factory=AlertConfig,
        description="Alert system configuration",
    )

    @field_validator("environment")  # type: ignore[misc]
    @classmethod
    def validate_environment_settings(cls, v: str) -> str:
        normalized = v.lower()
        if normalized not in {"development", "staging", "production"}:
            raise ConfigValidationError.invalid_environment(v)
        return normalized

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def should_enable_debug_logging(self) -> bool:
        return self.debug or self.is_development

    def model_dump_safe(self) -> dict[str, Any]:
        """Safe model dump that redacts sensitive information."""
        data = self.model_dump()
        if "database" in data and "password" in data["database"]:
            data["database"]["password"] = REDACTED_VALUE
            # Remove the computed URL field that contains the password
            if "url" in data["database"]:
                del data["database"]["url"]
        if "entsoe_client" in data and "api_token" in data["entsoe_client"]:
            data["entsoe_client"]["api_token"] = REDACTED_VALUE
        if (
            "alert" in data
            and "smtp_password" in data["alert"]
            and data["alert"]["smtp_password"]
        ):
            data["alert"]["smtp_password"] = REDACTED_VALUE
        return data


def get_settings() -> Settings:
    return Settings()
