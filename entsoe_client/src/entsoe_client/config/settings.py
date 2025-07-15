import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from entsoe_client.exceptions import ConfigValidationError

# Constants
MIN_API_TOKEN_LENGTH = 10
REDACTED_TOKEN = "***REDACTED***"  # noqa: S105


class HttpConfig(BaseModel):
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
    pool_timeout: timedelta = Field(
        default=timedelta(seconds=30),
        description="Timeout to acquire connection from pool",
    )
    max_connections: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum HTTP connections in pool",
    )
    max_keepalive_connections: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum keep-alive connections",
    )


class RetryConfig(BaseModel):
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts",
    )
    base_delay: timedelta = Field(
        default=timedelta(seconds=1),
        description="Base delay between retries",
    )
    max_delay: timedelta = Field(
        default=timedelta(seconds=60),
        description="Maximum delay between retries",
    )
    exponential_base: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff base multiplier",
    )
    retry_on_status: set[int] = Field(
        default={429, 502, 503, 504},
        description="HTTP status codes that trigger retries",
    )


class LoggingConfig(BaseModel):
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


class EntsoEClientConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ENTSOE_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_assignment=True,
    )

    api_token: SecretStr = Field(description="ENTSO-E API token for authentication")

    base_url: HttpUrl = Field(
        default="https://web-api.tp.entsoe.eu/api",
        description="ENTSO-E API base URL",
    )

    user_agent: str = Field(
        default="entsoe-python-client/1.0.0",
        description="User-Agent header for API requests",
    )

    environment: str = Field(
        default="production",
        description="Application environment",
    )

    debug: bool = Field(default=False, description="Enable debug mode")

    http: HttpConfig = Field(
        default_factory=HttpConfig,
        description="HTTP client configuration",
    )

    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry policy configuration",
    )

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )

    @field_validator("base_url")  # type: ignore[misc]
    @classmethod
    def validate_base_url(cls, v: HttpUrl) -> HttpUrl:
        if not str(v).startswith(("http://", "https://")):
            raise ConfigValidationError.invalid_base_url()
        return v

    @field_validator("api_token")  # type: ignore[misc]
    @classmethod
    def validate_api_token(cls, v: SecretStr) -> SecretStr:
        token = v.get_secret_value()
        if len(token) < MIN_API_TOKEN_LENGTH:
            raise ConfigValidationError.api_token_too_short()
        return v

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

    def get_auth_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
        }

    def get_auth_params(self) -> dict[str, str]:
        return {
            "securityToken": self.api_token.get_secret_value(),
        }

    @classmethod
    def load_from_file(cls, config_path: Path) -> "EntsoEClientConfig":
        if config_path.suffix.lower() == ".json":
            data = json.loads(config_path.read_text())
            return cls.model_validate(data)
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(config_path.read_text())
            return cls.model_validate(data)
        raise ConfigValidationError.unsupported_config_format(config_path.suffix)

    def model_dump_safe(self) -> dict:
        data = self.model_dump()
        if "api_token" in data:
            data["api_token"] = REDACTED_TOKEN
        return data


def load_config(
    config_path: Path | None = None,
    **overrides: Any,
) -> EntsoEClientConfig:
    if config_path and config_path.exists():
        config = EntsoEClientConfig.load_from_file(config_path)
        if overrides:
            return config.model_copy(update=overrides)
        return config

    return EntsoEClientConfig(**overrides)
