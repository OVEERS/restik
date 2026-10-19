from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_minutes: int = 60
    cors_origins: list[str] = []

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()