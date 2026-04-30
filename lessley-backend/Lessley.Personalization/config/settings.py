# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic will automatically look for these keys in the .env file or system environment variables
    Environment: str
    ConnectionStrings_Rabbit: str
    MONGO_CONNECTION_STRING: str
    MONGO_USER: str | None = None
    MONGO_PASSWORD: str | None = None
    MONGO_AUTH_SOURCE: str = "admin"
    RabbitMQ_Enabled: bool = False  # Default to False if not set
    OpenFinanceConfig_ClientId: str | None = None  # Optional setting
    OpenFinanceConfig_ClientSecret: str | None = None  # Optional setting
    OpenFinanceConfig_BaseUrl: str | None = None  # Optional setting
    Loki_Url: str | None = None  # Optional setting for Loki logging  

    # Tell Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# We instantiate it once here. Think of this as your Dependency Injection container providing the Singleton instance.
settings = Settings()
