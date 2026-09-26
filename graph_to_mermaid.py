#!/usr/bin/env python3
"""
Phase 2: Architecture Diagram Renderer
Converts a Phase 1 codebase structure graph JSON into Mermaid flowchart syntax
and a standalone, interactive HTML viewer with zero build step.
Restyled to matching modern 2-column studio layout with fixed right legend sidebar,
rich card nodes with custom type color chips, and clean geometry-styled edges.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def sanitize_mermaid_id(raw_id: str) -> str:
    """
    Sanitize an arbitrary node or entity ID into a safe Mermaid identifier.
    Replaces periods and non-alphanumeric characters with underscores.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", str(raw_id))
    if not sanitized or not sanitized[0].isalpha():
        sanitized = f"node_{sanitized}"
    return sanitized


def make_node_card_html(
    node: Dict[str, Any],
    dropped_functions: int = 0,
    dropped_classes: int = 0,
) -> str:
    """
    Generate an HTML card for a node:
    - Fixed-size (~150-170px wide, 120px tall)
    - 1px neutral border (#232833), background #12161D
    - Small uppercase type label in accent color
    - Bold node name
    - Small muted subtitle (file name for modules, 'extends X' for subclasses, file name/entrypoint for functions)
      When collapsed (>150 nodes), modules/classes that had functions or classes removed display a count badge,
      e.g. "12 functions" or "12 classes, 34 functions".
    Colors: module #E8874A, class #8B6FD1, function #2FA89C
    """
    ntype = node.get("type", "module")
    name = node.get("name", node.get("id", ""))
    file_path = node.get("file", "")
    file_name = Path(file_path).name if file_path else ""

    if ntype == "module":
        type_label = "MODULE"
        color = "#E8874A"
        display_name = name
        if dropped_classes > 0 and dropped_functions > 0:
            cls_str = "1 class" if dropped_classes == 1 else f"{dropped_classes} classes"
            fn_str = "1 function" if dropped_functions == 1 else f"{dropped_functions} functions"
            sub_text = f"{cls_str}, {fn_str}"
        elif dropped_classes > 0:
            sub_text = "1 class" if dropped_classes == 1 else f"{dropped_classes} classes"
        elif dropped_functions > 0:
            fn_badge = "1 function" if dropped_functions == 1 else f"{dropped_functions} functions"
            if file_name and len(file_name) + len(fn_badge) <= 16:
                sub_text = f"{file_name} • {fn_badge}"
            else:
                sub_text = fn_badge
        else:
            sub_text = file_name or "module"

    elif ntype == "class":
        type_label = "CLASS"
        color = "#8B6FD1"
        display_name = name
        bases = node.get("bases", [])
        if dropped_functions > 0:
            fn_badge = "1 function" if dropped_functions == 1 else f"{dropped_functions} functions"
            if bases:
                base_str = bases[0].split(".")[-1]
                if len(base_str) <= 6:
                    sub_text = f"extends {base_str} • {fn_badge}"
                else:
                    sub_text = fn_badge
            else:
                sub_text = fn_badge
        else:
            if bases:
                base_str = bases[0].split(".")[-1]
                sub_text = f"extends {base_str}"
            else:
                sub_text = file_name or "class"

    elif ntype == "function":
        type_label = "FUNCTION"
        color = "#2FA89C"
        display_name = f"{name}()" if not name.endswith("()") else name
        if name == "main":
            sub_text = "entrypoint"
        else:
            sub_text = file_name or "function"

    else:
        type_label = "UNKNOWN"
        color = "#8B93A3"
        display_name = name
        sub_text = file_name

    escaped_sub = html.escape(sub_text)
    return (
        f"<div class='node-card' style='border-left:4px solid {color};'>"
        f"<div class='node-type' style='color:{color};'>{type_label}</div>"
        f"<div class='node-name'>{display_name}</div>"
        f"<div class='node-sub' title='{escaped_sub}'>{escaped_sub}</div>"
        f"</div>"
    )


