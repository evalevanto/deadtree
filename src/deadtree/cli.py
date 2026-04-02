"""CLI entrypoint for deadtree."""

import argparse
import sys

from . import __version__
from .auth import get_csrf, get_session, login
from .config import get_paper_dir, get_project_id, get_session_dir, init_config, load_config
from .sync import diff, log, pull, push, status


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="deadtree",
        description="Sync local LaTeX projects with Overleaf. Because papers are dead trees.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Configure project: write .overleaf.json")
    p_init.add_argument("project", help="Overleaf project URL or ID")
    p_init.add_argument("--paper-dir", default=".", help="Local directory to sync (default: .)")

    sub.add_parser("login", help="Open browser to log in to Overleaf")

    p_push = sub.add_parser("push", help="Upload local → Overleaf")
    p_push.add_argument("--force", action="store_true", help="Auto-commit uncommitted changes")

    p_pull = sub.add_parser("pull", help="Download Overleaf → local")
    p_pull.add_argument("--force", action="store_true", help="Auto-commit uncommitted changes")

    sub.add_parser("status", help="Show diff between local and Overleaf")
    sub.add_parser("diff", help="Show git diff against Overleaf state")

    p_log = sub.add_parser("log", help="Show sync history")
    p_log.add_argument("-n", type=int, default=10, help="Number of entries (default: 10)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        out = init_config(args.project, args.paper_dir)
        print(f"Config written to {out}")
        return

    cfg = load_config()

    if args.command == "login":
        login(get_session_dir(cfg))
        return

    paper_dir = get_paper_dir(cfg)

    # Offline commands (no Overleaf session needed)
    if args.command == "diff":
        diff(paper_dir)
        return
    if args.command == "log":
        log(paper_dir, n=args.n)
        return

    # Online commands
    project_id = get_project_id(cfg)
    session = get_session(get_session_dir(cfg))

    if args.command == "status":
        status(session, project_id, paper_dir)
    elif args.command == "pull":
        pull(session, project_id, paper_dir, force=args.force)
    elif args.command == "push":
        csrf = get_csrf(session, project_id)
        push(session, project_id, paper_dir, csrf, force=args.force)
