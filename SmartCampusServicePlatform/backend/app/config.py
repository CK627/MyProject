from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database (默认使用占位符，生产环境通过 .env 覆盖)
    DB_HOST: str = "<DB_HOST>"
    DB_PORT: int = 3306
    DB_USER: str = "<DB_USER>"
    DB_PASSWORD: str = "<DB_PASSWORD>"
    DB_NAME: str = "<DB_NAME>"
    
    # Security (必须通过环境变量修改)
    SECRET_KEY: str = "<SECRET_KEY_PLACEHOLDER>"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # 应用配置
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    
    # SMTP邮件配置
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@smartcampus.com"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # GitHub OAuth (可选配置，用于第三方登录)
    GITHUB_CLIENT_ID: str = "<GITHUB_CLIENT_ID>"
    GITHUB_CLIENT_SECRET: str = "<GITHUB_CLIENT_SECRET>"
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
