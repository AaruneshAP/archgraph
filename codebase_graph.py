#!/usr/bin/env python3
"""
Phase 1: Codebase-to-Architecture-Diagram Tool
Parses a Python codebase using the `ast` module into a structured architecture graph JSON.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Directories to skip when scanning a codebase
EXCLUDED_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "site-packages",
    ".mypy_cache",
    ".pytest_cache",
    ".vercel",
    ".agents",
}


def resolve_callee_name(node: ast.AST) -> Optional[str]:
    """
    Resolve ast.Name and ast.Attribute chains to a dotted string (e.g. 'os.environ.get').
    If the expression is not purely Name and Attribute, returns None (skip).
    """
    parts: List[str] = []
    curr: ast.AST = node
    while isinstance(curr, ast.Attribute):
        parts.append(curr.attr)
        curr = curr.value
    if isinstance(curr, ast.Name):
        parts.append(curr.id)
        return ".".join(reversed(parts))
    return None


def resolve_base_name(node: ast.AST) -> str:
    """
    Convert an AST node representing a base class to its string representation.
    """
    callee = resolve_callee_name(node)
    if callee:
        return callee
    try:
        return ast.unparse(node)
    except Exception:
        return "<unknown_base>"


def get_module_name_from_relpath(rel_path_str: str) -> str:
    """
    Compute the dotted module name for a relative file path string.
    E.g.:
      'app.py' -> 'app'
      'pkg/utils.py' -> 'pkg.utils'
      'pkg/__init__.py' -> 'pkg'
      '__init__.py' -> '__init__'
    """
    clean_path = rel_path_str.replace("\\", "/").strip("/")
    parts = [p for p in clean_path.split("/") if p]
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        if len(parts) > 1:
            return ".".join(parts[:-1])
        return "__init__"
    return ".".join(parts)


def get_module_name(file_path: Path, root_dir: Path) -> str:
    """
    Compute the dotted module name for a python file relative to the root directory.
    """
    rel = file_path.relative_to(root_dir).as_posix()
    return get_module_name_from_relpath(str(rel))


def resolve_relative_import(
    current_module: str,
    is_init_file: bool,
    import_module: Optional[str],
    level: int,
) -> str:
    """
    Resolve a relative import (from .x or from ..x) against current module path.
    """
    if level == 0:
        return import_module or ""

    parts = current_module.split(".") if current_module else []
    # If not __init__.py, current package is parent directory
    pkg_parts = parts if is_init_file else parts[:-1]

    # level 1 is current package (ascend 0 times)
    # level 2 ascends 1 time, etc.
    ascend = level - 1
    if ascend > 0:
        if ascend <= len(pkg_parts):
            base_parts = pkg_parts[:-ascend]
        else:
            base_parts = []
    else:
        base_parts = pkg_parts

    if import_module:
        return ".".join(base_parts + [import_module]) if base_parts else import_module
    return ".".join(base_parts)


class FileParseResult:
    def __init__(self, file_path: Optional[Path], rel_path_str: str, module_name: str):
        self.file_path = file_path
        self.rel_path_str = rel_path_str
        self.module_name = module_name
        self.imports: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.calls: List[Dict[str, Any]] = []


def parse_python_code(
    source: str,
    rel_path_str: str,
    errors: List[Dict[str, Any]],
    file_path: Optional[Path] = None,
) -> Optional[FileParseResult]:
    """
    Parse Python source code using the ast module and extract:
      - module name
      - imports
      - classes
      - top-level functions
      - best-effort call edges
    Handles SyntaxError gracefully.
    """
    module_name = get_module_name_from_relpath(rel_path_str)
    is_init = rel_path_str.endswith("__init__.py") or (
        file_path.name == "__init__.py" if file_path else False
    )

    try:
        tree = ast.parse(source, filename=rel_path_str)
    except SyntaxError as e:
        errors.append(
            {
                "file": rel_path_str,
                "error_type": "SyntaxError",
                "message": str(e.msg if hasattr(e, "msg") else e),
                "line": e.lineno,
            }
        )
        return None
    except Exception as e:
        errors.append(
            {
                "file": rel_path_str,
                "error_type": type(e).__name__,
                "message": str(e),
                "line": getattr(e, "lineno", None),
            }
        )
        return None

    result = FileParseResult(file_path, rel_path_str, module_name)

    # 1. Extract imports (both `import x` and `from x import y`)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append(
                    {
                        "module": alias.name,
                        "name": None,
                        "asname": alias.asname,
                        "line": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            level = getattr(node, "level", 0)
            raw_module = node.module
            resolved_module = resolve_relative_import(
                module_name, is_init, raw_module, level
            )
            for alias in node.names:
                result.imports.append(
                    {
                        "module": resolved_module,
                        "raw_module": raw_module,
                        "name": alias.name,
                        "asname": alias.asname,
                        "line": node.lineno,
                    }
                )

    # Helper function to walk all ast.Call nodes in a function/method body
    def extract_calls_from_body(
        body_nodes: List[ast.AST], caller_qualname: str
    ) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        for stmt in body_nodes:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call):
                    callee = resolve_callee_name(n.func)
                    if callee:
                        calls.append(
                            {
                                "caller_qualname": caller_qualname,
                                "callee_name": callee,
                                "line": getattr(n, "lineno", None),
                            }
                        )
        return calls

    # 2. Extract classes, top-level functions, and their calls
    for item in tree.body:
        if isinstance(item, ast.ClassDef):
            class_name = item.name
            base_names = [resolve_base_name(b) for b in item.bases]
            method_names: List[str] = []

            for member in item.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_names.append(member.name)
                    method_qualname = f"{class_name}.{member.name}"
                    result.calls.extend(
                        extract_calls_from_body(member.body, method_qualname)
                    )

            result.classes.append(
                {
                    "name": class_name,
                    "bases": base_names,
                    "methods": method_names,
                    "line": item.lineno,
                }
            )

        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = item.name
            arg_names: List[str] = []
            if hasattr(item.args, "posonlyargs"):
                arg_names.extend([a.arg for a in item.args.posonlyargs])
            arg_names.extend([a.arg for a in item.args.args])
            if item.args.vararg:
                arg_names.append(item.args.vararg.arg)
            if hasattr(item.args, "kwonlyargs"):
                arg_names.extend([a.arg for a in item.args.kwonlyargs])
            if item.args.kwarg:
                arg_names.append(item.args.kwarg.arg)

            result.functions.append(
                {
                    "name": func_name,
                    "args": arg_names,
                    "line": item.lineno,
                }
            )
            result.calls.extend(extract_calls_from_body(item.body, func_name))

    return result


def parse_python_file(
    file_path: Path, root_dir: Path, errors: List[Dict[str, Any]]
) -> Optional[FileParseResult]:
    """
    Read a Python file from disk and parse it using parse_python_code.
    Handles UnicodeDecodeError and I/O errors gracefully.
    """
    rel_path_str = str(file_path.relative_to(root_dir).as_posix())
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except UnicodeDecodeError as e:
        errors.append(
            {
                "file": rel_path_str,
                "error_type": "UnicodeDecodeError",
                "message": str(e),
                "line": None,
            }
        )
        return None
    except Exception as e:
        errors.append(
            {
                "file": rel_path_str,
                "error_type": type(e).__name__,
                "message": str(e),
                "line": None,
            }
        )
        return None

    return parse_python_code(source, rel_path_str, errors, file_path)


def find_all_python_files(root_dir: Path) -> List[Path]:
    """
    Recursively find all .py files in root_dir, skipping excluded directories.
    """
    py_files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter dirnames in-place so os.walk does not traverse excluded dirs
        dirnames[:] = sorted([d for d in dirnames if d not in EXCLUDED_DIRS])
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                py_files.append(Path(dirpath) / filename)
    return sorted(py_files)


def assemble_graph(
    parsed_results: List[FileParseResult],
    files_scanned: int,
    errors: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], int, int, int, int]:
    """
    Assemble nodes and edges from parsed results into the standard graph dictionary.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Build Nodes
    # - one per module (type: module)
    # - one per class (id = module.ClassName, type: class)
    # - one per top-level function (id = module.func_name, type: function)
    for res in parsed_results:
        mod_id = res.module_name
        nodes.append(
            {
                "id": mod_id,
                "type": "module",
                "name": mod_id,
                "file": res.rel_path_str,
            }
        )

        for cls in res.classes:
            cls_id = f"{mod_id}.{cls['name']}"
            nodes.append(
                {
                    "id": cls_id,
                    "type": "class",
                    "name": cls["name"],
                    "module": mod_id,
                    "file": res.rel_path_str,
                    "line": cls["line"],
                    "bases": cls["bases"],
                    "methods": cls["methods"],
                }
            )

        for fn in res.functions:
            fn_id = f"{mod_id}.{fn['name']}"
            nodes.append(
                {
                    "id": fn_id,
                    "type": "function",
                    "name": fn["name"],
                    "module": mod_id,
                    "file": res.rel_path_str,
                    "line": fn["line"],
                    "args": fn["args"],
                }
            )

    # 2. Build Edges
    # - `contains`: (module → its classes/functions)
    # - `inherits`: (class → base class name)
    # - `imports`: (module → imported module/name)
    # - `calls`: (caller qualname → callee name)
    for res in parsed_results:
        mod_id = res.module_name

        # contains: module -> class
        for cls in res.classes:
            cls_id = f"{mod_id}.{cls['name']}"
            edges.append(
                {
                    "source": mod_id,
                    "target": cls_id,
                    "type": "contains",
                }
            )
            # inherits: class -> base class name
            for base_name in cls["bases"]:
                edges.append(
                    {
                        "source": cls_id,
                        "target": base_name,
                        "type": "inherits",
                        "class_name": cls["name"],
                        "line": cls["line"],
                    }
                )

        # contains: module -> function
        for fn in res.functions:
            fn_id = f"{mod_id}.{fn['name']}"
            edges.append(
                {
                    "source": mod_id,
                    "target": fn_id,
                    "type": "contains",
                }
            )

        # imports: module -> imported module/name
        for imp in res.imports:
            target_name = (
                f"{imp['module']}.{imp['name']}"
                if imp["module"] and imp["name"]
                else (imp["module"] or imp["name"])
            )
            edges.append(
                {
                    "source": mod_id,
                    "target": target_name,
                    "type": "imports",
                    "module": imp["module"],
                    "name": imp["name"],
                    "asname": imp["asname"],
                    "line": imp["line"],
                }
            )

        # calls: caller qualname -> callee name
        for call in res.calls:
            edges.append(
                {
                    "source": call["caller_qualname"],
                    "target": call["callee_name"],
                    "type": "calls",
                    "caller_qualname": call["caller_qualname"],
                    "callee_name": call["callee_name"],
                    "caller_module": mod_id,
                    "caller_id": f"{mod_id}.{call['caller_qualname']}",
                    "line": call["line"],
                }
            )

    graph_data = {
        "files_scanned": files_scanned,
        "nodes": nodes,
        "edges": edges,
        "errors": errors,
    }
    return graph_data, files_scanned, len(nodes), len(edges), len(errors)


