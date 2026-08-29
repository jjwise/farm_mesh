"""Application settings loaded from environment variables or secret files."""

from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


def read_secret(value: str, file_path: str) -> str:
    """Resolve a secret from a mounted file, falling back to an environment value."""

    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()
    return value


class Settings(BaseSettings):
    """Runtime settings for API, storage, and auth."""

    app_name: str = "Irrigation Pod Tracker API"
    database_url: str = ""
    database_host: str = ""
    database_port: int = 5432
    database_name: str = "irrigation"
    database_user: str = "irrigation"
    database_password: str = ""
    database_password_file: str = ""
    api_token: str = "change-me-token"
    api_token_file: str = ""
    admin_token: str = "change-me-admin-token"
    admin_token_file: str = ""
    snapshot_window_seconds: int = 30
    max_history_points: int = 10000

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_password_file: str = ""
    mqtt_client_id: str = "irrigation-backend"
    mqtt_topic: str = "farm/+/lines/+/trackers/+/telemetry"
    mqtt_qos: int = 1
    mqtt_tls: bool = False
    mqtt_ca_file: str = ""
    mqtt_keepalive_seconds: int = 60
    mqtt_command_qos: int = 1
    mqtt_publish_timeout_seconds: int = 5
    command_ttl_seconds: int = 120
    command_retry_seconds: int = 10
    command_hmac_key: str = ""
    command_hmac_key_file: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="IRRIGATION_")

    @property
    def resolved_database_url(self) -> str:
        """Build a PostgreSQL URL without placing its password in Compose environment."""

        if self.database_url:
            return self.database_url
        if not self.database_host:
            return "sqlite:///./irrigation_tracker.db"
        password = quote_plus(read_secret(self.database_password, self.database_password_file))
        user = quote_plus(self.database_user)
        database = quote_plus(self.database_name)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.database_host}:{self.database_port}/{database}"
        )

    @property
    def resolved_api_token(self) -> str:
        return read_secret(self.api_token, self.api_token_file)

    @property
    def resolved_admin_token(self) -> str:
        return read_secret(self.admin_token, self.admin_token_file)

    @property
    def resolved_mqtt_password(self) -> str:
        return read_secret(self.mqtt_password, self.mqtt_password_file)

    @property
    def resolved_command_hmac_key(self) -> str:
        return read_secret(self.command_hmac_key, self.command_hmac_key_file)


settings = Settings()
