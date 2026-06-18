import logging
from pathlib import Path
from flask import Flask, jsonify # Added jsonify

from app.config import Config

def create_app():
    # 1. Create the logs directory safely
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 2. Upgraded Logging Config (File + Terminal + INFO level)
    logging.basicConfig(
        level=logging.INFO, # Changed from ERROR to INFO for debugging
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "app.log"), # Saves to your file
            logging.StreamHandler()                   # Prints to your terminal
        ]
    )

    app = Flask(__name__)
    app.config.from_object(Config)

    # 3. Register Blueprints
    from app.routes.kb_routes import kb_bp
    from app.routes.rag_routes import rag_bp

    app.register_blueprint(kb_bp, url_prefix="/api/v1/kb")
    app.register_blueprint(rag_bp, url_prefix="/api/v1/rag")

    # 4. Health Check
    @app.route("/health")
    def health():
        return {"status": "ok"}

    # 5. NEW: Global Crash Catcher!
    @app.errorhandler(Exception)
    def handle_exception(e):
        # This writes the full red Traceback into your app.log file
        app.logger.exception(f"A fatal error occurred: {e}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    return app