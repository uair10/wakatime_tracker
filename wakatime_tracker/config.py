from dotenv import load_dotenv
from pydantic import Field
from functools import lru_cache

from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    name: str = "wakatime_tracker"
    user: str = "postgres"
    password: str = "postgres"

    class Config:
        env_prefix = "db_"

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class WakaTimeSettings(BaseSettings):
    """Настройки WakaTime API"""

    api_key: str
    user_id: str = "current"
    base_url: str = "https://wakatime.com/api/v1"

    class Config:
        env_prefix = "wakatime_"


class TelegramSettings(BaseSettings):
    """Настройки Telegram"""

    bot_token: str = None
    chat_id: str = None

    class Config:
        env_prefix = "telegram_"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


class LoggingSettings(BaseSettings):
    """Настройки логирования"""

    level: str = "INFO"
    render_json_logs: bool = False

    class Config:
        env_prefix = "logging_"


class SchedulerSettings(BaseSettings):
    """Настройки планировщика"""

    cron_schedule: str = "0 13 * * *"  # Ежедневно в 13:00
    import_initial_data: bool = True
    initial_data_path: str = "initial_data.json"
    run_on_startup: bool = True

    class Config:
        env_prefix = "scheduler_"


class Settings(BaseSettings):
    """Основные настройки приложения"""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    wakatime: WakaTimeSettings = Field(default_factory=WakaTimeSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)


@lru_cache()
def load_config() -> Settings:
    load_dotenv()
    return Settings()
