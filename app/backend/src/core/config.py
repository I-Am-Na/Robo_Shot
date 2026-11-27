from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "robo"
    db_password: str = "robo"
    db_name: str = "robo_shot"
    timezone: str = "Asia/Seoul"

    # 주유를 마친(done) 차량이 빠져나가는 동안 다시 감지돼도 이 시간(초) 동안은 대기열에 다시 넣지 않는다.
    done_redetect_window_seconds: int = 120

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()
