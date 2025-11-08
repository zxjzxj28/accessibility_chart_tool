from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

from .auth import bp as auth_bp
from .charts import bp as charts_bp
from .config import get_config
from .extensions import db, jwt
from .tasks import worker


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(auth_bp)
    app.register_blueprint(charts_bp)

    @app.get("/")
    def healthcheck():
        return jsonify({"message": "Accessibility Chart Tool API"})

    worker.start(app)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
