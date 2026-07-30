# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic will automatically look for these keys in the .env file or system environment variables
    Environment: str
    ConnectionStrings_Rabbit: str
    ConnectionStrings_MongoDb: str
    RabbitMQ_Enabled: bool = True
    OpenFinanceConfig_ClientId: str | None = None
    OpenFinanceConfig_ClientSecret: str | None = None
    OpenFinanceConfig_BaseUrl: str | None = None
    Loki_Url: str | None = None  # Optional setting for Loki logging
    Cors_AllowOrigins: str = "http://localhost:8000,http://127.0.0.1:8000"  # Comma-separated origins

    # Shared secret the edge (Caddy) stamps on every inbound request as X-Edge-Key.
    # Server-only — never shipped to a browser. Blank disables edge verification.
    Edge_ApiKey: str | None = None
    # Mode 1 escape hatch: services run locally with no Caddy in front. Only honoured when
    # Environment is also Development, so production cannot be opened by this flag alone.
    Edge_AllowUnverified: bool = False
    # Identity used while the bypass is active, since nothing injects X-Auth-Email locally.
    Dev_AuthEmail: str | None = None

    # Tell Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# We instantiate it once here. Think of this as your Dependency Injection container providing the Singleton instance.
settings = Settings()
