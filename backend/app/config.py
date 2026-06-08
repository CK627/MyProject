from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = "<DB_HOST>"
    DB_PORT: int = 3306
    DB_USER: str = "<DB_USER>"
    DB_PASSWORD: str = "<DB_PASSWORD>"
    DB_NAME: str = "<DB_NAME>"

    # JWT配置
    SECRET_KEY: str = "<SECRET_KEY>"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # 应用配置
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"

    # SMTP/邮件配置 (可选，允许环境变量传入)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    GITHUB_CLIENT_ID: str = "<GITHUB_CLIENT_ID>"
    GITHUB_CLIENT_SECRET: str = "<GITHUB_CLIENT_SECRET>"
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        extra = "ignore"  # 允许 .env 中存在额外的环境变量

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
