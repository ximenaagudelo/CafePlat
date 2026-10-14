import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "finca.db"


def build_database_uri():
    """SQLite en local. En Render se usa la URL de Neon (u otro Postgres)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{DB_PATH.as_posix()}"

    parts = urlsplit(url)
    scheme = "postgresql+psycopg" if parts.scheme in ("postgres", "postgresql") else parts.scheme

    netloc = parts.netloc
    if "@" in netloc:
        userinfo, hostport = netloc.rsplit("@", 1)
    else:
        userinfo, hostport = "", netloc

    # La cadena del panel de Neon suele ser el pooler. Las migraciones
    # necesitan el endpoint directo: se quita el sufijo "-pooler" del host.
    hostport = hostport.replace("-pooler", "", 1)
    if userinfo:
        netloc = f"{userinfo}@{hostport}"
    else:
        netloc = hostport

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != "channel_binding"
    ]
    if hostport.endswith("neon.tech") and not any(key == "sslmode" for key, _ in query):
        query.append(("sslmode", "require"))

    return urlunsplit((scheme, netloc, parts.path, urlencode(query), parts.fragment))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-temporal-desarrollo")
    DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"

    SQLALCHEMY_DATABASE_URI = build_database_uri()

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Neon apaga el cómputo tras unos minutos. Esto reconecta sin tumbar la app.
    if SQLALCHEMY_DATABASE_URI.startswith("postgresql"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        }

    FINCAS_UPLOAD_FOLDER = os.getenv(
        "FINCAS_UPLOAD_FOLDER",
        str(BASE_DIR / "app" / "static" / "uploads" / "fincas")
    )