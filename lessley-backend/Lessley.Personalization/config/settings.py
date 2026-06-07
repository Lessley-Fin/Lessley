# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic will automatically look for these keys in the .env file or system environment variables
    Environment: str
    ConnectionStrings_Rabbit: str
    ConnectionStrings_MongoDb: str
    RabbitMQ_Enabled: bool = False  # Default to False if not set
    OpenFinanceConfig_ClientId: str | None = None  # Optional setting
    OpenFinanceConfig_ClientSecret: str | None = None  # Optional setting
    OpenFinanceConfig_BaseUrl: str | None = None  # Optional setting
    Loki_Url: str | None = None  # Optional setting for Loki logging

    # Publisher protocol: "rabbitmq" (default) or "http"
    Publisher_Mode: str = "rabbitmq"
    # Required when Publisher_Mode=http: base URL of the Gateway API
    Gateway_BaseUrl: str | None = None
    # Admin JWT used by the HTTP publisher to call Gateway endpoints
    Gateway_ServiceToken: str | None = None

    # Tell Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# We instantiate it once here. Think of this as your Dependency Injection container providing the Singleton instance.
settings = Settings()
