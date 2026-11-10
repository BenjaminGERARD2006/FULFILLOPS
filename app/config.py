
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    POSTGRES_DB: str = "fulfillops"
    POSTGRES_USER: str = "fulfillops"
    DB_PASSWORD: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def database_url(self):
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.POSTGRES_DB,
        )


settings = Settings()
