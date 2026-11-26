import json
import shutil

import pytest
from fastapi.testclient import TestClient

from app.assessments.content import ContentError
from app.core.config import Settings
from app.main import create_app
from tests.conftest import CONTENT_DIR


def test_editing_a_released_version_is_refused(tmp_path, db_url):
    content = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content)
    settings = Settings(environment="test", database_url=db_url, content_dir=content)
    with TestClient(create_app(settings, create_schema=True)):
        pass
    path = content / "instruments" / "mini-ipip-20.v1.0.0.json"
    data = json.loads(path.read_text())
    data["items"][0]["text"] = "Am the life of every party."
    path.write_text(json.dumps(data, indent=2))
    with pytest.raises(ContentError, match="changed after release"), TestClient(create_app(settings)):
        pass
