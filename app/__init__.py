import logging
from pathlib import Path
from flask import Flask, jsonify

from app.config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))

    root = logging.getLogger()
    root.addHandler(file_handler)
    root.setLevel(logging.ERROR)

    app.logger.setLevel(logging.ERROR)

    from app.routes.kb_routes import kb_bp
    from app.routes.rag_routes import rag_bp

    app.register_blueprint(kb_bp, url_prefix="/api/v1/kb")
    app.register_blueprint(rag_bp, url_prefix="/api/v1/rag")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception(f"Unhandled exception: %s", e)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    return app