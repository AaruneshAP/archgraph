#!/usr/bin/env python3
"""
Phase 4: Natural language architecture changelog generation using Groq.
Converts a Phase 3 diff_graphs() output dictionary into a concise plain-English summary.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert software architect analyzing an automated structural code diff.
Your task is to write a plain-English architecture changelog summary (2 to 5 sentences) describing what changed and why it matters structurally.

Guidelines:
1. Write like a terse, insightful pull-request description highlighting structural impacts (e.g., new dependencies, removed couplings, new call paths, component lifecycle changes).
2. Do NOT mechanically restate the JSON (avoid robotic phrasing like "Node X was added, Edge Y was removed").
3. If the diff is large (>15 combined changes in the summary), summarize counts first (e.g., "12 functions added across 3 new modules") rather than listing every symbol.
4. For small diffs (the common case), name the actual symbols and describe the architectural change (e.g., "utils gained a notify() function, now called from main() after the os import was dropped — likely swapping print-based logging for something else.").
5. Output ONLY the 2-5 sentence plain-English paragraph. Do not include markdown bullet lists, headings, or json blocks."""


def format_diff_for_llm(diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a concise, token-efficient representation of the diff
    containing only relevant structural fields (id, type, file, source, target).
    """
    nodes_added = [
        {"id": n.get("id"), "type": n.get("type"), "file": n.get("file")}
        for n in diff.get("nodes_added", [])
    ]
    nodes_removed = [
        {"id": n.get("id"), "type": n.get("type"), "file": n.get("file")}
        for n in diff.get("nodes_removed", [])
    ]
    edges_added = [
        {"source": e.get("source"), "target": e.get("target"), "type": e.get("type")}
        for e in diff.get("edges_added", [])
    ]
    edges_removed = [
        {"source": e.get("source"), "target": e.get("target"), "type": e.get("type")}
        for e in diff.get("edges_removed", [])
    ]
    return {
        "summary": diff.get(
            "summary",
            {
                "nodes_added": len(nodes_added),
                "nodes_removed": len(nodes_removed),
                "edges_added": len(edges_added),
                "edges_removed": len(edges_removed),
            },
        ),
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "edges_added": edges_added,
        "edges_removed": edges_removed,
    }


def narrate_diff(
    diff: Dict[str, Any],
    model: str = "openai/gpt-oss-120b",
    api_key: Optional[str] = None,
) -> str:
    """
    Turn a diff_graphs() output into a plain-English architecture changelog using Groq.

    Args:
        diff: Phase 3 diff dictionary with nodes_added, nodes_removed,
              edges_added, edges_removed, and summary.
        model: Groq model identifier (default: "openai/gpt-oss-120b").
        api_key: Optional Groq API key (defaults to GROQ_API_KEY environment variable).

    Returns:
        A short natural-language summary (2-5 sentences).
        If the diff contains no changes, returns "No structural changes." without calling API.
    """
    nodes_added = diff.get("nodes_added", []) if diff else []
    nodes_removed = diff.get("nodes_removed", []) if diff else []
    edges_added = diff.get("edges_added", []) if diff else []
    edges_removed = diff.get("edges_removed", []) if diff else []

    # Explicit empty-diff check: don't waste API call or require key
    if not nodes_added and not nodes_removed and not edges_added and not edges_removed:
        return "No structural changes."

    resolved_key = api_key or os.environ.get("GROQ_API_KEY")
    if not resolved_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError(
            "The 'groq' package is not installed. Install it with: pip install groq"
        ) from e

    payload = format_diff_for_llm(diff)
    user_prompt = f"Summarize the structural changes in this codebase diff:\n\n{json.dumps(payload, indent=2)}"

    client = Groq(api_key=resolved_key)
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        temperature=0.2,
        max_tokens=256,
    )

    content = chat_completion.choices[0].message.content
    if content:
        return content.strip()

    return "No structural narrative could be generated."


def narrate_architecture(
    graph_data: Dict[str, Any],
    model: str = "openai/gpt-oss-120b",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Generate a concise plain-English architecture overview of a codebase graph using Groq.
    """
    resolved_key = api_key or os.environ.get("GROQ_API_KEY")
    if not resolved_key:
        return None

    try:
        from groq import Groq
    except ImportError:
        return None

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    modules = [n["id"] for n in nodes if n.get("type") == "module"][:15]
    classes = [
        f"{n['name']} (in {n.get('module', '')})"
        for n in nodes
        if n.get("type") == "class"
    ][:15]
    functions = [
        f"{n['name']} (in {n.get('module', '')})"
        for n in nodes
        if n.get("type") == "function"
    ][:15]
    calls = [
        f"{e['source']} -> {e['target']}"
        for e in edges
        if e.get("type") == "calls"
    ][:15]
    inherits = [
        f"{e['source']} extends {e['target']}"
        for e in edges
        if e.get("type") == "inherits"
    ][:10]

    arch_summary = {
        "files_scanned": graph_data.get("files_scanned", 0),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "modules": modules,
        "classes": classes,
        "functions": functions,
        "inheritance": inherits,
        "call_examples": calls,
    }

    arch_system_prompt = (
        "You are an expert software architect analyzing a codebase's structural architecture graph. "
        "Write a concise, plain-English architecture overview (2 to 4 sentences) describing the core modules, "
        "primary classes, and how the components interact. Do not output markdown headers or bullet points; "
        "write a single cohesive paragraph."
    )

    user_prompt = f"Provide an architectural overview for this codebase:\n\n{json.dumps(arch_summary, indent=2)}"

    try:
        client = Groq(api_key=resolved_key)
        resp = client.chat.completions.create(
            messages=[
                {"role": "system", "content": arch_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            temperature=0.2,
            max_tokens=256,
        )
        content = resp.choices[0].message.content
        return content.strip() if content else None
    except Exception as e:
        print(f"[Narration error: {e}]", file=sys.stderr)
        return None
