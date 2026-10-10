"""Package the corrected code and video without credentials or runtime caches."""
from pathlib import Path
import os
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ["agent", "contexts", "parsed", "decisions", "reports", "docs", "scripts", "tests", ".streamlit", "ui",
         "README.md", "requirements.txt", "start-ui.cmd", ".gitignore"]


def main():
    secrets = []
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("TOKENROUTER_API_KEY="):
                value = line.split("=", 1)[1].strip().strip('"')
                if value:
                    secrets.append(value.encode())
    files = []
    for name in ALLOW:
        path = ROOT / name
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            if not candidate.is_file() or "__pycache__" in candidate.parts or candidate.suffix == ".pyc":
                continue
            if candidate.name == ".env" or ".git" in candidate.parts:
                continue
            if any(secret in candidate.read_bytes() for secret in secrets):
                raise ValueError("A selected artifact contains a credential; packaging stopped.")
            files.append(candidate)
    out = ROOT / "release"
    out.mkdir(exist_ok=True)
    target = out / "condorcet_submission_corrected.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, "condorcet-agent/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all("/.env" not in name and "/.git/" not in name and "/.venv/" not in name and "/cache/" not in name for name in archive.namelist())
    print(f"Packaged {len(files)} source/media files; {target.stat().st_size:,} bytes. Credentials and runtime caches excluded.")


if __name__ == "__main__":
    main()