def build_graph_from_sources(
    sources: Dict[str, str],
) -> Tuple[Dict[str, Any], int, int, int, int]:
    """
    Parse a collection of Python file contents directly from memory.
    sources: mapping from relative posix path (e.g. 'app.py', 'pkg/utils.py') to source code string.
    """
    errors: List[Dict[str, Any]] = []
    parsed_results: List[FileParseResult] = []

    for rel_path_str, source in sorted(sources.items()):
        parsed = parse_python_code(source, rel_path_str, errors)
        if parsed:
            parsed_results.append(parsed)

    return assemble_graph(parsed_results, len(sources), errors)


def build_graph(
    root_dir: Path | str,
) -> Tuple[Dict[str, Any], int, int, int, int]:
    """
    Scan root_dir, parse all .py files, and construct nodes, edges, errors.
    Returns:
      (graph_dict, files_scanned, node_count, edge_count, error_count)
    """
    path_obj = Path(root_dir).resolve() if isinstance(root_dir, str) else root_dir
    py_files = find_all_python_files(path_obj)
    errors: List[Dict[str, Any]] = []
    parsed_results: List[FileParseResult] = []

    for file_path in py_files:
        parsed = parse_python_file(file_path, path_obj, errors)
        if parsed:
            parsed_results.append(parsed)

    return assemble_graph(parsed_results, len(py_files), errors)


def parse_codebase_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a Python codebase into a structure graph JSON."
    )
    parser.add_argument(
        "root_dir",
        help="Root directory path of the codebase to parse.",
    )
    parser.add_argument(
        "output_path_pos",
        nargs="?",
        default=None,
        help="Optional output JSON path (default: graph.json).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output JSON path (default: graph.json).",
    )

    args = parser.parse_args()
    root_path = Path(args.root_dir).resolve()
    if not root_path.exists() or not root_path.is_dir():
        print(f"Error: Directory '{args.root_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    output_path_str = args.output or args.output_path_pos or "graph.json"
    output_path = Path(output_path_str).resolve()

    graph_data, files_scanned, node_count, edge_count, error_count = build_graph(
        root_path
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)

    # Print one-line summary to stdout
    print(
        f"Files scanned: {files_scanned}, Nodes: {node_count}, Edges: {edge_count}, Errors: {error_count}"
    )


if __name__ == "__main__":
    parse_codebase_cli()
