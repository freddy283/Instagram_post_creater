from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    APP_NAME: str = "Aureus"
    APP_ENV: str = "development"
    SECRET_KEY: str = secrets.token_urlsafe(32)

    DATABASE_URL: str = "sqlite:///./dailyquote.db"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    ENCRYPTION_KEY: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # FREE: Groq LLaMA-3.3 for script generation (console.groq.com — no CC)
    GROQ_API_KEY: str = ""

    # FREE: Pixabay for background images (pixabay.com/api/docs — no CC)
    PIXABAY_API_KEY: str = ""

    # Instagram OAuth (optional — only needed if user wants auto-posting)
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = "http://localhost:8000/api/instagram/callback"

    # Public URL for serving videos to Instagram API
    # In dev: run `ngrok http 8000`, paste the https URL here
    PUBLIC_URL: str = "http://localhost:8000"

    # Video content settings
    VIDEO_THEME: str = "success, growth and daily motivation"
    BRAND_HANDLE: str = "@daily_wisdom"
    VIDEOS_DIR: str = "./videos"

    # AWS S3 (optional, future)
    USE_S3: bool = False
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = "aureus-videos"
    AWS_REGION: str = "us-east-1"

    ALLOWED_ORIGINS: str = "http://localhost:3000"
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()

if not settings.ENCRYPTION_KEY:
    from cryptography.fernet import Fernet
    settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
