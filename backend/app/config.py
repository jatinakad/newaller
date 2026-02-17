# Environment and configuration helpers for AllerSense backend
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AllerSense"
    debug: bool = True

settings = Settings()
