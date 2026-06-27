import os
from unittest.mock import patch

from app.config import Config


def test_config_kb_id_from_env():
    with patch.dict(os.environ, {"KNOWLEDGE_BASE_ID": "ABC123DEF4"}, clear=True):
        assert Config.KNOWLEDGE_BASE_ID == "ABC123DEF4"
