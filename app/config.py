import json
import os

_KB_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "kb_config.json")


def _load_config() -> dict:
    try:
        with open(_KB_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(**kwargs):
    data = _load_config()
    data.update(kwargs)
    with open(_KB_CONFIG_PATH, "w") as f:
        json.dump(data, f)


def _load_stored_kb_id() -> str:
    return _load_config().get("kb_id", "")


def _save_kb_id(kb_id: str):
    _save_config(kb_id=kb_id)


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
