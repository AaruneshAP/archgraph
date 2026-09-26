"""
Automated test suite verifying Phase 1 of codebase-to-architecture-diagram tool.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from codebase_graph import build_graph, EXCLUDED_DIRS


class TestCodebaseGraph(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parent.resolve()
        self.sample_dir = self.repo_root / "sample_package"
        self.output_json = self.repo_root / "test_graph_out.json"

    def tearDown(self):
        if self.output_json.exists():
            self.output_json.unlink()

    def test_sample_package_structure(self):
        """
        Verify the 3-file sample package outputs:
        - 3 files scanned
        - 0 errors
        - module, class, function nodes
        - the inheritance edge
        - both import edges
        - the call chain across files
        """
        graph_data, files_scanned, node_count, edge_count, error_count = build_graph(
            self.sample_dir
        )

        self.assertEqual(files_scanned, 3)
        self.assertEqual(error_count, 0)
        self.assertEqual(len(graph_data["errors"]), 0)

        # Validate nodes
        nodes_by_id = {n["id"]: n for n in graph_data["nodes"]}

        # Modules
        self.assertIn("app", nodes_by_id)
        self.assertEqual(nodes_by_id["app"]["type"], "module")
        self.assertIn("base", nodes_by_id)
        self.assertEqual(nodes_by_id["base"]["type"], "module")
        self.assertIn("utils", nodes_by_id)
        self.assertEqual(nodes_by_id["utils"]["type"], "module")

        # Classes
        self.assertIn("base.BaseService", nodes_by_id)
        self.assertEqual(nodes_by_id["base.BaseService"]["type"], "class")
        self.assertEqual(nodes_by_id["base.BaseService"]["bases"], [])
        self.assertIn("execute", nodes_by_id["base.BaseService"]["methods"])

        self.assertIn("app.AppService", nodes_by_id)
        self.assertEqual(nodes_by_id["app.AppService"]["type"], "class")
        self.assertEqual(nodes_by_id["app.AppService"]["bases"], ["BaseService"])
        self.assertIn("run", nodes_by_id["app.AppService"]["methods"])

        # Top-level Functions
        self.assertIn("app.main", nodes_by_id)
        self.assertEqual(nodes_by_id["app.main"]["type"], "function")

        self.assertIn("utils.format_message", nodes_by_id)
        self.assertEqual(nodes_by_id["utils.format_message"]["type"], "function")
        self.assertEqual(nodes_by_id["utils.format_message"]["args"], ["prefix", "msg"])

        self.assertIn("utils.compute_total", nodes_by_id)
        self.assertEqual(nodes_by_id["utils.compute_total"]["type"], "function")
        self.assertEqual(nodes_by_id["utils.compute_total"]["args"], ["a", "b"])

        # Validate edges
        edges = graph_data["edges"]

        # 1. Inheritance Edge
        inherits_edges = [
            e for e in edges if e["type"] == "inherits" and e["source"] == "app.AppService"
        ]
        self.assertEqual(len(inherits_edges), 1)
        self.assertEqual(inherits_edges[0]["target"], "BaseService")

        # 2. Both Import Edges from app
        import_edges = [
            e for e in edges if e["type"] == "imports" and e["source"] == "app"
        ]
        self.assertGreaterEqual(len(import_edges), 2)
        base_import = [e for e in import_edges if "base" in e["target"] or e.get("module") == "base"]
        utils_import = [e for e in import_edges if "utils" in e["target"] or e.get("module") == "utils"]
        self.assertTrue(len(base_import) >= 1, "Expected import edge to base")
        self.assertTrue(len(utils_import) >= 1, "Expected import edge to utils")

        # 3. Call chain across files:
        # main -> app.run
        # AppService.run -> self.execute (base class method)
        # AppService.run -> utils.format_message
        # AppService.run -> utils.compute_total
        call_edges = [e for e in edges if e["type"] == "calls"]
        call_pairs = [(c["source"], c["target"]) for c in call_edges]

        self.assertIn(("main", "AppService"), call_pairs)
        self.assertIn(("main", "app.run"), call_pairs)
        self.assertIn(("AppService.run", "self.execute"), call_pairs)
        self.assertIn(("AppService.run", "utils.format_message"), call_pairs)
        self.assertIn(("AppService.run", "utils.compute_total"), call_pairs)

    def test_directory_exclusion(self):
        """
        Verify that excluded directories (.git, venv, etc.) are skipped during scanning.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a regular file
            (tmp_path / "valid.py").write_text("def ok(): pass\n", encoding="utf-8")

            # Create skipped directories with python files
            for skipped_name in EXCLUDED_DIRS:
                d = tmp_path / skipped_name
                d.mkdir(parents=True, exist_ok=True)
                (d / "should_skip.py").write_text("def skip(): pass\n", encoding="utf-8")

            graph_data, files_scanned, node_count, edge_count, error_count = build_graph(tmp_path)
            self.assertEqual(files_scanned, 1)
            self.assertEqual(len(graph_data["nodes"]), 2)  # 1 module + 1 function
            scanned_files = [n["file"] for n in graph_data["nodes"] if "file" in n]
            self.assertTrue(all("should_skip" not in f for f in scanned_files))

    def test_graceful_error_handling(self):
        """
        Verify that SyntaxError and UnicodeDecodeError are recorded in errors list
        and do not crash the run.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Valid file
            (tmp_path / "valid.py").write_text("x = 1\n", encoding="utf-8")

            # SyntaxError file
            (tmp_path / "bad_syntax.py").write_text("def broken_syntax(:\n", encoding="utf-8")

            # Non-utf8 binary file with .py extension
            with open(tmp_path / "bad_unicode.py", "wb") as f:
                f.write(b"\xff\xfe\x00\x00invalid-utf8\x80\x81")

            graph_data, files_scanned, node_count, edge_count, error_count = build_graph(tmp_path)
            self.assertEqual(files_scanned, 3)
            self.assertEqual(error_count, 2)
            self.assertEqual(len(graph_data["errors"]), 2)

            error_types = {e["error_type"] for e in graph_data["errors"]}
            self.assertIn("SyntaxError", error_types)
            self.assertIn("UnicodeDecodeError", error_types)

            # The valid file was still parsed successfully
            mod_names = [n["id"] for n in graph_data["nodes"] if n["type"] == "module"]
            self.assertIn("valid", mod_names)

    def test_cli_execution(self):
        """
        Verify CLI invocation and stdout one-line summary output.
        """
        cmd = [
            sys.executable,
            str(self.repo_root / "codebase_graph.py"),
            str(self.sample_dir),
            "-o",
            str(self.output_json),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Files scanned: 3", result.stdout)
        self.assertIn("Nodes:", result.stdout)
        self.assertIn("Edges:", result.stdout)
        self.assertIn("Errors: 0", result.stdout)

        self.assertTrue(self.output_json.exists())
        with open(self.output_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["files_scanned"], 3)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("errors", data)


if __name__ == "__main__":
    unittest.main()
