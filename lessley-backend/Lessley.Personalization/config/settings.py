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
    Loki_Url: str | None = None

    # Tell Pydantic to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# We instantiate it once here. Think of this as your Dependency Injection container providing the Singleton instance.
settings = Settings()
