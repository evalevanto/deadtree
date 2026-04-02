"""Project configuration discovery and management."""

import json
import os
import re
from pathlib import Path

CONFIG_FILENAME = ".overleaf.json"
SESSION_DIR_NAME = ".overleaf_session"

SYNC_EXTENSIONS = {
    ".tex", ".bib", ".sty", ".cls", ".bst",
    ".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg",
    ".txt", ".md", ".csv", ".json",
}

IGNORE_PATTERNS = {
    "*.aux", "*.log", "*.out", "*.synctex.gz",
    "*.fdb_latexmk", "*.fls", "*.bbl", "*.blg",
    "main.pdf", ".overleaf.json", ".overleaf_session",
}


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from start (default cwd) looking for .overleaf.json."""
    d = (start or Path.cwd()).resolve()
    while True:
        candidate = d / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        if d.parent == d:
            return None
        d = d.parent


def load_config(path: Path | None = None) -> dict:
    """Load config from .overleaf.json, with env-var overrides."""
    cfg = {}
    config_path = path or find_config()
    if config_path and config_path.is_file():
        cfg = json.loads(config_path.read_text())
        # Store where we found the config so paths are relative to it
        cfg["_config_dir"] = str(config_path.parent)

    # Env vars override file config
    if pid := os.getenv("OVERLEAF_PROJECT_ID"):
        cfg["project_id"] = pid
    if pd := os.getenv("OVERLEAF_PAPER_DIR"):
        cfg["paper_dir"] = pd

    return cfg


_PROJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")


def get_project_id(cfg: dict) -> str:
    pid = cfg.get("project_id")
    if not pid:
        raise SystemExit(
            "No project_id configured.\n"
            "Run: deadtree init <project-url-or-id>"
        )
    if not _PROJECT_ID_RE.match(pid):
        raise SystemExit(
            f"Invalid project ID: {pid!r}\n"
            "Expected a 24-character hex string."
        )
    return pid


def get_paper_dir(cfg: dict) -> Path:
    """Resolve paper_dir relative to config file location."""
    config_dir = Path(cfg.get("_config_dir", ".")).resolve()
    rel = cfg.get("paper_dir", ".")
    return (config_dir / rel).resolve()


def get_session_dir(cfg: dict) -> Path:
    """Session dir lives next to .overleaf.json (or in cwd)."""
    config_dir = Path(cfg.get("_config_dir", ".")).resolve()
    return config_dir / SESSION_DIR_NAME


def init_config(project_id: str, paper_dir: str = ".") -> Path:
    """Write a .overleaf.json in the current directory."""
    # Accept full URLs: https://www.overleaf.com/project/<id>
    if "/" in project_id:
        parts = project_id.rstrip("/").split("/")
        project_id = parts[-1]

    if not _PROJECT_ID_RE.match(project_id):
        raise SystemExit(
            f"Invalid project ID: {project_id!r}\n"
            "Expected a 24-character hex string (or an Overleaf project URL)."
        )

    config = {"project_id": project_id, "paper_dir": paper_dir}
    out = Path.cwd() / CONFIG_FILENAME
    out.write_text(json.dumps(config, indent=2) + "\n")
    return out
