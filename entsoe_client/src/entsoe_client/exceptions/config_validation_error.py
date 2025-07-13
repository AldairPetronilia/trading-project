class ConfigValidationError(ValueError):
    def __init__(self, message: str, field_name: str | None = None):
        super().__init__(message)
        self.field_name = field_name

    @classmethod
    def invalid_base_url(cls) -> "ConfigValidationError":
        return cls("base_url must start with http:// or https://", "base_url")

    @classmethod
    def api_token_too_short(cls) -> "ConfigValidationError":
        return cls("api_token must be at least 10 characters long", "api_token")

    @classmethod
    def invalid_environment(cls, value: str) -> "ConfigValidationError":
        message = f"environment must be one of: development, staging, production. Got: {value}"
        return cls(message, "environment")

    @classmethod
    def unsupported_config_format(cls, format_type: str) -> "ConfigValidationError":
        return cls(f"Unsupported config file format: {format_type}")
