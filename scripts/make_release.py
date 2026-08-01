import os
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE_NAME = "PixelGlide-source"
RELEASE_DIR = DIST / RELEASE_NAME
ZIP_PATH = DIST / f"{RELEASE_NAME}.zip"

INCLUDE_FILES = [
    "README.md",
    "requirements.txt",
    ".gitignore",
    "assets/main.py",
    "assets/ui_config.py",
    "docs/manual_test_checklist.md",
    "docs/release_checklist.md",
    "scripts/make_release.py",
]

EXCLUDED_NAMES = {
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "pixelglide_save.json",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log"}


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in path.parts) or path.suffix in EXCLUDED_SUFFIXES


def copy_file(relative_path: str) -> None:
    src = ROOT / relative_path
    if not src.exists():
        raise FileNotFoundError(f"Required release file is missing: {relative_path}")
    if is_excluded(Path(relative_path)):
        raise ValueError(f"Release file is excluded by policy: {relative_path}")
    dst = RELEASE_DIR / relative_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_zip() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    RELEASE_DIR.mkdir(parents=True)

    for relative_path in INCLUDE_FILES:
        copy_file(relative_path)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in RELEASE_DIR.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(DIST)
                zf.write(file_path, arcname)

    print(f"Release folder: {RELEASE_DIR}")
    print(f"Release zip:    {ZIP_PATH}")


if __name__ == "__main__":
    os.chdir(ROOT)
    build_zip()
