"""
Helper script for install.bat to write backend config.py
Usage: python _write_config.py <db_host> <db_port> <db_user> <db_password> <db_name> <secret_key> <config_path>
"""
import sys

if len(sys.argv) < 8:
    print("Usage: python _write_config.py <db_host> <db_port> <db_user> <db_password> <db_name> <secret_key> <config_path>")
    sys.exit(1)

db_host = sys.argv[1]
db_port = sys.argv[2]
db_user = sys.argv[3]
db_password = sys.argv[4]
db_name = sys.argv[5]
secret_key = sys.argv[6]
config_path = sys.argv[7]

content = f'''from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DB_HOST: str = "{db_host}"
    DB_PORT: int = {db_port}
    DB_USER: str = "{db_user}"
    DB_PASSWORD: str = "{db_password}"
    DB_NAME: str = "{db_name}"

    # JWT
    SECRET_KEY: str = "{secret_key}"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # App
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # SMTP email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@smartcampus.com"
    FRONTEND_URL: str = "http://localhost:3000"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{{self.DB_USER}}:{{self.DB_PASSWORD}}@{{self.DB_HOST}}:{{self.DB_PORT}}/{{self.DB_NAME}}?charset=utf8mb4"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
'''

with open(config_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"[OK] Config written to: {config_path}")
print(f"     DB_HOST     = {db_host}")
print(f"     DB_PORT     = {db_port}")
print(f"     DB_USER     = {db_user}")
print(f"     DB_NAME     = {db_name}")
