"""Git operations for deadtree sync. All git interaction goes through here."""

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

OVERLEAF_BRANCH = "overleaf/main"

GITIGNORE_ENTRIES = [
    ".overleaf.json",
    "*.aux", "*.log", "*.out", "*.synctex.gz",
    "*.fdb_latexmk", "*.fls", "*.bbl", "*.blg",
]


def _git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd,
        capture_output=True, text=True, check=check,
    )


def ensure_repo(paper_dir: Path) -> None:
    """Initialize git repo if needed, ensure .gitignore covers our files."""
    if not (paper_dir / ".git").exists():
        _git("init", cwd=paper_dir)

    # Ensure .gitignore
    gi = paper_dir / ".gitignore"
    existing = gi.read_text() if gi.exists() else ""
    to_add = [e for e in GITIGNORE_ENTRIES if e not in existing]
    if to_add:
        with open(gi, "a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("# dead-tree\n")
            f.write("\n".join(to_add) + "\n")

    # Ensure at least one commit exists
    r = _git("rev-parse", "HEAD", cwd=paper_dir, check=False)
    if r.returncode != 0:
        _git("add", ".gitignore", cwd=paper_dir)
        _git("commit", "--allow-empty", "-m", "initial commit (dead-tree)", cwd=paper_dir)


def has_overleaf_branch(paper_dir: Path) -> bool:
    r = _git("rev-parse", "--verify", OVERLEAF_BRANCH, cwd=paper_dir, check=False)
    return r.returncode == 0


def current_branch(paper_dir: Path) -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD", cwd=paper_dir).stdout.strip()


def is_clean(paper_dir: Path) -> bool:
    return _git("status", "--porcelain", cwd=paper_dir).stdout.strip() == ""


def auto_commit(paper_dir: Path, message: str = "WIP (deadtree auto-commit)") -> None:
    """Stage all changes and commit."""
    _git("add", "-A", cwd=paper_dir)
    _git("commit", "-m", message, cwd=paper_dir)


def commit_remote_state(paper_dir: Path, remote_files: dict[str, bytes], action: str) -> str:
    """Write remote files to overleaf/main branch without disturbing the working tree.

    Uses a temporary git index to avoid checkout.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message = f"overleaf: {action} {ts}"

    # Get parent commit for overleaf/main (if it exists)
    parent_args = []
    if has_overleaf_branch(paper_dir):
        parent = _git("rev-parse", OVERLEAF_BRANCH, cwd=paper_dir).stdout.strip()
        parent_args = ["-p", parent]

    # Build a tree object from remote_files using a temporary index
    fd, tmp_index = tempfile.mkstemp(prefix="deadtree-idx-")
    os.close(fd)
    os.unlink(tmp_index)  # git needs to create the index file itself
    env = {**os.environ, "GIT_INDEX_FILE": tmp_index}

    def _run(*args, **kwargs):
        return subprocess.run(["git", *args], cwd=paper_dir, capture_output=True, check=True, **kwargs)

    try:
        for name, content in remote_files.items():
            blob = _run("hash-object", "-w", "--stdin", input=content).stdout.decode().strip()
            _run("update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", env=env)

        tree_hash = _run("write-tree", env=env, text=True).stdout.strip()
        commit_hash = _run("commit-tree", tree_hash, *parent_args, "-m", message, text=True).stdout.strip()

        # Point overleaf/main at the new commit
        _git("update-ref", f"refs/heads/{OVERLEAF_BRANCH}", commit_hash, cwd=paper_dir)

        return commit_hash
    finally:
        if os.path.exists(tmp_index):
            os.unlink(tmp_index)


def merge_overleaf(paper_dir: Path, allow_unrelated: bool = False) -> str:
    """Merge overleaf/main into current branch. Returns 'clean', 'conflict', or 'up-to-date'."""
    args = ["merge", OVERLEAF_BRANCH, "--no-edit"]
    if allow_unrelated:
        args.append("--allow-unrelated-histories")

    r = _git(*args, cwd=paper_dir, check=False)
    if r.returncode == 0:
        if "Already up to date" in r.stdout:
            return "up-to-date"
        return "clean"
    if "CONFLICT" in r.stdout or "CONFLICT" in r.stderr:
        return "conflict"
    # Unexpected error
    raise RuntimeError(f"git merge failed: {r.stderr}")


def diff_overleaf(paper_dir: Path) -> str:
    r = _git("diff", f"HEAD...{OVERLEAF_BRANCH}", cwd=paper_dir, check=False)
    return r.stdout


def log_overleaf(paper_dir: Path, n: int = 10) -> str:
    r = _git("log", OVERLEAF_BRANCH, "--oneline", f"-{n}", cwd=paper_dir, check=False)
    return r.stdout


def changed_files(paper_dir: Path) -> list[str]:
    """Files changed in HEAD vs overleaf/main."""
    if not has_overleaf_branch(paper_dir):
        return []
    r = _git("diff", "--name-only", f"{OVERLEAF_BRANCH}..HEAD", cwd=paper_dir, check=False)
    return [f for f in r.stdout.strip().splitlines() if f]
