from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    Environment: str
    OpenAI_ApiKey: str | None = None
    ConnectionStrings_MongoDb: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
