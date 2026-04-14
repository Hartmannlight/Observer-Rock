from __future__ import annotations

import shutil
from pathlib import Path


TEMP_DIRECTORIES = (
    ".pytest_cache",
    ".pytest_cache_local",
    ".ruff_cache",
    "test_tmp",
)

TEMP_FILES = (
    ".tmp-docs.db",
    ".tmp-runs.db",
    ".tmp_patch_probe.txt",
)


def _remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return True
    path.unlink(missing_ok=True)
    return True


def cleanup_workspace(workspace_root: Path) -> list[Path]:
    removed_paths: list[Path] = []

    for name in TEMP_DIRECTORIES:
        candidate = workspace_root / name
        if _remove_path(candidate):
            removed_paths.append(candidate)

    for name in TEMP_FILES:
        candidate = workspace_root / name
        if _remove_path(candidate):
            removed_paths.append(candidate)

    for pattern in ("src/**/__pycache__", "tests/**/__pycache__"):
        for candidate in workspace_root.glob(pattern):
            if _remove_path(candidate):
                removed_paths.append(candidate)

    return removed_paths


def main() -> int:
    workspace_root = Path.cwd()
    removed_paths = cleanup_workspace(workspace_root)
    if removed_paths:
        for path in removed_paths:
            print(f"removed {path.relative_to(workspace_root)}")
    else:
        print("workspace already clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
