import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"

DATABASE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "traiteur-lounna-casa-secret-key")
    DATABASE = str(DATABASE_DIR / "database.db")
    UPLOAD_FOLDER = str(UPLOAD_DIR)
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "lounna123")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024