def graph_to_mermaid(
    graph_data: Dict[str, Any],
    include_calls: Optional[bool] = None,
    max_nodes_for_calls: int = 150,
    collapse_functions: Optional[bool] = None,
) -> str:
    """
    Pure function: converts a codebase graph dictionary into Mermaid flowchart syntax (graph TD).
    
    Level-of-detail collapsing:
    - Tier 1: If total nodes > max_nodes_for_calls (default: 150), drop function-type nodes,
      showing only module and class nodes.
    - Tier 2: If module + class count is STILL > max_nodes_for_calls, also drop class-type nodes,
      showing only module nodes with badge e.g. '12 classes, 34 functions'.
    """
    raw_nodes: List[Dict[str, Any]] = graph_data.get("nodes", [])
    raw_edges: List[Dict[str, Any]] = graph_data.get("edges", [])

    total_nodes = len(raw_nodes)
    if include_calls is None:
        allow_calls = total_nodes <= max_nodes_for_calls
    else:
        allow_calls = bool(include_calls)

    mod_nodes = [n for n in raw_nodes if n.get("type") == "module"]
    cls_nodes_list = [n for n in raw_nodes if n.get("type") == "class"]
    func_nodes_list = [n for n in raw_nodes if n.get("type") == "function"]

    mod_class_count = len(mod_nodes) + len(cls_nodes_list)

    if collapse_functions is False:
        collapse_level = "none"
    elif collapse_functions is True:
        if mod_class_count > max_nodes_for_calls:
            collapse_level = "functions-and-classes-hidden"
        else:
            collapse_level = "functions-hidden"
    else:
        if total_nodes <= max_nodes_for_calls:
            collapse_level = "none"
        elif mod_class_count <= max_nodes_for_calls:
            collapse_level = "functions-hidden"
        else:
            collapse_level = "functions-and-classes-hidden"

    dropped_funcs_per_parent: Dict[str, int] = defaultdict(int)
    dropped_classes_per_parent: Dict[str, int] = defaultdict(int)

    cls_nodes = {n["id"]: n for n in cls_nodes_list}
    func_nodes = {n["id"]: n for n in func_nodes_list}
    mod_ids = {n["id"] for n in mod_nodes}
    mod_by_file = {n.get("file"): n["id"] for n in mod_nodes if n.get("file")}

    if collapse_level == "functions-hidden":
        nodes_to_render = [n for n in raw_nodes if n.get("type") in ("module", "class")]

        # Attribute dropped functions to parent module or class:
        accounted_funcs: Set[str] = set()
        for e in raw_edges:
            if e.get("type") == "contains":
                src = e.get("source", "")
                tgt = e.get("target", "")
                if tgt in func_nodes:
                    dropped_funcs_per_parent[src] += 1
                    accounted_funcs.add(tgt)

        for fn_id, fn in func_nodes.items():
            if fn_id in accounted_funcs:
                continue
            mod = fn.get("module")
            if mod:
                dropped_funcs_per_parent[mod] += 1
                continue
            if "." in fn_id:
                parent_prefix = fn_id.rsplit(".", 1)[0]
                dropped_funcs_per_parent[parent_prefix] += 1
            else:
                fn_file = fn.get("file")
                matched = False
                if fn_file and fn_file in mod_by_file:
                    dropped_funcs_per_parent[mod_by_file[fn_file]] += 1
                    matched = True
                if not matched and len(mod_ids) == 1:
                    dropped_funcs_per_parent[next(iter(mod_ids))] += 1

    elif collapse_level == "functions-and-classes-hidden":
        nodes_to_render = list(mod_nodes)

        # 1. Attribute dropped classes to modules
        accounted_classes: Set[str] = set()
        for e in raw_edges:
            if e.get("type") == "contains":
                src = e.get("source", "")
                tgt = e.get("target", "")
                if tgt in cls_nodes and src in mod_ids:
                    dropped_classes_per_parent[src] += 1
                    accounted_classes.add(tgt)

        for c_id, c in cls_nodes.items():
            if c_id in accounted_classes:
                continue
            mod = c.get("module")
            if mod and mod in mod_ids:
                dropped_classes_per_parent[mod] += 1
            elif c.get("file") and c["file"] in mod_by_file:
                dropped_classes_per_parent[mod_by_file[c["file"]]] += 1
            elif "." in c_id:
                prefix = c_id.rsplit(".", 1)[0]
                if prefix in mod_ids:
                    dropped_classes_per_parent[prefix] += 1
                else:
                    cand = None
                    for m in mod_ids:
                        if c_id.startswith(m + "."):
                            if cand is None or len(m) > len(cand):
                                cand = m
                    if cand:
                        dropped_classes_per_parent[cand] += 1
                    elif len(mod_ids) == 1:
                        dropped_classes_per_parent[next(iter(mod_ids))] += 1
            elif len(mod_ids) == 1:
                dropped_classes_per_parent[next(iter(mod_ids))] += 1

        # 2. Attribute dropped functions to modules (either directly or via parent class)
        class_to_mod: Dict[str, str] = {}
        for c_id, c in cls_nodes.items():
            mod = c.get("module")
            if mod and mod in mod_ids:
                class_to_mod[c_id] = mod
            elif c.get("file") and c["file"] in mod_by_file:
                class_to_mod[c_id] = mod_by_file[c["file"]]
            elif "." in c_id:
                prefix = c_id.rsplit(".", 1)[0]
                if prefix in mod_ids:
                    class_to_mod[c_id] = prefix

        accounted_funcs_l2: Set[str] = set()
        for e in raw_edges:
            if e.get("type") == "contains":
                src = e.get("source", "")
                tgt = e.get("target", "")
                if tgt in func_nodes:
                    if src in mod_ids:
                        dropped_funcs_per_parent[src] += 1
                        accounted_funcs_l2.add(tgt)
                    elif src in class_to_mod:
                        dropped_funcs_per_parent[class_to_mod[src]] += 1
                        accounted_funcs_l2.add(tgt)

        for fn_id, fn in func_nodes.items():
            if fn_id in accounted_funcs_l2:
                continue
            mod = fn.get("module")
            if mod and mod in mod_ids:
                dropped_funcs_per_parent[mod] += 1
            elif fn.get("file") and fn["file"] in mod_by_file:
                dropped_funcs_per_parent[mod_by_file[fn["file"]]] += 1
            elif "." in fn_id:
                prefix = fn_id.rsplit(".", 1)[0]
                if prefix in mod_ids:
                    dropped_funcs_per_parent[prefix] += 1
                elif prefix in class_to_mod:
                    dropped_funcs_per_parent[class_to_mod[prefix]] += 1
                else:
                    cand = None
                    for m in mod_ids:
                        if fn_id.startswith(m + "."):
                            if cand is None or len(m) > len(cand):
                                cand = m
                    if cand:
                        dropped_funcs_per_parent[cand] += 1
                    elif len(mod_ids) == 1:
                        dropped_funcs_per_parent[next(iter(mod_ids))] += 1
            elif len(mod_ids) == 1:
                dropped_funcs_per_parent[next(iter(mod_ids))] += 1

    else:
        nodes_to_render = list(raw_nodes)

    # Index rendered nodes for fast resolution
    nodes_by_id: Dict[str, Dict[str, Any]] = {}
    classes_by_name: Dict[str, Dict[str, Any]] = {}
    modules_by_name: Dict[str, Dict[str, Any]] = {}
    funcs_by_name: Dict[str, Dict[str, Any]] = {}

    for n in nodes_to_render:
        nid = n.get("id")
        if not nid:
            continue
        nodes_by_id[nid] = n
        ntype = n.get("type")
        name = n.get("name")
        if name:
            if ntype == "class":
                classes_by_name[name] = n
            elif ntype == "module":
                modules_by_name[name] = n
            elif ntype == "function":
                funcs_by_name[name] = n

    # Node safe ID mapping
    node_id_to_safe: Dict[str, str] = {}
    for nid in nodes_by_id:
        node_id_to_safe[nid] = sanitize_mermaid_id(nid)

    # Helper to resolve external or shorthand references to known node IDs
    def resolve_target_node_id(target_ref: str, edge_type: str, edge: Dict[str, Any]) -> str:
        # For imports: check edge's module attribute or target module first
        if edge_type == "imports":
            mod = edge.get("module")
            if mod:
                if mod in nodes_by_id:
                    return mod
                if mod in modules_by_name:
                    return modules_by_name[mod]["id"]
            if target_ref in modules_by_name:
                return modules_by_name[target_ref]["id"]
            if "." in target_ref:
                mod_part = target_ref.split(".")[0]
                if mod_part in modules_by_name:
                    return modules_by_name[mod_part]["id"]

        if target_ref in nodes_by_id:
            return target_ref

        # For inherits: check class name lookup
        if edge_type == "inherits":
            if target_ref in classes_by_name:
                cand = classes_by_name[target_ref]["id"]
                if cand in nodes_by_id:
                    return cand
            if "." in target_ref:
                short = target_ref.split(".")[-1]
                if short in classes_by_name:
                    cand = classes_by_name[short]["id"]
                    if cand in nodes_by_id:
                        return cand

        # For calls:
        if edge_type == "calls":
            if target_ref in funcs_by_name:
                cand = funcs_by_name[target_ref]["id"]
                if cand in nodes_by_id:
                    return cand
            if target_ref in classes_by_name:
                cand = classes_by_name[target_ref]["id"]
                if cand in nodes_by_id:
                    return cand
            if target_ref.startswith("self."):
                method_name = target_ref[5:]
                caller_qual = edge.get("caller_qualname", "")
                if "." in caller_qual:
                    caller_class = caller_qual.split(".")[0]
                    cls_node = classes_by_name.get(caller_class)
                    if cls_node:
                        for base in cls_node.get("bases", []):
                            base_node = classes_by_name.get(base)
                            if base_node and method_name in base_node.get("methods", []):
                                cand = base_node["id"]
                                if cand in nodes_by_id:
                                    return cand
                        cand = cls_node["id"]
                        if cand in nodes_by_id:
                            return cand
            if "." in target_ref:
                parts = target_ref.split(".")
                mod_cand = ".".join(parts[:-1])
                fn_cand = parts[-1]
                full_id = f"{mod_cand}.{fn_cand}"
                if full_id in nodes_by_id:
                    return full_id
                if fn_cand in funcs_by_name:
                    cand = funcs_by_name[fn_cand]["id"]
                    if cand in nodes_by_id:
                        return cand

        # Fallback to module ONLY when collapse is active and target_ref class/function was dropped
        if collapse_level == "functions-and-classes-hidden":
            if target_ref in cls_nodes:
                c_mod = cls_nodes[target_ref].get("module")
                if c_mod and c_mod in nodes_by_id:
                    return c_mod
            if target_ref in func_nodes:
                f_mod = func_nodes[target_ref].get("module")
                if f_mod and f_mod in nodes_by_id:
                    return f_mod
            if "." in target_ref:
                mod_part = target_ref.split(".")[0]
                if mod_part in nodes_by_id:
                    return mod_part

        return target_ref

    def resolve_source_node_id(source_ref: str, edge_type: str, edge: Dict[str, Any]) -> str:
        if source_ref in nodes_by_id:
            return source_ref

        if edge_type == "calls":
            caller_mod = edge.get("caller_module", "")
            caller_id = edge.get("caller_id", "")
            if caller_id in nodes_by_id:
                return caller_id
            if caller_mod and f"{caller_mod}.{source_ref}" in nodes_by_id:
                return f"{caller_mod}.{source_ref}"
            if "." in source_ref:
                class_name = source_ref.split(".")[0]
                if caller_mod and f"{caller_mod}.{class_name}" in nodes_by_id:
                    return f"{caller_mod}.{class_name}"
                if class_name in classes_by_name:
                    cand = classes_by_name[class_name]["id"]
                    if cand in nodes_by_id:
                        return cand
            if source_ref in funcs_by_name:
                cand = funcs_by_name[source_ref]["id"]
                if cand in nodes_by_id:
                    return cand

            # Fallback to module ONLY if the class or function was dropped (Tier 2 collapse active)
            if collapse_level == "functions-and-classes-hidden":
                if caller_mod and caller_mod in nodes_by_id:
                    return caller_mod
                if source_ref in cls_nodes:
                    c_mod = cls_nodes[source_ref].get("module")
                    if c_mod and c_mod in nodes_by_id:
                        return c_mod
                if source_ref in func_nodes:
                    f_mod = func_nodes[source_ref].get("module")
                    if f_mod and f_mod in nodes_by_id:
                        return f_mod

        return source_ref

    # Deduplicate edges: collapse repeated (source, target, type) triples
    deduped_edges: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for e in raw_edges:
        etype = e.get("type", "")
        if etype == "calls" and not allow_calls:
            continue

        raw_src = e.get("source", "")
        raw_tgt = e.get("target", "")

        src_id = resolve_source_node_id(raw_src, etype, e)
        tgt_id = resolve_target_node_id(raw_tgt, etype, e)

        if not src_id or not tgt_id:
            continue

        # Both source and target must be known rendered nodes
        if src_id not in nodes_by_id or tgt_id not in nodes_by_id:
            continue

        # Prevent self-edges when child nodes resolve to parent module
        if src_id == tgt_id:
            continue

        edge_key = (src_id, tgt_id, etype)
        if edge_key not in deduped_edges:
            deduped_edges[edge_key] = {
                "source": src_id,
                "target": tgt_id,
                "type": etype,
            }

    # Build Mermaid syntax lines
    lines: List[str] = [
        "%%{init: {'flowchart': {'defaultRenderer': 'elk', 'nodeSpacing': 30, 'rankSpacing': 40}, 'maxTextSize': 2000000}}%%",
        "graph TD",
    ]

    lines.append("    %% Nodes")
    if collapse_level == "functions-hidden":
        fn_count = len(func_nodes_list)
        lines.append(
            f"    %% Note: Showing modules and classes only — {fn_count} functions hidden (repo exceeds {max_nodes_for_calls} nodes)"
        )
    elif collapse_level == "functions-and-classes-hidden":
        fn_count = len(func_nodes_list)
        cls_count = len(cls_nodes_list)
        lines.append(
            f"    %% Note: Showing modules only — {cls_count} classes and {fn_count} functions hidden (repo exceeds {max_nodes_for_calls} nodes)"
        )

    for n in nodes_to_render:
        nid = n["id"]
        safe_id = node_id_to_safe[nid]
        dropped_fn_count = dropped_funcs_per_parent.get(nid, 0)
        dropped_cls_count = dropped_classes_per_parent.get(nid, 0)
        card_content = make_node_card_html(
            n,
            dropped_functions=dropped_fn_count,
            dropped_classes=dropped_cls_count,
        )
        lines.append(f'    {safe_id}["{card_content}"]')

    # Format edges (no inline text labels)
    # - contains: solid with arrowhead (-->)
    # - inherits: dashed WITHOUT arrowhead (-.-)
    # - imports: dotted WITHOUT arrowhead (-.-)
    # - calls: thin solid with arrowhead (-->) at ~55% opacity
    lines.append("")
    lines.append("    %% Edges")

    edge_index = 0
    contains_indices: List[int] = []
    inherits_indices: List[int] = []
    imports_indices: List[int] = []
    calls_indices: List[int] = []

    edge_types_order = ["contains", "inherits", "imports", "calls"]
    for current_type in edge_types_order:
        type_edges = [e for e in deduped_edges.values() if e["type"] == current_type]
        if not type_edges:
            continue

        lines.append(f"    %% {current_type.capitalize()} Edges")
        for e in type_edges:
            src_safe = node_id_to_safe[e["source"]]
            tgt_safe = node_id_to_safe[e["target"]]

            if current_type == "contains":
                lines.append(f"    {src_safe} --> {tgt_safe}")
                contains_indices.append(edge_index)
            elif current_type == "inherits":
                lines.append(f"    {src_safe} -.- {tgt_safe}")
                inherits_indices.append(edge_index)
            elif current_type == "imports":
                lines.append(f"    {src_safe} -.- {tgt_safe}")
                imports_indices.append(edge_index)
            elif current_type == "calls":
                lines.append(f"    {src_safe} --> {tgt_safe}")
                calls_indices.append(edge_index)
            else:
                lines.append(f"    {src_safe} --> {tgt_safe}")

            edge_index += 1

    # CSS class definitions and styling
    lines.append("")
    lines.append("    %% Node Base Styling")
    lines.append(
        "    classDef default fill:#12161D,stroke:#232833,stroke-width:1px,color:#F2F1ED;"
    )

    # Edge styling by type via linkStyle
    lines.append("")
    lines.append("    %% Edge Styling by Type")
    if contains_indices:
        lines.append(
            f"    linkStyle {','.join(map(str, contains_indices))} stroke:#414957,stroke-width:1.5px;"
        )
    if inherits_indices:
        lines.append(
            f"    linkStyle {','.join(map(str, inherits_indices))} stroke:#4A5568,stroke-width:1.5px,stroke-dasharray:7 5;"
        )
    if imports_indices:
        lines.append(
            f"    linkStyle {','.join(map(str, imports_indices))} stroke:#4A5568,stroke-width:1.5px,stroke-dasharray:1 5;"
        )
    if calls_indices:
        lines.append(
            f"    linkStyle {','.join(map(str, calls_indices))} stroke:#414957,stroke-width:1px,opacity:0.55;"
        )

    return "\n".join(lines)


