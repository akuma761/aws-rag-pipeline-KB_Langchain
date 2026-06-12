import json
import os

_KB_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "kb_config.json")


def _load_stored_kb_id() -> str:
    try:
        with open(_KB_CONFIG_PATH) as f:
            data = json.load(f)
            return data.get("kb_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def _save_kb_id(kb_id: str):
    with open(_KB_CONFIG_PATH, "w") as f:
        json.dump({"kb_id": kb_id}, f)


class Config:
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

    KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID") or _load_stored_kb_id() or ""
    MODEL_ID = os.getenv("MODEL_ID", "amazon.nova-lite-v1:0")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
