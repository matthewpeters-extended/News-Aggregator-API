from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "mock" runs the bundled fixture providers so the app works with zero
    # external accounts. "live" calls the real provider APIs using the keys
    # below. Nothing else in the codebase changes between the two modes.
    app_mode: str = "mock"

    newsapi_key: str | None = None
    guardian_key: str | None = None
    nytimes_key: str | None = None

    jwt_secret: str = "dev-secret-change-me"
    aggregation_interval_minutes: int = 30


settings = Settings()
