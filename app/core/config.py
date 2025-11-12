from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    project_name: str = 'VibeZone'
    version: str = '1.0.0'

    frontend_url : str = ""
    frontend_password_reset_path: str = "auth"
    backend_url : str = ""

    database_url : str = ""

    secret_key : str = ""
    algorithm : str = "HS256"
    access_token_expire_minutes : int = 60
    password_reset_expire_minutes : int = 60

    google_client_id : str = ""
    google_client_secret : str = ""
    google_redirect_uri : str = ""

    resend_api_key : str = ""
    resend_from_address : str = "delivered@resend.dev"

    gemini_api_key : str = ""
    ai_model : str = "gemini-2.0"
    
    redis_url : str = ""

    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_plan_id: str = ""
    stripe_success_url: str = "http://127.0.0.1:3000/dashboard/overview"
    stripe_cancel_url: str = "http://127.0.0.1:3000/dashboard/overview"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()