def count_rendered_nodes(mermaid_str: str) -> int:
    """
    Count the number of actual node definitions rendered in a Mermaid flowchart string.
    Only counts lines in the '%% Nodes' section matching node definition syntax (id["..."]).
    """
    count = 0
    in_nodes_section = False
    for line in mermaid_str.splitlines():
        stripped = line.strip()
        if stripped == "%% Nodes":
            in_nodes_section = True
            continue
        if in_nodes_section:
            if stripped.startswith("%%") and not stripped.startswith("%% Note:"):
                break
            if stripped.startswith("classDef") or stripped.startswith("linkStyle"):
                break
            if '["' in stripped and stripped.endswith('"]'):
                count += 1
    return count


def count_rendered_edges(mermaid_str: str) -> int:
    """
    Count the number of actual edge statements rendered in a Mermaid flowchart string.
    Only counts lines matching edge syntax (--> or -.-) representing connections.
    """
    count = 0
    in_edges_section = False
    for line in mermaid_str.splitlines():
        stripped = line.strip()
        if stripped == "%% Edges":
            in_edges_section = True
            continue
        if in_edges_section:
            if (
                stripped.startswith("%% Node Base Styling")
                or stripped.startswith("classDef")
                or stripped.startswith("linkStyle")
            ):
                break
            if (" --> " in stripped or " -.- " in stripped) and not stripped.startswith("%%"):
                count += 1
    return count


