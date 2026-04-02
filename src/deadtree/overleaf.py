"""Overleaf HTTP API: download, upload, folder management."""

import io
import json
import os
import re
import time
import zipfile
from pathlib import Path

import requests

from .config import IGNORE_PATTERNS, SYNC_EXTENSIONS

BASE_URL = "https://www.overleaf.com"
MAX_ZIP_SIZE = 200 * 1024 * 1024
MAX_FILE_SIZE = 50 * 1024 * 1024


def should_sync(filepath: str) -> bool:
    p = Path(filepath)
    return p.suffix.lower() in SYNC_EXTENSIONS and not any(p.match(pat) for pat in IGNORE_PATTERNS)


def download(session: requests.Session, project_id: str) -> dict[str, bytes]:
    """Download project as zip, return {path: bytes}."""
    r = session.get(f"{BASE_URL}/project/{project_id}/download/zip", stream=True)
    if "login" in r.url:
        raise SystemExit("Session expired. Run: dead-tree login")
    r.raise_for_status()

    chunks, total = [], 0
    for chunk in r.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_ZIP_SIZE:
            raise SystemExit(f"Download exceeds {MAX_ZIP_SIZE // (1024*1024)} MB. Aborting.")
        chunks.append(chunk)

    z = zipfile.ZipFile(io.BytesIO(b"".join(chunks)))
    files = {}
    for info in z.infolist():
        if not should_sync(info.filename) or info.file_size > MAX_FILE_SIZE:
            continue
        if ".." in info.filename.split("/"):
            continue
        files[info.filename] = z.read(info)
    return files


def get_project_tree(session: requests.Session, project_id: str) -> tuple[dict[str, str], str]:
    """Get folder map and root ID via socket.io handshake."""
    r = session.get(f"{BASE_URL}/socket.io/1/?projectId={project_id}")
    r.raise_for_status()
    sid = r.text.strip().split(":")[0]
    session.get(f"{BASE_URL}/socket.io/1/xhr-polling/{sid}")

    for _ in range(3):
        time.sleep(0.5)
        r2 = session.get(f"{BASE_URL}/socket.io/1/xhr-polling/{sid}")
        m = re.search(r'"joinProjectResponse","args":\[(.+)\]\}$', r2.text)
        if m:
            data = json.loads(m.group(1))
            root = data["project"].get("rootFolder", [{}])[0]
            folder_map = {"": root["_id"], ".": root["_id"]}

            def walk(folder, prefix):
                for sub in folder.get("folders", []):
                    p = f"{prefix}{sub['name']}" if not prefix else f"{prefix}/{sub['name']}"
                    folder_map[p] = sub["_id"]
                    walk(sub, p)

            walk(root, "")
            return folder_map, root["_id"]

    raise SystemExit("Could not get project data. Run: dead-tree login")


def upload(session, project_id, csrf, folder_map, root_id, files: dict[str, bytes]) -> int:
    """Upload files to Overleaf. Returns count of successful uploads."""
    # Ensure subdirectories exist
    headers = {"x-csrf-token": csrf, "Content-Type": "application/json"}
    dirs_needed: set[str] = set()
    for rel in files:
        p = Path(rel).parent
        while str(p) not in ("", "."):
            dirs_needed.add(str(p))
            p = p.parent

    for d in sorted(dirs_needed):
        if d not in folder_map:
            parent_id = folder_map.get(str(Path(d).parent), root_id)
            r = session.post(f"{BASE_URL}/project/{project_id}/folder", headers=headers,
                             json={"name": Path(d).name, "parent_folder_id": parent_id})
            folder_map[d] = r.json()["_id"] if r.status_code == 200 else root_id

    uploaded = 0
    for rel, content in files.items():
        target = folder_map.get(str(Path(rel).parent), root_id)
        r = session.post(
            f"{BASE_URL}/project/{project_id}/upload",
            headers={"x-csrf-token": csrf},
            params={"folder_id": target},
            data={"name": os.path.basename(rel)},
            files={"qqfile": (os.path.basename(rel), content, "application/octet-stream")},
        )
        if r.status_code == 200:
            print(f"  uploaded: {rel}")
            uploaded += 1
        else:
            print(f"  FAILED: {rel} ({r.status_code}: {r.text[:200]})")
    return uploaded
