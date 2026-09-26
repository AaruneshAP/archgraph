#!/usr/bin/env python3
"""
Phase 3: Git-diff tracking for the codebase structure graph.
Compares parsed structure graphs between two git revisions and reports what changed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import git

from dotenv import load_dotenv

load_dotenv()

from codebase_graph import build_graph
from narrate_diff import narrate_diff

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

__all__ = ["get_graph_at_revision", "diff_graphs", "narrate_diff"]


def get_graph_at_revision(repo_path: str, rev: str) -> Dict[str, Any]:
    """
    Given a git ref (branch, tag, or commit SHA), extract that revision's full file tree
    into a temporary directory using GitPython (reading commit's tree/blobs directly without
    checking out or mutating the working tree or index), run it through the Phase 1
    parser (`build_graph` from codebase_graph.py), and clean up the temp directory.

    Returns the same {nodes, edges, errors, files_scanned} schema as Phase 1.
    """
    repo_dir = Path(repo_path).resolve()
    repo = git.Repo(repo_dir)

    try:
        commit = repo.commit(rev)
        temp_dir = tempfile.mkdtemp(prefix="git_graph_rev_")
        try:
            temp_root = Path(temp_dir)

            # Extract revision's full file tree from blobs directly
            for item in commit.tree.traverse():
                if item.type == "blob":
                    dest = temp_root / item.path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(item.data_stream.read())

            res = build_graph(temp_root)
            if isinstance(res, tuple):
                graph_data = res[0]
            else:
                graph_data = res

            return graph_data
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    finally:
        repo.close()


def diff_graphs(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure function (no git or file I/O) that compares two graph dicts
    by node id and by (source, target, type) edge tuples.

    Returns:
    {
      "nodes_added": [...],      # full node objects present in new but not old
      "nodes_removed": [...],    # full node objects present in old but not new
      "edges_added": [...],      # full edge objects present in new but not old
      "edges_removed": [...],    # full edge objects present in old but not new
      "summary": {
        "nodes_added": n,
        "nodes_removed": n,
        "edges_added": n,
        "edges_removed": n
      }
    }

    A node that exists in both but changed type or file shows as removed+added.
    """
    old_nodes = old.get("nodes", []) if old else []
    new_nodes = new.get("nodes", []) if new else []

    old_nodes_by_id: Dict[str, Dict[str, Any]] = {}
    for n in old_nodes:
        nid = n.get("id")
        if nid and nid not in old_nodes_by_id:
            old_nodes_by_id[nid] = n

    new_nodes_by_id: Dict[str, Dict[str, Any]] = {}
    for n in new_nodes:
        nid = n.get("id")
        if nid and nid not in new_nodes_by_id:
            new_nodes_by_id[nid] = n

    # Compute nodes_added and nodes_removed
    nodes_added: List[Dict[str, Any]] = []
    seen_added_ids: Set[str] = set()
    for n in new_nodes:
        nid = n.get("id")
        if not nid or nid in seen_added_ids:
            continue
        if nid not in old_nodes_by_id:
            nodes_added.append(n)
            seen_added_ids.add(nid)
        else:
            old_n = old_nodes_by_id[nid]
            if old_n.get("type") != n.get("type") or old_n.get("file") != n.get("file"):
                nodes_added.append(n)
                seen_added_ids.add(nid)

    nodes_removed: List[Dict[str, Any]] = []
    seen_removed_ids: Set[str] = set()
    for n in old_nodes:
        nid = n.get("id")
        if not nid or nid in seen_removed_ids:
            continue
        if nid not in new_nodes_by_id:
            nodes_removed.append(n)
            seen_removed_ids.add(nid)
        else:
            new_n = new_nodes_by_id[nid]
            if n.get("type") != new_n.get("type") or n.get("file") != new_n.get("file"):
                nodes_removed.append(n)
                seen_removed_ids.add(nid)

    # Compute edges_added and edges_removed by (source, target, type) tuples
    old_edges = old.get("edges", []) if old else []
    new_edges = new.get("edges", []) if new else []

    old_edge_keys: Set[Tuple[Any, Any, Any]] = {
        (e.get("source"), e.get("target"), e.get("type")) for e in old_edges
    }
    new_edge_keys: Set[Tuple[Any, Any, Any]] = {
        (e.get("source"), e.get("target"), e.get("type")) for e in new_edges
    }

    edges_added: List[Dict[str, Any]] = []
    seen_added_edge_keys: Set[Tuple[Any, Any, Any]] = set()
    for e in new_edges:
        key = (e.get("source"), e.get("target"), e.get("type"))
        if key not in old_edge_keys and key not in seen_added_edge_keys:
            edges_added.append(e)
            seen_added_edge_keys.add(key)

    edges_removed: List[Dict[str, Any]] = []
    seen_removed_edge_keys: Set[Tuple[Any, Any, Any]] = set()
    for e in old_edges:
        key = (e.get("source"), e.get("target"), e.get("type"))
        if key not in new_edge_keys and key not in seen_removed_edge_keys:
            edges_removed.append(e)
            seen_removed_edge_keys.add(key)

    summary = {
        "nodes_added": len(nodes_added),
        "nodes_removed": len(nodes_removed),
        "edges_added": len(edges_added),
        "edges_removed": len(edges_removed),
    }

    return {
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "edges_added": edges_added,
        "edges_removed": edges_removed,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare parsed codebase structure graphs between two git revisions."
    )
    parser.add_argument(
        "repo_path",
        help="Path to git repository.",
    )
    parser.add_argument(
        "from_rev",
        nargs="?",
        default="HEAD~1",
        help="Source git revision (branch, tag, or commit SHA). Default: HEAD~1",
    )
    parser.add_argument(
        "to_rev",
        nargs="?",
        default="HEAD",
        help="Target git revision (branch, tag, or commit SHA). Default: HEAD",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="diff_graph.json",
        help="Optional path to output JSON file (default: diff_graph.json).",
    )
    parser.add_argument(
        "--narrate",
        action="store_true",
        help="Generate plain-English architecture changelog summary using Groq.",
    )

    args = parser.parse_args()
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path '{args.repo_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        old_graph = get_graph_at_revision(str(repo_path), args.from_rev)
    except Exception as e:
        print(f"Error extracting graph at revision '{args.from_rev}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        new_graph = get_graph_at_revision(str(repo_path), args.to_rev)
    except Exception as e:
        print(f"Error extracting graph at revision '{args.to_rev}': {e}", file=sys.stderr)
        sys.exit(1)

    diff_result = diff_graphs(old_graph, new_graph)

    # Write output JSON
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(diff_result, f, indent=2)

    # Print one-line human summary
    summary = diff_result["summary"]
    print(
        f"{summary['nodes_added']} nodes added, "
        f"{summary['nodes_removed']} removed, "
        f"{summary['edges_added']} edges added, "
        f"{summary['edges_removed']} removed"
    )

    # Optional plain-English narration
    if args.narrate:
        try:
            narration = narrate_diff(diff_result)
            print()
            print(narration)
        except Exception as e:
            print(f"\n[Narration unavailable: {e}]", file=sys.stderr)


if __name__ == "__main__":
    main()