def get_collapse_info(
    graph_data: Dict[str, Any],
    max_nodes: int = 150,
    collapse_functions: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Return metadata regarding level-of-detail collapsing for a graph.
    Levels:
      - 'none': total_nodes <= max_nodes
      - 'functions-hidden': total_nodes > max_nodes, but module+class <= max_nodes
      - 'functions-and-classes-hidden': module+class > max_nodes, so only modules rendered
    """
    raw_nodes = graph_data.get("nodes", []) if graph_data else []
    total_nodes = len(raw_nodes)

    mod_count = sum(1 for n in raw_nodes if n.get("type") == "module")
    cls_count = sum(1 for n in raw_nodes if n.get("type") == "class")
    fn_count = sum(1 for n in raw_nodes if n.get("type") == "function")

    mod_class_count = mod_count + cls_count

    if collapse_functions is False:
        level = "none"
    elif collapse_functions is True:
        level = "functions-and-classes-hidden" if mod_class_count > max_nodes else "functions-hidden"
    else:
        if total_nodes <= max_nodes:
            level = "none"
        elif mod_class_count <= max_nodes:
            level = "functions-hidden"
        else:
            level = "functions-and-classes-hidden"

    if level == "none":
        return {
            "collapsed": False,
            "level": "none",
            "total_nodes": total_nodes,
            "rendered_nodes": total_nodes,
            "functions_hidden": 0,
            "classes_hidden": 0,
            "banner_text": "",
        }
    elif level == "functions-hidden":
        fn_text = "1 function" if fn_count == 1 else f"{fn_count} functions"
        return {
            "collapsed": True,
            "level": "functions-hidden",
            "total_nodes": total_nodes,
            "rendered_nodes": mod_class_count,
            "functions_hidden": fn_count,
            "classes_hidden": 0,
            "banner_text": f"Showing modules and classes only — {fn_text} hidden (repo exceeds {max_nodes} nodes)",
        }
    else:  # "functions-and-classes-hidden"
        cls_text = "1 class" if cls_count == 1 else f"{cls_count} classes"
        fn_text = "1 function" if fn_count == 1 else f"{fn_count} functions"
        return {
            "collapsed": True,
            "level": "functions-and-classes-hidden",
            "total_nodes": total_nodes,
            "rendered_nodes": mod_count,
            "functions_hidden": fn_count,
            "classes_hidden": cls_count,
            "banner_text": f"Showing modules only — {cls_text} and {fn_text} hidden (repo exceeds {max_nodes} nodes)",
        }


def generate_html_viewer(
    mermaid_code: str,
    graph_data: Optional[Dict[str, Any]] = None,
    title: str = "Architecture Diagram",
) -> str:
    """
    Generate a standalone HTML viewer matching the 2-column studio layout:
    - Main diagram area with title, breadcrumbs, 2px #3B82C4 accent rule, and stats row
    - Fixed 300px right sidebar legend with colored chips and line styles
    - Custom geometry arrowhead markers and transparent node wrappers around cards
    - Zero build step, runs in any browser.
    """
    files_scanned = graph_data.get("files_scanned", 0) if graph_data else 0
    if graph_data:
        collapse_info = get_collapse_info(graph_data)
        nodes_count = count_rendered_nodes(mermaid_code)
        edges_count = count_rendered_edges(mermaid_code)
    else:
        collapse_info = {"collapsed": False, "functions_hidden": 0, "classes_hidden": 0, "banner_text": ""}
        nodes_count = count_rendered_nodes(mermaid_code)
        edges_count = count_rendered_edges(mermaid_code)

    collapse_banner_html = ""
    if collapse_info.get("collapsed") and collapse_info.get("banner_text"):
        banner_msg = html.escape(collapse_info["banner_text"])
        collapse_banner_html = f"""
      <div class="collapse-banner" style="position: absolute; top: 14px; left: 50%; transform: translateX(-50%); z-index: 45; display: flex; align-items: center; gap: 8px; background: rgba(18, 22, 29, 0.94); border: 1px solid #3B82C4; border-radius: 20px; padding: 6px 16px; font-size: 12px; font-weight: 500; color: #F2F1ED; pointer-events: none; white-space: nowrap;">
        <span style="width: 7px; height: 7px; border-radius: 50%; background: #3B82C4; flex-shrink: 0; box-shadow: 0 0 8px #3B82C4;"></span>
        <span>{banner_msg}</span>
      </div>
"""

    escaped_mermaid = html.escape(mermaid_code)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: #0A0D12;
      color: #F2F1ED;
      font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      display: flex;
    }}

    /* Main Column */
    .main-column {{
      flex-grow: 1;
      display: flex;
      flex-direction: column;
      padding: 28px 36px;
      overflow: hidden;
      position: relative;
    }}

    /* Header */
    .header-section {{
      flex-shrink: 0;
    }}

    .title-row {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
    }}

    h1.app-title {{
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #F2F1ED;
    }}

    .breadcrumb {{
      margin-top: 6px;
      font-size: 13px;
      color: #8B93A3;
    }}

    .accent-rule {{
      margin-top: 16px;
      height: 2px;
      width: 100%;
      background: #3B82C4;
    }}

    .controls-row {{
      margin-top: 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .stats-group {{
      display: flex;
      gap: 24px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 13px;
      color: #8B93A3;
    }}

    .stats-group .stat-num {{
      color: #3B82C4;
      font-weight: 600;
    }}

    .btn-group {{
      display: flex;
      gap: 10px;
    }}

    .btn-outline {{
      font-family: 'IBM Plex Sans', sans-serif;
      font-weight: 500;
      font-size: 13px;
      padding: 8px 16px;
      border-radius: 6px;
      border: 1px solid #232833;
      background: transparent;
      color: #F2F1ED;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .btn-outline:hover {{
      background: rgba(255, 255, 255, 0.05);
      border-color: #3B82C4;
    }}

    .btn-primary {{
      font-family: 'IBM Plex Sans', sans-serif;
      font-weight: 600;
      font-size: 13px;
      padding: 8px 18px;
      border-radius: 6px;
      border: none;
      background: #3B82C4;
      color: #FFFFFF;
      cursor: pointer;
      transition: background 0.15s ease;
    }}

    .btn-primary:hover {{
      background: #2f6ea8;
    }}

    /* Canvas / Viewport */
    .canvas-viewport {{
      flex-grow: 1;
      position: relative;
      margin-top: 18px;
      overflow: hidden;
      cursor: grab;
      user-select: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .canvas-viewport:active {{
      cursor: grabbing;
    }}

    #diagram-wrapper {{
      transform-origin: center center;
      transition: transform 0.05s linear;
      display: inline-block;
      padding: 40px;
    }}

    /* Card styling inside node labels */
    .node-card {{
      width: 160px;
      height: 80px;
      box-sizing: border-box;
      border: 1px solid #232833;
      border-radius: 8px;
      background: #12161D;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      padding: 8px 12px;
      gap: 3px;
      font-family: 'IBM Plex Sans', sans-serif;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }}

    .node-type {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .node-name {{
      font-size: 13px;
      font-weight: 600;
      color: #F2F1ED;
      text-align: left;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 132px;
    }}

    .node-sub {{
      font-size: 10px;
      color: #8B93A3;
      text-align: left;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 132px;
    }}

    /* Hide default Mermaid rect/polygon wrappers around node cards */
    .node rect, .node polygon, .node path.label-container {{
      fill: transparent !important;
      stroke: transparent !important;
    }}

    /* Edge Paths styling */
    path.flowchart-link {{
      stroke: #414957 !important;
      stroke-width: 1.5px !important;
    }}

    /* Floating Zoom Controls */
    .zoom-toolbar {{
      position: absolute;
      bottom: 24px;
      left: 24px;
      display: flex;
      gap: 6px;
      background: #12161D;
      border: 1px solid #232833;
      border-radius: 8px;
      padding: 5px;
      z-index: 40;
    }}

    .zoom-btn {{
      width: 32px;
      height: 32px;
      border-radius: 4px;
      background: transparent;
      border: none;
      color: #F2F1ED;
      font-size: 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s ease;
    }}

    .zoom-btn:hover {{
      background: rgba(255, 255, 255, 0.08);
    }}

    /* Right Sidebar Panel */
    .sidebar-panel {{
      width: 300px;
      flex-shrink: 0;
      box-sizing: border-box;
      background: #10141A;
      border-left: 1px solid #232833;
      padding: 32px 28px;
      display: flex;
      flex-direction: column;
    }}

    .legend-heading {{
      font-size: 16px;
      font-weight: 700;
      color: #F2F1ED;
    }}

    .legend-list {{
      margin-top: 22px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}

    .legend-entry {{
      display: flex;
      gap: 12px;
      align-items: flex-start;
    }}

    .swatch-module {{
      width: 24px;
      height: 24px;
      flex-shrink: 0;
      border-radius: 6px;
      background: #E8874A;
    }}

    .swatch-class {{
      width: 24px;
      height: 24px;
      flex-shrink: 0;
      border-radius: 6px;
      background: #8B6FD1;
    }}

    .swatch-func {{
      width: 24px;
      height: 24px;
      flex-shrink: 0;
      border-radius: 6px;
      background: #2FA89C;
    }}

    .entry-label {{
      font-size: 13px;
      font-weight: 600;
      color: #F2F1ED;
    }}

    .entry-desc {{
      font-size: 12px;
      color: #8B93A3;
      line-height: 1.4;
    }}

    .legend-divider {{
      height: 1px;
      background: #232833;
      margin: 4px 0;
    }}

    .edge-entry {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}

    .line-swatch-contains {{
      width: 24px;
      flex-shrink: 0;
      border-top: 1.5px solid #414957;
    }}

    .line-swatch-inherits {{
      width: 24px;
      flex-shrink: 0;
      border-top: 1.5px dashed #4A5568;
    }}

    .line-swatch-imports {{
      width: 24px;
      flex-shrink: 0;
      border-top: 1.5px dotted #4A5568;
    }}

    .line-swatch-calls {{
      width: 24px;
      flex-shrink: 0;
      border-top: 1px solid #414957;
      opacity: 0.55;
    }}

    .edge-label {{
      font-size: 12px;
      color: #C9CDD6;
    }}

    .sidebar-spacer {{
      flex-grow: 1;
    }}

    .pinned-caption {{
      font-size: 11px;
      font-style: italic;
      color: #6B7280;
      line-height: 1.5;
    }}

    /* Modal for Mermaid Source */
    .modal-backdrop {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}

    .modal-backdrop.open {{
      display: flex;
    }}

    .modal-box {{
      background: #12161D;
      border: 1px solid #232833;
      border-radius: 12px;
      width: 100%;
      max-width: 820px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    }}

    .modal-head {{
      padding: 16px 20px;
      border-bottom: 1px solid #232833;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .modal-head h3 {{
      font-size: 15px;
      font-weight: 600;
      color: #F2F1ED;
    }}

    .modal-content {{
      padding: 20px;
      overflow-y: auto;
    }}

    pre.raw-code {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 12px;
      background: #0A0D12;
      padding: 16px;
      border-radius: 6px;
      border: 1px solid #232833;
      color: #38bdf8;
      overflow-x: auto;
      white-space: pre;
    }}

    #toast {{
      position: fixed;
      top: 24px;
      right: 24px;
      background: #3B82C4;
      color: #FFFFFF;
      padding: 10px 18px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      z-index: 2000;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s ease;
      transform: translateY(-8px);
    }}

    #toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
  </style>
</head>
<body>

  <!-- Main Column -->
  <div class="main-column">

    <!-- Header -->
    <div class="header-section">
      <div class="title-row">
        <h1 class="app-title">{html.escape(title)}</h1>
      </div>
      <div class="breadcrumb">ast parse › graph build › mermaid render</div>
      <div class="accent-rule"></div>

      <div class="controls-row">
        <div class="stats-group">
          <span><span class="stat-num">{files_scanned}</span>&nbsp;files</span>
          <span><span class="stat-num">{nodes_count}</span>&nbsp;nodes</span>
          <span><span class="stat-num">{edges_count}</span>&nbsp;edges</span>
        </div>

        <div class="btn-group">
          <button class="btn-outline" id="btn-show-source">View source</button>
          <button class="btn-outline" id="btn-copy-mermaid">Copy Mermaid</button>
          <button class="btn-primary" id="btn-export-svg">Export SVG</button>
        </div>
      </div>
    </div>

    <!-- Canvas Viewport -->
    <div class="canvas-viewport" id="canvas-viewport">
{collapse_banner_html}
      <div id="diagram-wrapper">
        <pre class="mermaid" id="mermaid-root">
{escaped_mermaid}
        </pre>
      </div>

      <!-- Zoom Controls -->
      <div class="zoom-toolbar">
        <button class="zoom-btn" id="zoom-in" title="Zoom In">+</button>
        <button class="zoom-btn" id="zoom-out" title="Zoom Out">−</button>
        <button class="zoom-btn" id="zoom-reset" title="Reset View">⊙</button>
      </div>
    </div>
  </div>

  <!-- Right Sidebar Panel -->
  <div class="sidebar-panel">
    <div class="legend-heading">Legend</div>

    <div class="legend-list">
      <div class="legend-entry">
        <span class="swatch-module"></span>
        <div>
          <div class="entry-label">Module</div>
          <div class="entry-desc">One node per parsed .py file</div>
        </div>
      </div>

      <div class="legend-entry">
        <span class="swatch-class"></span>
        <div>
          <div class="entry-label">Class</div>
          <div class="entry-desc">Definition; inherits shown separately</div>
        </div>
      </div>

      <div class="legend-entry">
        <span class="swatch-func"></span>
        <div>
          <div class="entry-label">Function</div>
          <div class="entry-desc">Top-level function or class method</div>
        </div>
      </div>

      <div class="legend-divider"></div>

      <div class="edge-entry">
        <span class="line-swatch-contains"></span>
        <div class="edge-label">Contains</div>
      </div>

      <div class="edge-entry">
        <span class="line-swatch-inherits"></span>
        <div class="edge-label">Inherits</div>
      </div>

      <div class="edge-entry">
        <span class="line-swatch-imports"></span>
        <div class="edge-label">Imports</div>
      </div>

      <div class="edge-entry">
        <span class="line-swatch-calls"></span>
        <div class="edge-label">Calls</div>
      </div>
    </div>

    <div class="sidebar-spacer"></div>
    <div class="pinned-caption">Unresolved calls (builtins, instance vars) are dropped, not guessed.</div>
  </div>

  <!-- Source Code Modal -->
  <div class="modal-backdrop" id="source-modal">
    <div class="modal-box">
      <div class="modal-head">
        <h3>Mermaid Flowchart Syntax</h3>
        <button class="btn-outline" id="btn-close-source">✕ Close</button>
      </div>
      <div class="modal-content">
        <pre class="raw-code">{escaped_mermaid}</pre>
      </div>
    </div>
  </div>

  <div id="toast">Copied to clipboard!</div>

  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'dark',
      securityLevel: 'loose',
      maxTextSize: 2000000,
      maxEdges: 20000,
      flowchart: {{
        defaultRenderer: 'elk',
        nodeSpacing: 35,
        rankSpacing: 45,
        useMaxWidth: false,
        htmlLabels: true
      }}
    }});

    // Inject custom arrowhead marker and enforce edge geometries post-render
    function postProcessSvg() {{
      const svg = document.querySelector('#diagram-wrapper svg');
      if (!svg) return;

      // Ensure defs and marker exist
      let defs = svg.querySelector('defs');
      if (!defs) {{
        defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        svg.insertBefore(defs, svg.firstChild);
      }}

      // Custom sleek arrowhead marker matching #414957
      let marker = svg.querySelector('#proper-arrow');
      if (!marker) {{
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'proper-arrow');
        marker.setAttribute('viewBox', '0 0 10 10');
        marker.setAttribute('refX', '8');
        marker.setAttribute('refY', '5');
        marker.setAttribute('markerWidth', '7');
        marker.setAttribute('markerHeight', '7');
        marker.setAttribute('orient', 'auto-start-reverse');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
        path.setAttribute('fill', '#414957');
        marker.appendChild(path);
        defs.appendChild(marker);
      }}

      // Apply marker to edge paths with arrowheads and strip markers from dashed/dotted edges
      const edgePaths = svg.querySelectorAll('path.flowchart-link, path.edge-thickness-normal, path.path');
      edgePaths.forEach((p) => {{
        const strokeDash = p.getAttribute('stroke-dasharray') || p.style.strokeDasharray;
        if (strokeDash && strokeDash !== 'none') {{
          // Inherits or Imports: NO arrowhead
          p.removeAttribute('marker-end');
          p.style.markerEnd = 'none';
        }} else {{
          // Contains or Calls: apply proper arrowhead marker
          p.setAttribute('marker-end', 'url(#proper-arrow)');
        }}
      }});
    }}

    // Watch for SVG render completion
    const observer = new MutationObserver(() => {{
      if (document.querySelector('#diagram-wrapper svg')) {{
        postProcessSvg();
        observer.disconnect();
      }}
    }});
    observer.observe(document.getElementById('diagram-wrapper'), {{ childList: true, subtree: true }});

    // Pan & Zoom
    const viewport = document.getElementById('canvas-viewport');
    const wrapper = document.getElementById('diagram-wrapper');

    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;

    function applyTransform() {{
      wrapper.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
    }}

    viewport.addEventListener('wheel', (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
      scale = Math.min(Math.max(scale * zoomFactor, 0.2), 4);
      applyTransform();
    }}, {{ passive: false }});

    viewport.addEventListener('mousedown', (e) => {{
      if (e.target.closest('button') || e.target.closest('.modal-box')) return;
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
    }});

    window.addEventListener('mousemove', (e) => {{
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      applyTransform();
    }});

    window.addEventListener('mouseup', () => {{
      isDragging = false;
    }});

    // Zoom Buttons
    document.getElementById('zoom-in').addEventListener('click', () => {{
      scale = Math.min(scale * 1.25, 4);
      applyTransform();
    }});

    document.getElementById('zoom-out').addEventListener('click', () => {{
      scale = Math.max(scale / 1.25, 0.2);
      applyTransform();
    }});

    document.getElementById('zoom-reset').addEventListener('click', () => {{
      scale = 1;
      translateX = 0;
      translateY = 0;
      applyTransform();
    }});

    // Toast
    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2200);
    }}

    // Copy Mermaid
    const rawMermaid = document.querySelector('.raw-code').textContent;
    document.getElementById('btn-copy-mermaid').addEventListener('click', () => {{
      navigator.clipboard.writeText(rawMermaid).then(() => {{
        showToast('Mermaid code copied to clipboard!');
      }}).catch(() => {{
        showToast('Failed to copy');
      }});
    }});

    // Export SVG
    document.getElementById('btn-export-svg').addEventListener('click', () => {{
      const svg = document.querySelector('#diagram-wrapper svg');
      if (!svg) {{
        showToast('SVG not ready yet');
        return;
      }}
      postProcessSvg();
      const serializer = new XMLSerializer();
      let source = serializer.serializeToString(svg);
      const blob = new Blob([source], {{ type: 'image/svg+xml;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'architecture_diagram.svg';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('SVG exported successfully!');
    }});

    // Source Modal
    const modal = document.getElementById('source-modal');
    document.getElementById('btn-show-source').addEventListener('click', () => {{
      modal.classList.add('open');
    }});

    document.getElementById('btn-close-source').addEventListener('click', () => {{
      modal.classList.remove('open');
    }});

    modal.addEventListener('click', (e) => {{
      if (e.target === modal) modal.classList.remove('open');
    }});
  </script>
</body>
</html>
"""


def render_diagram_files(
    input_json_path: Path | str,
    output_path: Optional[Path | str] = None,
    include_calls: Optional[bool] = None,
    max_nodes_for_calls: int = 150,
) -> Tuple[Path, Path]:
    """
    Load graph JSON from input_json_path, convert to Mermaid, and write both .mmd and .html files.
    
    Returns:
      (mmd_path, html_path)
    """
    in_path = Path(input_json_path).resolve()
    if not in_path.exists():
        raise FileNotFoundError(f"Input graph file not found: {in_path}")

    with open(in_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    mermaid_code = graph_to_mermaid(
        graph_data,
        include_calls=include_calls,
        max_nodes_for_calls=max_nodes_for_calls,
    )

    if output_path is None:
        mmd_path = in_path.with_suffix(".mmd")
        html_path = in_path.with_suffix(".html")
    else:
        out_p = Path(output_path).resolve()
        if out_p.suffix in (".mmd", ".html"):
            mmd_path = out_p.with_suffix(".mmd")
            html_path = out_p.with_suffix(".html")
        else:
            mmd_path = out_p.with_suffix(".mmd")
            html_path = out_p.with_suffix(".html")

    mmd_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    title = "Architecture Diagram"
    html_content = generate_html_viewer(mermaid_code, graph_data=graph_data, title=title)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return mmd_path, html_path


def render_diagram_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2: Convert Phase 1 graph JSON into a rendered Mermaid architecture diagram and standalone HTML viewer."
    )
    parser.add_argument(
        "graph_json",
        help="Path to input graph.json file.",
    )
    parser.add_argument(
        "output_path_pos",
        nargs="?",
        default=None,
        help="Optional output path for .mmd and .html (default: same stem as graph_json).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output path for .mmd and .html.",
    )
    parser.add_argument(
        "--include-calls",
        action="store_true",
        default=None,
        help="Force include calls edges even if graph has > 150 nodes.",
    )
    parser.add_argument(
        "--no-calls",
        action="store_true",
        help="Force exclude calls edges regardless of node count.",
    )

    args = parser.parse_args()

    include_calls = None
    if args.no_calls:
        include_calls = False
    elif args.include_calls:
        include_calls = True

    out_arg = args.output or args.output_path_pos
    try:
        mmd_file, html_file = render_diagram_files(
            args.graph_json,
            output_path=out_arg,
            include_calls=include_calls,
        )
        print(f"Generated Mermaid diagram: {mmd_file.name}")
        print(f"Generated HTML viewer: {html_file.name}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    render_diagram_cli()
