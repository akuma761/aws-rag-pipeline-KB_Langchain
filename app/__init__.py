from flask import Flask
from app.config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.routes.kb_routes import kb_bp
    from app.routes.rag_routes import rag_bp

    app.register_blueprint(kb_bp, url_prefix="/api/v1/kb")
    app.register_blueprint(rag_bp, url_prefix="/api/v1/rag")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
