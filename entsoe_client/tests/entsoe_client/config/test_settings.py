import os
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from entsoe_client.config.settings import EntsoEClientConfig, load_config


class TestEntsoEClientConfig:
    def test_config_requires_api_token(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            EntsoEClientConfig()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("api_token",)

    def test_config_with_valid_api_token(self) -> None:
        config = EntsoEClientConfig(api_token="test-token-123")

        assert config.api_token.get_secret_value() == "test-token-123"
        assert str(config.base_url) == "https://web-api.tp.entsoe.eu/api"
        assert config.environment == "production"
        assert config.debug is False

    def test_api_token_validation_too_short(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            EntsoEClientConfig(api_token="short")

        errors = exc_info.value.errors()
        assert any("at least 10 characters" in str(error) for error in errors)

    def test_base_url_validation_invalid_scheme(self) -> None:
        with pytest.raises(ValidationError):
            EntsoEClientConfig(
                api_token="valid-token-123",
                base_url="ftp://invalid.com",
            )

    def test_environment_validation_case_insensitive(self) -> None:
        with patch.dict(os.environ, {"ENTSOE_ENVIRONMENT": "DEVELOPMENT"}, clear=True):
            config = EntsoEClientConfig(api_token="valid-token-123")
            assert config.environment == "development"

    def test_nested_config_defaults(self) -> None:
        config = EntsoEClientConfig(api_token="valid-token-123")

        assert config.http.connection_timeout == timedelta(seconds=30)
        assert config.http.read_timeout == timedelta(seconds=60)
        assert config.retry.max_attempts == 3
        assert config.retry.retry_on_status == {429, 502, 503, 504}
        assert config.logging.level == "INFO"

    def test_nested_config_override(self) -> None:
        config = EntsoEClientConfig(
            api_token="valid-token-123",
            http={"connection_timeout": timedelta(seconds=10)},
            retry={"max_attempts": 5},
        )

        assert config.http.connection_timeout == timedelta(seconds=10)
        assert config.retry.max_attempts == 5

    def test_is_development_property(self) -> None:
        dev_config = EntsoEClientConfig(
            api_token="valid-token-123",
            environment="development",
        )
        assert dev_config.is_development is True
        assert dev_config.is_production is False

    def test_is_production_property(self) -> None:
        prod_config = EntsoEClientConfig(
            api_token="valid-token-123",
            environment="production",
        )
        assert prod_config.is_production is True
        assert prod_config.is_development is False

    def test_should_enable_debug_logging(self) -> None:
        debug_config = EntsoEClientConfig(api_token="valid-token-123", debug=True)
        assert debug_config.should_enable_debug_logging is True

        dev_config = EntsoEClientConfig(
            api_token="valid-token-123",
            environment="development",
        )
        assert dev_config.should_enable_debug_logging is True

        prod_config = EntsoEClientConfig(
            api_token="valid-token-123",
            environment="production",
            debug=False,
        )
        assert prod_config.should_enable_debug_logging is False

    def test_get_auth_headers(self) -> None:
        config = EntsoEClientConfig(
            api_token="valid-token-123",
            user_agent="custom-agent/1.0",
        )
        headers = config.get_auth_headers()
        assert headers == {"User-Agent": "custom-agent/1.0"}

    def test_get_auth_params(self) -> None:
        config = EntsoEClientConfig(api_token="valid-token-123")
        params = config.get_auth_params()
        assert params == {"securityToken": "valid-token-123"}

    def test_model_dump_safe_masks_token(self) -> None:
        config = EntsoEClientConfig(api_token="secret-token-123")
        safe_dump = config.model_dump_safe()

        assert safe_dump["api_token"] == "***REDACTED***"
        assert "secret-token-123" not in str(safe_dump)


class TestEnvironmentVariableLoading:
    @patch.dict(os.environ, {"ENTSOE_API_TOKEN": "env-token-123"}, clear=True)
    def test_load_from_environment_variable(self) -> None:
        config = EntsoEClientConfig()
        assert config.api_token.get_secret_value() == "env-token-123"

    @patch.dict(
        os.environ,
        {
            "ENTSOE_API_TOKEN": "env-token-123",
            "ENTSOE_ENVIRONMENT": "development",
            "ENTSOE_DEBUG": "true",
        },
        clear=True,
    )
    def test_load_multiple_env_vars(self) -> None:
        config = EntsoEClientConfig()

        assert config.api_token.get_secret_value() == "env-token-123"
        assert config.environment == "development"
        assert config.debug is True

    @patch.dict(
        os.environ,
        {"ENTSOE_HTTP__CONNECTION_TIMEOUT": "PT10S", "ENTSOE_RETRY__MAX_ATTEMPTS": "5"},
        clear=True,
    )
    def test_nested_config_from_env_vars(self) -> None:
        config = EntsoEClientConfig(api_token="valid-token-123")

        assert config.http.connection_timeout == timedelta(seconds=10)
        assert config.retry.max_attempts == 5


class TestDotEnvFileLoading:
    def test_load_from_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("ENTSOE_API_TOKEN=dotenv-token-123\n")

            config = EntsoEClientConfig(_env_file=env_file)
            assert config.api_token.get_secret_value() == "dotenv-token-123"

    def test_env_var_overrides_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("ENTSOE_API_TOKEN=dotenv-token-123\n")

            with patch.dict(os.environ, {"ENTSOE_API_TOKEN": "env-token-456"}):
                config = EntsoEClientConfig(_env_file=env_file)
                assert config.api_token.get_secret_value() == "env-token-456"

    def test_complex_dotenv_loading(self) -> None:
        env_content = """
ENTSOE_API_TOKEN=complex-token-123
ENTSOE_ENVIRONMENT=staging
ENTSOE_DEBUG=false
ENTSOE_USER_AGENT=test-agent/2.0
ENTSOE_HTTP__CONNECTION_TIMEOUT=PT15S
ENTSOE_RETRY__MAX_ATTEMPTS=7
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(env_content.strip())

            config = EntsoEClientConfig(_env_file=env_file)

            assert config.api_token.get_secret_value() == "complex-token-123"
            assert config.environment == "staging"
            assert config.debug is False
            assert config.user_agent == "test-agent/2.0"
            assert config.http.connection_timeout == timedelta(seconds=15)
            assert config.retry.max_attempts == 7


class TestConfigFileLoading:
    def test_load_from_json_file(self) -> None:
        config_data = {
            "api_token": "json-token-123",
            "environment": "development",
            "debug": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = load_config(config_path)
            assert config.api_token.get_secret_value() == "json-token-123"
            assert config.environment == "development"
            assert config.debug is True
        finally:
            config_path.unlink()

    def test_load_from_yaml_file(self) -> None:
        config_content = """
api_token: yaml-token-123
environment: staging
http:
  connection_timeout: 20
  read_timeout: 90
retry:
  max_attempts: 6
  base_delay: 2
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)

        try:
            config = load_config(config_path)
            assert config.api_token.get_secret_value() == "yaml-token-123"
            assert config.environment == "staging"
            assert config.http.connection_timeout == timedelta(seconds=20)
            assert config.http.read_timeout == timedelta(seconds=90)
            assert config.retry.max_attempts == 6
            assert config.retry.base_delay == timedelta(seconds=2)
        finally:
            config_path.unlink()

    def test_load_with_overrides(self) -> None:
        config_data = {"api_token": "file-token-123"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = load_config(config_path, environment="development", debug=True)
            assert config.api_token.get_secret_value() == "file-token-123"
            assert config.environment == "development"
            assert config.debug is True
        finally:
            config_path.unlink()

    def test_load_nonexistent_file(self) -> None:
        config = load_config(Path("nonexistent.json"), api_token="fallback-token")
        assert config.api_token.get_secret_value() == "fallback-token"

    def test_unsupported_file_format(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("api_token=txt-token")
            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Unsupported config file format"):
                EntsoEClientConfig.load_from_file(config_path)
        finally:
            config_path.unlink()
