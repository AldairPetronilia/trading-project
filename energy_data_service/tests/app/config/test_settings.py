import os
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from app.config.settings import Settings
from pydantic import ValidationError


class TestSettings:
    def test_settings_requires_api_token(self) -> None:
        # Clear environment and disable .env file loading for this test
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["type"] == "missing"
            assert errors[0]["loc"] == ("api_token",)

    def test_settings_with_valid_api_token(self) -> None:
        # Clear environment and disable .env file loading for this test
        with patch.dict(os.environ, {}, clear=True):
            config = Settings(
                entsoe_client={"api_token": "test-token-123"},
                _env_file=None,
            )

            assert config.environment == "production"
            assert config.debug is False
            assert config.entsoe_client.api_token.get_secret_value() == "test-token-123"
            assert (
                str(config.entsoe_client.base_url) == "https://web-api.tp.entsoe.eu/api"
            )
            assert config.entsoe_client.user_agent == "energy-data-service/1.0.0"

    def test_api_token_validation_too_short(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(entsoe_client={"api_token": "short"}, _env_file=None)

        errors = exc_info.value.errors()
        assert any(
            "API token must be at least 10 characters" in str(error) for error in errors
        )

    def test_database_port_validation_invalid(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                entsoe_client={"api_token": "test-token-123"},
                database={"port": 0},
                _env_file=None,
            )

        errors = exc_info.value.errors()
        assert any(
            "Database port must be between 1 and 65535" in str(error)
            for error in errors
        )

    def test_database_port_validation_valid_range(self) -> None:
        # Test valid ports
        config_min = Settings(
            entsoe_client={"api_token": "test-token-123"},
            database={"port": 1},
            _env_file=None,
        )
        assert config_min.database.port == 1

        config_max = Settings(
            entsoe_client={"api_token": "test-token-123"},
            database={"port": 65535},
            _env_file=None,
        )
        assert config_max.database.port == 65535

    def test_environment_validation_invalid(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                entsoe_client={"api_token": "test-token-123"},
                environment="invalid",
                _env_file=None,
            )

        errors = exc_info.value.errors()
        assert any(
            "Environment must be one of: development, staging, production"
            in error.get("msg", "")
            for error in errors
        )

    def test_settings_defaults(self) -> None:
        config = Settings(entsoe_client={"api_token": "test-token-123"}, _env_file=None)

        # Application defaults
        assert config.environment == "production"
        assert config.debug is False

        # Database defaults
        assert config.database.host == "localhost"
        assert config.database.port == 5432
        assert config.database.user == "energy_user"
        assert config.database.password.get_secret_value() == "dummy"
        assert config.database.name == "energy_data_service"

        # HTTP defaults
        assert config.http.connection_timeout == timedelta(seconds=30)
        assert config.http.read_timeout == timedelta(seconds=60)
        assert config.http.write_timeout == timedelta(seconds=60)

        # Logging defaults
        assert config.logging.level == "INFO"
        assert config.logging.format == "json"
        assert config.logging.enable_request_logging is False

    def test_nested_config_override(self) -> None:
        config = Settings(
            entsoe_client={"api_token": "test-token-123"},
            database={"host": "custom-host", "port": 3306},
            http={"connection_timeout": timedelta(seconds=10)},
            logging={"level": "DEBUG", "format": "text"},
            _env_file=None,
        )

        assert config.database.host == "custom-host"
        assert config.database.port == 3306
        assert config.http.connection_timeout == timedelta(seconds=10)
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "text"

    def test_environment_properties(self) -> None:
        dev_config = Settings(
            entsoe_client={"api_token": "test-token-123"},
            environment="development",
            _env_file=None,
        )
        assert dev_config.is_development is True
        assert dev_config.is_production is False
        assert dev_config.should_enable_debug_logging is True

        prod_config = Settings(
            entsoe_client={"api_token": "test-token-123"},
            environment="production",
            _env_file=None,
        )
        assert prod_config.is_production is True
        assert prod_config.is_development is False
        assert prod_config.should_enable_debug_logging is False

    def test_debug_logging_with_debug_flag(self) -> None:
        config = Settings(
            entsoe_client={"api_token": "test-token-123"},
            environment="production",
            debug=True,
            _env_file=None,
        )
        assert config.should_enable_debug_logging is True

    def test_model_dump_safe(self) -> None:
        config = Settings(
            entsoe_client={"api_token": "secret-token-123"},
            database={"password": "secret-password"},
            _env_file=None,
        )
        safe_dump = config.model_dump_safe()

        assert safe_dump["database"]["password"] == "***REDACTED***"
        assert safe_dump["entsoe_client"]["api_token"] == "***REDACTED***"
        assert "secret-token-123" not in str(safe_dump)
        assert "secret-password" not in str(safe_dump)
        # URL is removed from safe dump for security
        assert "url" not in safe_dump["database"]

    def test_database_url_generation(self) -> None:
        config = Settings(
            entsoe_client={"api_token": "test-token-123"},
            database={
                "host": "testhost",
                "port": 3306,
                "user": "testuser",
                "password": "testpass",
                "name": "testdb",
            },
            _env_file=None,
        )

        expected_url = "postgresql+asyncpg://testuser:testpass@testhost:3306/testdb"
        assert config.database.url == expected_url


class TestEnvironmentVariableLoading:
    @patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "env-token-123"}, clear=True)
    def test_load_from_environment_variable(self) -> None:
        config = Settings()
        assert config.entsoe_client.api_token.get_secret_value() == "env-token-123"

    @patch.dict(
        os.environ,
        {
            "ENTSOE_CLIENT__API_TOKEN": "env-token-123",
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "DATABASE__HOST": "env-host",
            "DATABASE__PORT": "3306",
            "DATABASE__USER": "env-user",
            "DATABASE__PASSWORD": "env-pass",
            "DATABASE__NAME": "env-db",
            "LOGGING__LEVEL": "DEBUG",
            "LOGGING__FORMAT": "text",
            "LOGGING__ENABLE_REQUEST_LOGGING": "true",
        },
        clear=True,
    )
    def test_load_multiple_env_vars(self) -> None:
        config = Settings()

        assert config.entsoe_client.api_token.get_secret_value() == "env-token-123"
        assert config.environment == "development"
        assert config.debug is True
        assert config.database.host == "env-host"
        assert config.database.port == 3306
        assert config.database.user == "env-user"
        assert config.database.password.get_secret_value() == "env-pass"
        assert config.database.name == "env-db"
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "text"
        assert config.logging.enable_request_logging is True

    @patch.dict(
        os.environ,
        {
            "ENTSOE_CLIENT__API_TOKEN": "env-token-123",
            "HTTP__CONNECTION_TIMEOUT": "PT10S",
            "HTTP__READ_TIMEOUT": "PT90S",
        },
        clear=True,
    )
    def test_nested_config_from_env_vars(self) -> None:
        config = Settings()

        assert config.http.connection_timeout == timedelta(seconds=10)
        assert config.http.read_timeout == timedelta(seconds=90)


