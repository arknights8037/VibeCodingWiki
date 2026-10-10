"""Real integration server. Uses a fresh DB, never the user's local data."""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

import uvicorn

backend = Path(__file__).resolve().parents[2] / "backend"
runtime = backend.parents[1] / ".local"
runtime.mkdir(exist_ok=True)
test_data = Path(tempfile.mkdtemp(prefix="integration-", dir=runtime))
os.environ["VCW_DATABASE_URL"] = f"sqlite+aiosqlite:///{test_data.as_posix()}/test.db"
os.environ["VCW_DATA_DIR"] = str(test_data)
os.environ["VCW_ADMIN_EMAIL"] = "admin@example.com"
os.environ["VCW_ADMIN_PASSWORD"] = "AdminPassword123!"
os.environ["VCW_ACCESS_SECRET"] = "integration-only-secret-not-used-by-local-app"
sys.path.insert(0, str(backend))
os.chdir(backend)

from app.seed import seed  # noqa: E402

asyncio.run(seed())
uvicorn.run("app.main:app", host="127.0.0.1", port=8001)
