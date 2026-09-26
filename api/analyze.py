#!/usr/bin/env python3
"""
Phase 5: Vercel Serverless Function for analyzing GitHub repositories into architecture graphs.
Endpoint: POST /api/analyze
Body: { "url": "https://github.com/owner/repo", "narrate": false }
Response: { "mermaid": "...", "stats": { "files": n, "nodes": n, "edges": n }, "narration": str | null }
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from codebase_graph import EXCLUDED_DIRS, build_graph_from_sources
from graph_to_mermaid import (
    count_rendered_edges,
    count_rendered_nodes,
    get_collapse_info,
    graph_to_mermaid,
)
from narrate_diff import narrate_architecture


def parse_github_url(url_str: str) -> Optional[Tuple[str, str]]:
    """
    Extract (owner, repo) from GitHub URL or shorthand.
    Supports:
      https://github.com/owner/repo
      http://github.com/owner/repo.git
      github.com/owner/repo
      owner/repo
    """
    if not url_str or not isinstance(url_str, str):
        return None
    clean = url_str.strip()
    if clean.endswith(".git"):
        clean = clean[:-4]
    clean = clean.rstrip("/")

    # Full URL match
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)", clean, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)

    # Shorthand: owner/repo
    parts = clean.split("/")
    if len(parts) == 2 and all(re.match(r"^[\w.-]+$", p) for p in parts):
        return parts[0], parts[1]

    return None


def fetch_repo_tree(
    owner: str, repo: str, token: Optional[str]
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Tuple[int, str]]]:
    """
    Fetch the recursive file tree for HEAD from GitHub's Git Trees API.
    Returns (tree_items, None) or (None, (status_code, error_message)).
    """
    headers = {"User-Agent": "Codebase-Architecture-Visualizer"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    req = urllib.request.Request(tree_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
            return data.get("tree", []), None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, (404, "Repo not found or private")
        elif e.code in (403, 429):
            rem = e.headers.get("x-ratelimit-remaining", "")
            reset_ts = e.headers.get("x-ratelimit-reset", "")
            if rem == "0" and reset_ts:
                try:
                    mins = max(1, int((int(reset_ts) - time.time()) / 60))
                    return None, (429, f"GitHub rate limit reached, try again in {mins} minutes")
                except Exception:
                    pass
            return None, (429, "GitHub rate limit reached, try again in 60 minutes")
        return None, (e.code, f"GitHub API error: {e.reason}")
    except Exception as e:
        return None, (502, f"Failed to connect to GitHub: {str(e)}")


def fetch_raw_file(
    owner: str, repo: str, path: str, token: Optional[str]
) -> Tuple[str, Optional[str]]:
    """
    Fetch raw file content from raw.githubusercontent.com.
    """
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
    headers = {"User-Agent": "Codebase-Architecture-Visualizer"}
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(raw_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            return path, content
    except Exception:
        return path, None


class handler(BaseHTTPRequestHandler):
    """
    Vercel Serverless Function handler.
    """

    def send_json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path in ("", "/index.html"):
            index_path = PROJECT_ROOT / "index.html"
            if index_path.exists():
                content = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
        self.send_json(200, {"status": "ok", "service": "codebase-architecture-visualizer"})

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            self.send_json(400, {"error": "Missing request body."})
            return

        raw_body = self.rfile.read(content_len).decode("utf-8", errors="replace")
        try:
            req_data = json.loads(raw_body)
        except Exception:
            self.send_json(400, {"error": "Invalid JSON in request body."})
            return

        url_str = req_data.get("url", "")
        should_narrate = bool(req_data.get("narrate", False))

        parsed_repo = parse_github_url(url_str)
        if not parsed_repo:
            self.send_json(
                400,
                {
                    "error": (
                        "Invalid GitHub repository URL. "
                        "Please use format: https://github.com/owner/repo"
                    )
                },
            )
            return

        owner, repo = parsed_repo
        github_token = os.environ.get("GITHUB_TOKEN") or None

        # 1. Fetch file tree
        tree_items, error_info = fetch_repo_tree(owner, repo, github_token)
        if error_info:
            status_code, err_msg = error_info
            self.send_json(status_code, {"error": err_msg})
            return

        # 2. Filter tree to .py files, skipping EXCLUDED_DIRS
        py_paths: List[str] = []
        for item in (tree_items or []):
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if not path.endswith(".py"):
                continue
            parts = path.replace("\\", "/").split("/")
            if any(p in EXCLUDED_DIRS for p in parts):
                continue
            py_paths.append(path)

        if not py_paths:
            self.send_json(400, {"error": "No Python files found in this repo"})
            return

        # 3. Fetch file contents (capped at 500 files for fast serverless execution)
        selected_paths = py_paths[:500]
        sources: Dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(fetch_raw_file, owner, repo, p, github_token)
                for p in selected_paths
            ]
            for f in futures:
                p, content = f.result()
                if content is not None:
                    sources[p] = content

        if not sources:
            self.send_json(
                400,
                {"error": "Failed to retrieve Python files from the repository."},
            )
            return

        # 4. Parse in-memory using Phase 1 parser
        try:
            graph_data, files_scanned, node_count, edge_count, error_count = (
                build_graph_from_sources(sources)
            )
        except Exception as e:
            self.send_json(500, {"error": f"Failed to build codebase graph: {str(e)}"})
            return

        # 5. Convert to Mermaid using Phase 2 renderer
        try:
            mermaid_str = graph_to_mermaid(graph_data)
        except Exception as e:
            self.send_json(500, {"error": f"Failed to render diagram: {str(e)}"})
            return

        rendered_edge_count = count_rendered_edges(mermaid_str)
        rendered_node_count = count_rendered_nodes(mermaid_str)
        collapse_info = get_collapse_info(graph_data)

        # 6. Optional narration using Phase 4 Groq narration
        narration_text: Optional[str] = None
        if should_narrate:
            try:
                narration_text = narrate_architecture(graph_data)
            except Exception:
                narration_text = None

        # 7. Return successful result
        self.send_json(
            200,
            {
                "mermaid": mermaid_str,
                "stats": {
                    "files": files_scanned,
                    "nodes": rendered_node_count,
                    "edges": rendered_edge_count,
                    "raw_nodes": node_count,
                    "collapsed": collapse_info["collapsed"],
                    "collapse_level": collapse_info["level"],
                    "classes_hidden": collapse_info["classes_hidden"],
                    "functions_hidden": collapse_info["functions_hidden"],
                    "banner_text": collapse_info["banner_text"],
                },
                "narration": narration_text,
            },
        )


if __name__ == "__main__":
    from http.server import HTTPServer

    port = 3000
    server = HTTPServer(("localhost", port), handler)
    print(f"API server running at http://localhost:{port}/api/analyze")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
