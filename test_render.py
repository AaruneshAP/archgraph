"""
Unit tests for Phase 2: Architecture Diagram Renderer.
Verifies pure function graph_to_mermaid, node shapes, edge styles, deduplication,
noise guard (>150 nodes), and verification against sample_package/graph.json.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from graph_to_mermaid import (
    graph_to_mermaid,
    generate_html_viewer,
    render_diagram_files,
    sanitize_mermaid_id,
    count_rendered_nodes,
    count_rendered_edges,
    get_collapse_info,
)


class TestGraphToMermaid(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parent.resolve()
        self.sample_graph_json = self.repo_root / "graph.json"
        with open(self.sample_graph_json, "r", encoding="utf-8") as f:
            self.sample_graph_data = json.load(f)

    def test_pure_function_conversion(self):
        """
        Verify graph_to_mermaid is a pure function returning a valid Mermaid string.
        """
        mermaid_text = graph_to_mermaid(self.sample_graph_data)
        self.assertIsInstance(mermaid_text, str)
        self.assertIn("defaultRenderer': 'elk'", mermaid_text)
        self.assertIn("nodeSpacing': 30", mermaid_text)
        self.assertIn("rankSpacing': 40", mermaid_text)
        self.assertIn("graph TD", mermaid_text)
        self.assertIn("classDef default", mermaid_text)

    def test_node_styling_by_type(self):
        """
        Verify nodes are structured as fixed-size cards with:
        - small uppercase type label in accent color
        - 36px colored icon chip
        - bold node name
        - small muted subtitle (file name for modules, extends X for subclasses, file name/entrypoint for functions)
        Type colors: module #E8874A, class #8B6FD1, function #2FA89C
        """
        mermaid_text = graph_to_mermaid(self.sample_graph_data)

        # Module: app
        self.assertIn("#E8874A", mermaid_text)
        self.assertIn("MODULE", mermaid_text)
        self.assertIn("app.py", mermaid_text)

        # Class: AppService extending BaseService
        self.assertIn("#8B6FD1", mermaid_text)
        self.assertIn("CLASS", mermaid_text)
        self.assertIn("AppService", mermaid_text)
        self.assertIn("extends BaseService", mermaid_text)

        # Function: format_message() and compute_total()
        self.assertIn("#2FA89C", mermaid_text)
        self.assertIn("FUNCTION", mermaid_text)
        self.assertIn("format_message()", mermaid_text)
        self.assertIn("main()", mermaid_text)
        self.assertIn("entrypoint", mermaid_text)

    def test_edge_styling_and_verification(self):
        """
        Verify:
        - AppService → BaseService inheritance (dashed without arrow: -.-)
        - app → base and app → utils imports as single clean edges (dotted without arrow: -.-)
        - contains as solid with arrow: -->
        - calls as thin solid with arrow: -->
        - NO inline text labels (|calls|, |imports|, |inherits|) on edges
        """
        mermaid_text = graph_to_mermaid(self.sample_graph_data)

        # 1. Inheritance edge (dashed without arrow, no inline label)
        self.assertIn("app_AppService -.- base_BaseService", mermaid_text)

        # 2. Both imports as single clean edges (dotted without arrow, no inline label)
        self.assertIn("app -.- base", mermaid_text)
        self.assertIn("app -.- utils", mermaid_text)

        # Check there is only ONE clean app -> base import edge
        self.assertEqual(mermaid_text.count("app -.- base"), 1)
        self.assertEqual(mermaid_text.count("app -.- utils"), 1)

        # 3. Contains edges (solid with arrow)
        self.assertIn("app --> app_AppService", mermaid_text)
        self.assertIn("base --> base_BaseService", mermaid_text)
        self.assertIn("utils --> utils_format_message", mermaid_text)

        # 4. Call edges (thin solid with arrow, no inline label)
        self.assertIn("app_AppService --> utils_format_message", mermaid_text)
        self.assertIn("app_AppService --> utils_compute_total", mermaid_text)
        self.assertIn("app_AppService --> base_BaseService", mermaid_text)
        self.assertIn("app_main --> app_AppService", mermaid_text)

        # 5. Verify NO per-edge text labels exist (legend communicates edge meaning)
        self.assertNotIn("|calls|", mermaid_text)
        self.assertNotIn("|imports|", mermaid_text)
        self.assertNotIn("|inherits|", mermaid_text)
        self.assertNotIn("|contains|", mermaid_text)

        # 6. Verify linkStyle for calls has opacity:0.55, and other groups do not
        for line in mermaid_text.splitlines():
            s = line.strip()
            if s.startswith("linkStyle"):
                if "stroke-width:1px" in s:
                    self.assertIn("opacity:0.55", s, "Calls linkStyle must have opacity:0.55")
                else:
                    self.assertNotIn("opacity", s, "Non-calls linkStyle must NOT have opacity set")

    def test_calls_linkstyle_opacity_specifically(self):
        """
        Verify that the generated Mermaid string contains 'opacity:0.55' specifically
        on the calls linkStyle line, and that contains, inherits, and imports do not have opacity.
        """
        mermaid_text = graph_to_mermaid(self.sample_graph_data)
        self.assertIn("stroke:#414957,stroke-width:1px,opacity:0.55;", mermaid_text)
        self.assertIn("linkStyle 0,1,2,3,4 stroke:#414957,stroke-width:1.5px;", mermaid_text)
        self.assertIn("linkStyle 5 stroke:#4A5568,stroke-width:1.5px,stroke-dasharray:7 5;", mermaid_text)
        self.assertIn("linkStyle 6,7 stroke:#4A5568,stroke-width:1.5px,stroke-dasharray:1 5;", mermaid_text)

    def test_unresolved_external_calls_dropped_and_no_phantom_nodes(self):
        """
        Verify that unresolved/external call targets (such as builtins, stdlib,
        or local variable calls like app.run() or prefix.upper()) NEVER appear as nodes,
        and their call edges are dropped entirely from the diagram.
        Only real internal calls between known codebase symbols survive.
        """
        mermaid_text = graph_to_mermaid(self.sample_graph_data)

        # 1. Assert phantom nodes do NOT appear anywhere in the Mermaid output
        self.assertNotIn("app_run", mermaid_text)
        self.assertNotIn("prefix_upper", mermaid_text)
        self.assertNotIn("app.run()", mermaid_text)
        self.assertNotIn("prefix.upper()", mermaid_text)

        # 2. Assert exact set of nodes in Mermaid matches original raw nodes
        expected_safe_ids = [
            "app",
            "app_AppService",
            "app_main",
            "base",
            "base_BaseService",
            "utils",
            "utils_format_message",
            "utils_compute_total",
        ]
        for nid in expected_safe_ids:
            self.assertIn(f'{nid}["', mermaid_text)

        # 3. Assert real internal calls survive
        self.assertIn("app_AppService --> base_BaseService", mermaid_text)
        self.assertIn("app_AppService --> utils_format_message", mermaid_text)
        self.assertIn("app_AppService --> utils_compute_total", mermaid_text)
        self.assertIn("app_main --> app_AppService", mermaid_text)

        # 4. Synthetic graph with external calls like os.path.join and sys.exit
        synthetic_graph = {
            "nodes": [
                {"id": "mod.foo", "type": "function", "name": "foo"},
                {"id": "mod.bar", "type": "function", "name": "bar"},
            ],
            "edges": [
                {"source": "mod.foo", "target": "mod.bar", "type": "calls"},
                {"source": "mod.foo", "target": "os.path.join", "type": "calls"},
                {"source": "mod.foo", "target": "sys.exit", "type": "calls"},
                {"source": "mod.foo", "target": "unknown_var.method", "type": "calls"},
            ],
        }
        synth_output = graph_to_mermaid(synthetic_graph)
        self.assertIn("mod_foo --> mod_bar", synth_output)
        self.assertNotIn("os_path_join", synth_output)
        self.assertNotIn("sys_exit", synth_output)
        self.assertNotIn("unknown_var", synth_output)

    def test_edge_deduplication(self):
        """
        Verify that repeated (source, target, type) triples collapse into a single edge.
        """
        sample_data = {
            "nodes": [
                {"id": "m1", "type": "module", "name": "m1"},
                {"id": "m2", "type": "module", "name": "m2"},
            ],
            "edges": [
                {"source": "m1", "target": "m2", "type": "imports"},
                {"source": "m1", "target": "m2", "type": "imports"},
                {"source": "m1", "target": "m2", "type": "imports"},
            ],
        }
        mermaid_text = graph_to_mermaid(sample_data)
        # Should only contain m1 -.- m2 exactly once
        self.assertEqual(mermaid_text.count("m1 -.- m2"), 1)

    def test_noise_guard_threshold(self):
        """
        Verify: if graph has > 150 nodes, drop calls edges by default,
        with a flag to force-include them anyway.
        """
        # Create a synthetic graph with 160 nodes
        big_nodes = [
            {"id": f"mod_{i}", "type": "module", "name": f"mod_{i}"} for i in range(160)
        ]
        big_edges = [
            {"source": "mod_0", "target": "mod_1", "type": "imports"},
            {"source": "mod_1", "target": "mod_2", "type": "calls"},
        ]
        big_graph = {"nodes": big_nodes, "edges": big_edges}

        # 1. Default (include_calls=None): >150 nodes -> calls omitted
        out_default = graph_to_mermaid(big_graph)
        self.assertIn("mod_0 -.- mod_1", out_default)
        self.assertNotIn("mod_1 --> mod_2", out_default)

        # 2. Forced include (include_calls=True): calls included
        out_forced = graph_to_mermaid(big_graph, include_calls=True)
        self.assertIn("mod_0 -.- mod_1", out_forced)
        self.assertIn("mod_1 --> mod_2", out_forced)

        # 3. Explicit exclude (include_calls=False): calls omitted
        out_excluded = graph_to_mermaid(big_graph, include_calls=False)
        self.assertNotIn("mod_1 --> mod_2", out_excluded)

        # 4. Small graph (<= 150 nodes): calls included by default
        small_nodes = [
            {"id": f"mod_{i}", "type": "module", "name": f"mod_{i}"} for i in range(10)
        ]
        small_graph = {"nodes": small_nodes, "edges": big_edges}
        out_small = graph_to_mermaid(small_graph)
        self.assertIn("mod_1 --> mod_2", out_small)

    def test_html_viewer_generation(self):
        """
        Verify HTML viewer contains IBM Plex Sans, IBM Plex Mono, 2-column layout,
        fixed 300px sidebar, and zero build step.
        """
        mermaid_code = graph_to_mermaid(self.sample_graph_data)
        html_code = generate_html_viewer(mermaid_code, self.sample_graph_data)

        self.assertIn("<!DOCTYPE html>", html_code)
        self.assertIn("cdn.jsdelivr.net/npm/mermaid", html_code)
        self.assertIn("IBM+Plex+Sans", html_code)
        self.assertIn("IBM+Plex+Mono", html_code)
        self.assertIn("300px", html_code)
        self.assertIn("sidebar-panel", html_code)
        self.assertIn("Legend", html_code)
        self.assertIn("#E8874A", html_code)
        self.assertIn("#8B6FD1", html_code)
        self.assertIn("#2FA89C", html_code)
        self.assertIn("Unresolved calls (builtins, instance vars) are dropped, not guessed.", html_code)

    def test_render_diagram_files_and_cli(self):
        """
        Verify render_diagram_files writes both .mmd and .html files,
        and CLI executes properly.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_mmd = Path(tmp_dir) / "out.mmd"
            out_html = Path(tmp_dir) / "out.html"

            # API Call
            mmd_res, html_res = render_diagram_files(
                self.sample_graph_json,
                output_path=out_mmd,
            )
            self.assertTrue(mmd_res.exists())
            self.assertTrue(html_res.exists())

            # CLI Call
            cli_out = Path(tmp_dir) / "cli_out"
            cmd = [
                sys.executable,
                str(self.repo_root / "render_diagram.py"),
                str(self.sample_graph_json),
                str(cli_out),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertTrue((Path(tmp_dir) / "cli_out.mmd").exists())
            self.assertTrue((Path(tmp_dir) / "cli_out.html").exists())

    def test_count_rendered_edges(self):
        """
        Verify count_rendered_edges accurately counts the edges present in the Mermaid output.
        """
        mmd = graph_to_mermaid(self.sample_graph_data)
        count = count_rendered_edges(mmd)
        # In sample_package, 14 raw edges -> 2 unresolved calls dropped -> 12 rendered edges
        self.assertEqual(count, 12)

    def test_count_rendered_nodes(self):
        """
        Verify count_rendered_nodes accurately counts the node cards rendered in the Mermaid output.
        """
        mmd = graph_to_mermaid(self.sample_graph_data)
        count = count_rendered_nodes(mmd)
        # sample_package has 8 nodes (3 modules, 2 classes, 3 functions)
        self.assertEqual(count, 8)

    def test_level_of_detail_collapsing(self):
        """
        Verify:
        - If total node count exceeds 150, drop function nodes and render only module & class nodes.
        - Dropped functions are attributed to parent module/class cards as badge subtitles (e.g. '12 functions').
        - Displayed node count matches visible rendered count (modules + classes only).
        - Visible collapse banner indicator is added to HTML viewer and Mermaid comment.
        - Graphs <= 150 nodes remain completely uncollapsed with full function detail and no banner.
        """
        # 1. Build a synthetic graph with 160 nodes: 20 modules, 30 classes, 110 functions
        nodes = []
        edges = []

        # 20 modules
        for m in range(20):
            mod_id = f"mod_{m}"
            nodes.append({"id": mod_id, "type": "module", "name": mod_id, "file": f"{mod_id}.py"})

        # 30 classes (distributed across modules)
        for c in range(30):
            cls_id = f"cls_{c}"
            mod_id = f"mod_{c % 20}"
            nodes.append({"id": cls_id, "type": "class", "name": cls_id, "module": mod_id})
            edges.append({"source": mod_id, "target": cls_id, "type": "contains"})

        # 110 functions (attached to classes and modules)
        for f in range(110):
            fn_id = f"fn_{f}"
            if f < 60:
                parent_cls = f"cls_{f % 30}"
                nodes.append({"id": fn_id, "type": "function", "name": fn_id, "qualname": f"{parent_cls}.{fn_id}"})
                edges.append({"source": parent_cls, "target": fn_id, "type": "contains"})
            else:
                parent_mod = f"mod_{f % 20}"
                nodes.append({"id": fn_id, "type": "function", "name": fn_id, "module": parent_mod})
                edges.append({"source": parent_mod, "target": fn_id, "type": "contains"})

        large_graph = {"nodes": nodes, "edges": edges, "files_scanned": 20}
        self.assertEqual(len(nodes), 160)

        # A. Large graph (>150 nodes): LoD active
        collapse_info = get_collapse_info(large_graph)
        self.assertTrue(collapse_info["collapsed"])
        self.assertEqual(collapse_info["functions_hidden"], 110)
        self.assertEqual(collapse_info["rendered_nodes"], 50)
        self.assertEqual(collapse_info["total_nodes"], 160)

        large_mmd = graph_to_mermaid(large_graph)
        rendered_nodes = count_rendered_nodes(large_mmd)
        self.assertEqual(rendered_nodes, 50)  # 20 modules + 30 classes

        # Confirm no function nodes are in the diagram
        self.assertNotIn("FUNCTION", large_mmd)
        for f in range(110):
            self.assertNotIn(f'node_fn_{f}["', large_mmd)

        # Confirm module and class nodes ARE rendered
        self.assertIn("MODULE", large_mmd)
        self.assertIn("CLASS", large_mmd)

        # Confirm function count badges appear on cards
        self.assertIn("functions", large_mmd)

        # Confirm comment banner in Mermaid string
        self.assertIn("%% Note: Showing modules and classes only — 110 functions hidden (repo exceeds 150 nodes)", large_mmd)

        # Confirm HTML viewer contains visible collapse banner
        html_out = generate_html_viewer(large_mmd, large_graph)
        self.assertIn("Showing modules and classes only — 110 functions hidden (repo exceeds 150 nodes)", html_out)
        self.assertIn("collapse-banner", html_out)
        # Stats in HTML viewer must show 50 nodes, not 160
        self.assertIn(">50</span>&nbsp;nodes", html_out)

        # B. Small graph (sample_package, 8 nodes): LoD inactive
        small_info = get_collapse_info(self.sample_graph_data)
        self.assertFalse(small_info["collapsed"])
        self.assertEqual(small_info["functions_hidden"], 0)
        self.assertEqual(small_info["rendered_nodes"], 8)

        small_mmd = graph_to_mermaid(self.sample_graph_data)
        self.assertEqual(count_rendered_nodes(small_mmd), 8)
        self.assertIn("FUNCTION", small_mmd)
        self.assertIn("format_message()", small_mmd)
        self.assertNotIn("%% Note: Showing modules and classes only", small_mmd)

        small_html = generate_html_viewer(small_mmd, self.sample_graph_data)
        self.assertNotIn("collapse-banner", small_html)
        self.assertIn(">8</span>&nbsp;nodes", small_html)

        # C. Explicit collapse_functions flag override
        force_uncollapsed_mmd = graph_to_mermaid(large_graph, collapse_functions=False)
        self.assertEqual(count_rendered_nodes(force_uncollapsed_mmd), 160)
        self.assertIn("FUNCTION", force_uncollapsed_mmd)

        force_collapsed_small_mmd = graph_to_mermaid(self.sample_graph_data, collapse_functions=True)
        self.assertEqual(count_rendered_nodes(force_collapsed_small_mmd), 5)  # 3 modules + 2 classes
        self.assertNotIn("FUNCTION", force_collapsed_small_mmd)

        # D. Very large graph where modules + classes STILL exceeds 150 (Tier 2 Escalation)
        # 50 modules, 160 classes, 200 functions = 410 total nodes
        huge_nodes = []
        huge_edges = []
        for m in range(50):
            m_id = f"pkg.mod_{m}"
            huge_nodes.append({"id": m_id, "type": "module", "name": f"mod_{m}", "file": f"mod_{m}.py"})

        for c in range(160):
            c_id = f"pkg.mod_{c % 50}.Class_{c}"
            m_id = f"pkg.mod_{c % 50}"
            huge_nodes.append({"id": c_id, "type": "class", "name": f"Class_{c}", "module": m_id})
            huge_edges.append({"source": m_id, "target": c_id, "type": "contains"})

        for f in range(200):
            f_id = f"pkg.mod_{f % 50}.func_{f}"
            m_id = f"pkg.mod_{f % 50}"
            huge_nodes.append({"id": f_id, "type": "function", "name": f"func_{f}", "module": m_id})
            huge_edges.append({"source": m_id, "target": f_id, "type": "contains"})

        huge_graph = {"nodes": huge_nodes, "edges": huge_edges, "files_scanned": 50}
        self.assertEqual(len(huge_nodes), 410)

        huge_info = get_collapse_info(huge_graph)
        self.assertTrue(huge_info["collapsed"])
        self.assertEqual(huge_info["level"], "functions-and-classes-hidden")
        self.assertEqual(huge_info["functions_hidden"], 200)
        self.assertEqual(huge_info["classes_hidden"], 160)
        self.assertEqual(huge_info["rendered_nodes"], 50)
        self.assertEqual(
            huge_info["banner_text"],
            "Showing modules only — 160 classes and 200 functions hidden (repo exceeds 150 nodes)",
        )

        huge_mmd = graph_to_mermaid(huge_graph)
        self.assertEqual(count_rendered_nodes(huge_mmd), 50)

        # Confirm neither FUNCTION nor CLASS nodes are rendered
        self.assertNotIn("FUNCTION", huge_mmd)
        self.assertNotIn("CLASS", huge_mmd)
        self.assertIn("MODULE", huge_mmd)

        # Confirm module cards have both class and function count badges
        self.assertIn("classes", huge_mmd)
        self.assertIn("functions", huge_mmd)

        # Confirm comment banner in Mermaid
        self.assertIn("%% Note: Showing modules only — 160 classes and 200 functions hidden", huge_mmd)

        # Confirm HTML viewer contains visible collapse banner with both counts
        huge_html = generate_html_viewer(huge_mmd, huge_graph)
        self.assertIn("Showing modules only — 160 classes and 200 functions hidden (repo exceeds 150 nodes)", huge_html)
        self.assertIn(">50</span>&nbsp;nodes", huge_html)


if __name__ == "__main__":
    unittest.main()
