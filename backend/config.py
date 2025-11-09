import os
from datetime import timedelta
from pathlib import Path
from typing import Optional
BASE_DIR = Path(__file__).resolve().parent
class Config:
    """Default application configuration.

    Values fall back to development-friendly defaults so the project works out of the
    box. For production usage, set the corresponding environment variables or edit the
    defaults here explicitly.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + str(BASE_DIR / "accessibility_chart_tool.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # === JWT 常见安全配置（HS256，对称密钥）===
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key")
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

    # Token 放哪里（常用：headers 或 headers+cookies）
    JWT_TOKEN_LOCATION = os.environ.get("JWT_TOKEN_LOCATION", "headers").split(",")

    # Cookie 相关（本地开发 Secure 可设 False；生产必须 True，且配 HTTPS）
    JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "False").lower() == "true"
    JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = os.environ.get("JWT_COOKIE_CSRF_PROTECT", "True").lower() == "true"

    # 发行方/受众（跨服务时能防误用）
    JWT_ENCODE_ISSUER = os.environ.get("JWT_ENCODE_ISSUER", "chart-tool-api")
    JWT_DECODE_AUDIENCE = os.environ.get("JWT_DECODE_AUDIENCE", "chart-tool-web")

    # 有效期：常用方案 = 短 Access + 长 Refresh
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "30")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "14")))

    # 其他
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_by_name = {
    "default": Config,
    "testing": TestConfig,
}


def get_config(name: Optional[str] = None):
    return config_by_name.get(name or "default", Config)
