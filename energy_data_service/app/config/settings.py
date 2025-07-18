from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    SecretStr,
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
        return data


def get_settings() -> Settings:
    return Settings()
