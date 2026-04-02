"""Sync orchestration: thin layer over overleaf.py and repo.py."""

from pathlib import Path

import requests

from . import overleaf, repo


def _require_clean(paper_dir: Path, force: bool) -> None:
    if repo.is_clean(paper_dir):
        return
    if force:
        repo._git("add", "-A", cwd=paper_dir)
        repo._git("commit", "-m", "WIP (deadtree auto-commit)", cwd=paper_dir)
    else:
        raise SystemExit(
            "Uncommitted changes. Commit first, or use --force.\n"
            "  git add -A && git commit -m 'WIP'\n"
            "  -- or --\n"
            "  deadtree push --force"
        )


def _require_not_overleaf_branch(paper_dir: Path) -> None:
    if repo.current_branch(paper_dir) == repo.OVERLEAF_BRANCH:
        raise SystemExit(
            f"You are on the {repo.OVERLEAF_BRANCH} branch.\n"
            "Switch to your working branch first: git checkout main"
        )


def pull(session: requests.Session, project_id: str, paper_dir: Path,
         force: bool = False) -> None:
    repo.ensure_repo(paper_dir)
    _require_not_overleaf_branch(paper_dir)
    _require_clean(paper_dir, force)

    print(f"Pulling from Overleaf project {project_id}...")
    remote_files = overleaf.download(session, project_id)
    first_time = not repo.has_overleaf_branch(paper_dir)

    repo.commit_remote_state(paper_dir, remote_files, "pull")
    result = repo.merge_overleaf(paper_dir, allow_unrelated=first_time)

    if result == "conflict":
        print("\nMerge conflicts detected. Resolve them, then:")
        print("  git add -A && git commit")
    elif result == "clean":
        print(f"Done. Pulled {len(remote_files)} file(s).")
    else:
        print("Already up to date.")


def push(session: requests.Session, project_id: str, paper_dir: Path,
         csrf: str, force: bool = False) -> None:
    repo.ensure_repo(paper_dir)
    _require_not_overleaf_branch(paper_dir)
    _require_clean(paper_dir, force)

    print(f"Pushing to Overleaf project {project_id}...")

    if repo.has_overleaf_branch(paper_dir):
        changed = [f for f in repo.changed_files(paper_dir) if overleaf.should_sync(f)]
    else:
        changed = _local_syncable(paper_dir)

    if not changed:
        print("Nothing to push.")
        return

    files = {f: (paper_dir / f).read_bytes() for f in changed if (paper_dir / f).exists()}
    folder_map, root_id = overleaf.get_project_tree(session, project_id)
    n = overleaf.upload(session, project_id, csrf, folder_map, root_id, files)

    remote_files = overleaf.download(session, project_id)
    repo.commit_remote_state(paper_dir, remote_files, "push")
    print(f"Done. {n} file(s) uploaded.")


def status(session: requests.Session, project_id: str, paper_dir: Path) -> None:
    repo.ensure_repo(paper_dir)
    print("Comparing local with Overleaf...")

    remote_files = overleaf.download(session, project_id)

    if not repo.has_overleaf_branch(paper_dir):
        print(f"  No sync history. {len(remote_files)} remote file(s).")
        print("  Run: deadtree pull")
        return

    repo.commit_remote_state(paper_dir, remote_files, "status check")
    diff_out = repo.diff_overleaf(paper_dir)
    print(diff_out if diff_out else "  Everything in sync.")


def diff(paper_dir: Path) -> None:
    if not repo.has_overleaf_branch(paper_dir):
        raise SystemExit("No sync history. Run: deadtree pull")
    output = repo.diff_overleaf(paper_dir)
    print(output or "No differences.")


def log(paper_dir: Path, n: int = 10) -> None:
    if not repo.has_overleaf_branch(paper_dir):
        raise SystemExit("No sync history. Run: deadtree pull")
    print(repo.log_overleaf(paper_dir, n))


def _local_syncable(paper_dir: Path) -> list[str]:
    return [
        str(p.relative_to(paper_dir))
        for p in sorted(paper_dir.rglob("*"))
        if p.is_file()
        and not str(p.relative_to(paper_dir)).startswith(".")
        and overleaf.should_sync(str(p.relative_to(paper_dir)))
    ]
