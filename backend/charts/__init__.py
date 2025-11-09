from flask import Blueprint

bp = Blueprint("charts", __name__, url_prefix="/api")

from . import routes  # noqa: E402,F401
