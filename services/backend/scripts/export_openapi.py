"""Write the OpenAPI document to packages/api-client/openapi.json (or --check that it is current)."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import REPO_ROOT, Settings
from app.main import create_app

TARGET = REPO_ROOT / "packages" / "api-client" / "openapi.json"


def render() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(environment="development", database_url=f"sqlite:///{Path(tmp) / 'x.db'}")
        spec = create_app(settings).openapi()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text() != text:
            print("packages/api-client/openapi.json is stale. Run: pnpm api:generate", file=sys.stderr)
            sys.exit(1)
        print("openapi.json is up to date")
    else:
        TARGET.write_text(text)
        print(f"wrote {TARGET}")
