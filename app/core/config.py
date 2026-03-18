from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    APP_ENV: str = "prod"
    REQUEST_TIMEOUT_SECONDS: int = 10
    REFRESH_DEFAULT_SECONDS: int = 30
    SF_REPORT_CACHE_SECONDS: int = 120
    SF_HTTP_RETRY_TOTAL: int = 3
    SF_HTTP_RETRY_BACKOFF_SECONDS: float = 0.8
    SF_TOKEN_TTL_SECONDS: int = 900
    SF_TOKEN_RENEW_SKEW_SECONDS: int = 60

    SF_LOGIN_URL: str = "https://login.salesforce.com"
    SF_CONSUMER_KEY: str
    SF_CONSUMER_SECRET: str
    SF_USERNAME: str
    SF_PRIVATE_KEY_PATH: str
    SF_API_VERSION: str = "v59.0"

    SF_REPORT_1_ID: str = "00OU6000004ouzCMAQ"
    SF_REPORT_2_ID: str = "00OU6000004ouzDMAQ"
    SF_REPORT_3_ID: str = "00OU6000004mDGoMAM"


@lru_cache
def get_settings() -> Settings:
    return Settings()
