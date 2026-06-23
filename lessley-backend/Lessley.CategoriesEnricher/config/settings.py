from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    Environment: str
    OpenAI_ApiKey: str | None = None
    ConnectionStrings_MongoDb: str | None = None

    COLLEGE_API_BASE: str = None
    COLLEGE_MODEL_HOST: str | None = None
    COLLEGE_MODEL_NAME: str | None = None
    COLLEGE_API_KEY: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
