import re
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def workspace_tmp_root() -> Path:
    root = PROJECT_ROOT / "test_tmp"
    root.mkdir(exist_ok=True)
    return root


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest, workspace_tmp_root: Path) -> Path:
    # Keep tmp data inside the workspace to avoid Windows ACL issues in the user temp dir.
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", request.node.name).strip("-") or "test"
    path = workspace_tmp_root / f"{safe_name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path