class TestDotEnvFileLoading:
    def test_load_from_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("ENTSOE_CLIENT__API_TOKEN=dotenv-token-123\n")

            config = Settings(_env_file=env_file)
            assert (
                config.entsoe_client.api_token.get_secret_value() == "dotenv-token-123"
            )

    def test_env_var_overrides_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("ENTSOE_CLIENT__API_TOKEN=dotenv-token-123\n")

            with patch.dict(os.environ, {"ENTSOE_CLIENT__API_TOKEN": "env-token-456"}):
                config = Settings(_env_file=env_file)
                assert (
                    config.entsoe_client.api_token.get_secret_value() == "env-token-456"
                )

    def test_complex_dotenv_loading(self) -> None:
        env_content = """
ENTSOE_CLIENT__API_TOKEN=complex-token-123
ENVIRONMENT=staging
DEBUG=false
DATABASE__HOST=dotenv-host
DATABASE__PORT=5433
DATABASE__USER=dotenv-user
DATABASE__PASSWORD=dotenv-pass
DATABASE__NAME=dotenv-db
LOGGING__LEVEL=ERROR
LOGGING__FORMAT=json
LOGGING__ENABLE_REQUEST_LOGGING=false
HTTP__CONNECTION_TIMEOUT=PT15S
HTTP__READ_TIMEOUT=PT90S
HTTP__WRITE_TIMEOUT=PT45S
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(env_content.strip())

            config = Settings(_env_file=env_file)

            assert (
                config.entsoe_client.api_token.get_secret_value() == "complex-token-123"
            )
            assert config.environment == "staging"
            assert config.debug is False
            assert config.database.host == "dotenv-host"
            assert config.database.port == 5433
            assert config.database.user == "dotenv-user"
            assert config.database.password.get_secret_value() == "dotenv-pass"
            assert config.database.name == "dotenv-db"
            assert config.logging.level == "ERROR"
            assert config.logging.format == "json"
            assert config.logging.enable_request_logging is False
            assert config.http.connection_timeout == timedelta(seconds=15)
            assert config.http.read_timeout == timedelta(seconds=90)
            assert config.http.write_timeout == timedelta(seconds=45)


class TestProjectEnvFileLoading:
    """Test loading from the actual project .env file."""

    def test_load_from_project_env_file(self) -> None:
        """Test that configuration loads correctly from the actual project .env file."""
        # This test will work with the actual energy_data_service .env file
        # Skip test if .env file doesn't exist (CI environment)
        project_env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if not project_env_file.exists():
            pytest.skip("Energy data service .env file not found")

        # Test that Settings can load from energy_data_service .env file
        # Note: This uses the actual credentials from the energy_data_service .env file
        config = Settings(_env_file=project_env_file)

        # Test database config from project .env
        assert config.database.host == "localhost"
        assert config.database.port == 5432
        assert config.database.user == "energy_user"
        # Note: Uses actual password from project .env file
        assert config.database.password.get_secret_value() == "energy_secure_password"
        assert config.database.name == "energy_data_service"

        # Test proper URL generation
        expected_url = "postgresql+asyncpg://energy_user:energy_secure_password@localhost:5432/energy_data_service"
        assert config.database.url == expected_url

        # Test ENTSO-E config from energy_data_service .env
        # Note: Uses actual API token from energy_data_service .env file
        assert (
            len(config.entsoe_client.api_token.get_secret_value()) > 10
        )  # Don't expose actual token
        assert str(config.entsoe_client.base_url) == "https://web-api.tp.entsoe.eu/api"

    def test_model_dump_safe_with_project_env(self) -> None:
        """Test that model_dump_safe properly redacts sensitive information from energy_data_service .env."""
        project_env_file = Path(__file__).parent.parent.parent.parent / ".env"
        if not project_env_file.exists():
            pytest.skip("Energy data service .env file not found")

        config = Settings(_env_file=project_env_file)
        safe_dump = config.model_dump_safe()

        # Ensure sensitive values are redacted
        assert safe_dump["database"]["password"] == "***REDACTED***"
        assert safe_dump["entsoe_client"]["api_token"] == "***REDACTED***"

        # Ensure actual sensitive values are not in the dump
        assert "energy_secure_password" not in str(safe_dump)
        # Don't check for actual API token since it's redacted

        # Ensure non-sensitive values are still present
        assert safe_dump["database"]["host"] == "localhost"
        assert safe_dump["database"]["port"] == 5432
        assert safe_dump["database"]["user"] == "energy_user"
        assert safe_dump["database"]["name"] == "energy_data_service"
        # Note: database URL is removed from safe dump for security
        assert "url" not in safe_dump["database"]


class TestGetSettingsFunction:
    def test_get_settings_function(self) -> None:
        # Test with environment variable to provide required API token
        from app.config.settings import get_settings

        with patch.dict(
            os.environ,
            {"ENTSOE_CLIENT__API_TOKEN": "function-test-token"},
            clear=True,
        ):
            settings = get_settings()

            assert isinstance(settings, Settings)
            assert settings.environment == "production"
            assert settings.debug is False
            assert (
                settings.entsoe_client.api_token.get_secret_value()
                == "function-test-token"
            )


class TestConfigValidationErrors:
    def test_database_port_validation_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                entsoe_client={"api_token": "test-token-123"},
                database={"port": 70000},
                _env_file=None,
            )

        errors = exc_info.value.errors()
        assert any(
            "Database port must be between 1 and 65535" in str(error)
            for error in errors
        )

    def test_api_token_validation_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(entsoe_client={"api_token": "short"}, _env_file=None)

        errors = exc_info.value.errors()
        assert any(
            "API token must be at least 10 characters" in str(error) for error in errors
        )

    def test_environment_validation_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                entsoe_client={"api_token": "test-token-123"},
                environment="invalid",
                _env_file=None,
            )

        errors = exc_info.value.errors()
        assert any(
            "Environment must be one of: development, staging, production"
            in error.get("msg", "")
            for error in errors
        )
