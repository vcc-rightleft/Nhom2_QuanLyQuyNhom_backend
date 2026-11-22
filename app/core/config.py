
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "app_db")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def database_url(self) -> str:
        user = quote_plus(self.DB_USER)
        password = (
            f":{quote_plus(self.DB_PASSWORD)}"
            if self.DB_PASSWORD
            else ""
        )

        return (
            f"mysql+pymysql://{user}{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )


settings = Settings()
