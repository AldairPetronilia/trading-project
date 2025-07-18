class ConfigValidationError(ValueError):
    def __init__(self, message: str, field_name: str | None = None):
        super().__init__(message)
        self.field_name = field_name

    @classmethod
    def invalid_database_port(cls) -> "ConfigValidationError":
        return cls("Database port must be between 1 and 65535", "port")

    @classmethod
    def api_token_too_short(cls) -> "ConfigValidationError":
        return cls("API token must be at least 10 characters long", "api_token")

    @classmethod
    def invalid_environment(cls, value: str) -> "ConfigValidationError":
        return cls(
            f"Environment must be one of: development, staging, production. Got: {value}",
            "environment",
        )

    @classmethod
    def invalid_base_url(cls) -> "ConfigValidationError":
        return cls("Base URL must start with http:// or https://", "base_url")

    @classmethod
    def unsupported_config_format(cls, suffix: str) -> "ConfigValidationError":
        return cls(
            f"Unsupported config file format: {suffix}. Supported formats: .json, .yaml, .yml",
            "config_format",
        )
