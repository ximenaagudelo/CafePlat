import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "finca.db"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-temporal-desarrollo")
    DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DB_PATH.as_posix()}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False