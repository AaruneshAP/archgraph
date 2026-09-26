"""
Unit and integration tests for Phase 3: Git-diff tracking for codebase structure graphs.
Verifies:
1. diff_graphs pure function behavior (nodes/edges added/removed, type/file changes, deduplication).
2. get_graph_at_revision git tree blob extraction without working-tree mutation.
3. End-to-end verification against a git repo initialized from sample_package:
   - Commit 1: sample_package with unused `import os`
   - Commit 2: adds utils.notify(), calls it from app.main(), removes `import os`
   - Confirms: 1 node added (utils.notify), 0 nodes removed,
     2 edges added (contains + calls), 1 edge removed (os import),
     and nothing else falsely flagged as changed.
4. CLI diff_graph.py execution and stdout summary output.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import git

from diff_graph import diff_graphs, get_graph_at_revision


class TestDiffGraphsPure(unittest.TestCase):
    """
    Unit tests for the pure diff_graphs function.
    Ensures zero git or file I/O dependencies.
    """

    def test_empty_graphs(self):
        result = diff_graphs({}, {})
        self.assertEqual(result["nodes_added"], [])
        self.assertEqual(result["nodes_removed"], [])
        self.assertEqual(result["edges_added"], [])
        self.assertEqual(result["edges_removed"], [])
        self.assertEqual(
            result["summary"],
            {"nodes_added": 0, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0},
        )

    def test_node_addition_and_removal(self):
        old_graph = {
            "nodes": [
                {"id": "mod_a", "type": "module", "file": "mod_a.py"},
                {"id": "mod_b", "type": "module", "file": "mod_b.py"},
            ],
            "edges": [],
        }
        new_graph = {
            "nodes": [
                {"id": "mod_b", "type": "module", "file": "mod_b.py"},
                {"id": "mod_c", "type": "module", "file": "mod_c.py"},
            ],
            "edges": [],
        }

        result = diff_graphs(old_graph, new_graph)
        self.assertEqual(len(result["nodes_added"]), 1)
        self.assertEqual(result["nodes_added"][0]["id"], "mod_c")
        self.assertEqual(len(result["nodes_removed"]), 1)
        self.assertEqual(result["nodes_removed"][0]["id"], "mod_a")
        self.assertEqual(result["summary"]["nodes_added"], 1)
        self.assertEqual(result["summary"]["nodes_removed"], 1)

    def test_node_type_change_shows_removed_and_added(self):
        """
        A node that exists in both graphs but changed type must appear in both
        nodes_removed and nodes_added.
        """
        old_graph = {
            "nodes": [
                {"id": "sym_x", "type": "function", "file": "sym.py", "line": 10},
            ],
            "edges": [],
        }
        new_graph = {
            "nodes": [
                {"id": "sym_x", "type": "class", "file": "sym.py", "line": 10},
            ],
            "edges": [],
        }

        result = diff_graphs(old_graph, new_graph)
        self.assertEqual(len(result["nodes_removed"]), 1)
        self.assertEqual(result["nodes_removed"][0]["type"], "function")
        self.assertEqual(len(result["nodes_added"]), 1)
        self.assertEqual(result["nodes_added"][0]["type"], "class")
        self.assertEqual(result["summary"]["nodes_added"], 1)
        self.assertEqual(result["summary"]["nodes_removed"], 1)

    def test_node_file_change_shows_removed_and_added(self):
        """
        A node that exists in both graphs but changed file must appear in both
        nodes_removed and nodes_added.
        """
        old_graph = {
            "nodes": [
                {"id": "helper", "type": "function", "file": "old_path.py"},
            ],
            "edges": [],
        }
        new_graph = {
            "nodes": [
                {"id": "helper", "type": "function", "file": "new_path.py"},
            ],
            "edges": [],
        }

        result = diff_graphs(old_graph, new_graph)
        self.assertEqual(len(result["nodes_removed"]), 1)
        self.assertEqual(result["nodes_removed"][0]["file"], "old_path.py")
        self.assertEqual(len(result["nodes_added"]), 1)
        self.assertEqual(result["nodes_added"][0]["file"], "new_path.py")

    def test_node_line_change_does_not_falsely_flag(self):
        """
        Line number shifting alone must NOT cause a node to show as removed/added.
        """
        old_graph = {
            "nodes": [
                {"id": "mod.fn", "type": "function", "file": "mod.py", "line": 12},
            ],
            "edges": [],
        }
        new_graph = {
            "nodes": [
                {"id": "mod.fn", "type": "function", "file": "mod.py", "line": 45},
            ],
            "edges": [],
        }

        result = diff_graphs(old_graph, new_graph)
        self.assertEqual(len(result["nodes_added"]), 0)
        self.assertEqual(len(result["nodes_removed"]), 0)
        self.assertEqual(result["summary"]["nodes_added"], 0)
        self.assertEqual(result["summary"]["nodes_removed"], 0)

    def test_edge_addition_removal_and_deduplication(self):
        """
        Compares edges by (source, target, type) tuples.
        Repeated edge tuples in input are deduplicated in additions/removals.
        """
        old_graph = {
            "nodes": [],
            "edges": [
                {"source": "app", "target": "utils", "type": "imports", "line": 2},
                {"source": "app", "target": "os", "type": "imports", "line": 1},
            ],
        }
        new_graph = {
            "nodes": [],
            "edges": [
                {"source": "app", "target": "utils", "type": "imports", "line": 5},
                # Duplicate calls in source code (e.g. line 10 and line 20)
                {"source": "app.main", "target": "utils.notify", "type": "calls", "line": 10},
                {"source": "app.main", "target": "utils.notify", "type": "calls", "line": 20},
            ],
        }

        result = diff_graphs(old_graph, new_graph)

        # Removed: app -> os (imports)
        self.assertEqual(len(result["edges_removed"]), 1)
        self.assertEqual(result["edges_removed"][0]["target"], "os")
        self.assertEqual(result["edges_removed"][0]["type"], "imports")

        # Added: app.main -> utils.notify (calls) - deduplicated to 1
        self.assertEqual(len(result["edges_added"]), 1)
        self.assertEqual(result["edges_added"][0]["source"], "app.main")
        self.assertEqual(result["edges_added"][0]["target"], "utils.notify")
        self.assertEqual(result["edges_added"][0]["type"], "calls")

        self.assertEqual(result["summary"]["edges_added"], 1)
        self.assertEqual(result["summary"]["edges_removed"], 1)


class TestGetGraphAtRevision(unittest.TestCase):
    """
    Tests get_graph_at_revision extracting directly from git object storage.
    """

    def setUp(self):
        self.temp_repo_dir = tempfile.mkdtemp(prefix="test_git_repo_")
        self.repo = git.Repo.init(self.temp_repo_dir)
        # Configure test author
        self.repo.config_writer().set_value("user", "name", "Test Committer").release()
        self.repo.config_writer().set_value("user", "email", "test@test.local").release()

    def tearDown(self):
        self.repo.close()
        shutil.rmtree(self.temp_repo_dir, ignore_errors=True)

    def test_extract_graph_at_commit_without_working_tree_mutation(self):
        repo_path = Path(self.temp_repo_dir)

        # Commit 1
        (repo_path / "mod_a.py").write_text("def func_a(): pass\n", encoding="utf-8")
        self.repo.index.add(["mod_a.py"])
        commit1 = self.repo.index.commit("Commit 1: Add mod_a")

        # Commit 2
        (repo_path / "mod_b.py").write_text("import mod_a\ndef func_b(): mod_a.func_a()\n", encoding="utf-8")
        self.repo.index.add(["mod_b.py"])
        commit2 = self.repo.index.commit("Commit 2: Add mod_b")

        # Dirty the working tree (should NOT affect get_graph_at_revision)
        (repo_path / "mod_a.py").write_text("SYNTAX ERROR !!!", encoding="utf-8")

        # Get graph at commit 1
        graph1 = get_graph_at_revision(str(repo_path), commit1.hexsha)
        self.assertEqual(graph1["files_scanned"], 1)
        nodes1 = {n["id"] for n in graph1["nodes"]}
        self.assertIn("mod_a", nodes1)
        self.assertIn("mod_a.func_a", nodes1)
        self.assertNotIn("mod_b", nodes1)

        # Get graph at commit 2
        graph2 = get_graph_at_revision(str(repo_path), commit2.hexsha)
        self.assertEqual(graph2["files_scanned"], 2)
        nodes2 = {n["id"] for n in graph2["nodes"]}
        self.assertIn("mod_a", nodes2)
        self.assertIn("mod_b", nodes2)
        self.assertIn("mod_b.func_b", nodes2)

        # Confirm working tree file is still dirty (was NOT touched)
        self.assertEqual((repo_path / "mod_a.py").read_text(encoding="utf-8"), "SYNTAX ERROR !!!")


class TestEndToEndSamplePackageDiff(unittest.TestCase):
    """
    End-to-end verification of Phase 3 against a throwaway git repository initialized
    from sample_package:
    1. Commit 1: sample_package committed as-is (with unused import os in app.py)
    2. Commit 2:
       - add new function to utils.py (notify)
       - call utils.notify from app.py's main()
       - remove unused import os from app.py
    3. Run diff_graphs and verify:
       - 1 node added: utils.notify
       - 0 nodes removed
       - 2 edges added: contains (utils -> utils.notify), calls (main -> utils.notify)
       - 1 edge removed: imports (app -> os)
       - nothing else falsely flagged as changed
    4. Run CLI diff_graph.py and verify human-readable summary and JSON output.
    """

    def setUp(self):
        self.repo_root = Path(__file__).parent.resolve()
        self.sample_src = self.repo_root / "sample_package"
        self.temp_repo_dir = tempfile.mkdtemp(prefix="sample_pkg_git_")
        self.repo_path = Path(self.temp_repo_dir)

        # Copy sample_package files into throwaway git repo
        for item in self.sample_src.glob("*.py"):
            shutil.copy2(item, self.repo_path / item.name)

        # Ensure app.py has import os in Commit 1
        app_py = self.repo_path / "app.py"
        app_content = app_py.read_text(encoding="utf-8")
        if "import os" not in app_content:
            app_py.write_text("import os\n" + app_content, encoding="utf-8")

        # Initialize git repo and commit
        self.repo = git.Repo.init(self.temp_repo_dir)
        self.repo.config_writer().set_value("user", "name", "Test Committer").release()
        self.repo.config_writer().set_value("user", "email", "test@test.local").release()

        self.repo.index.add(["app.py", "base.py", "utils.py"])
        self.commit1 = self.repo.index.commit("Commit 1: Initial sample package with os import")

        # Commit 2: Add notify() to utils.py, call from app.main(), remove import os
        utils_py = self.repo_path / "utils.py"
        utils_content = utils_py.read_text(encoding="utf-8")
        utils_content += "\n\ndef notify(msg: str) -> str:\n    return f'[NOTIFY] {msg}'\n"
        utils_py.write_text(utils_content, encoding="utf-8")

        # In app.py, remove import os, call utils.notify from main()
        app_lines = app_py.read_text(encoding="utf-8").splitlines()
        app_lines = [line for line in app_lines if line.strip() != "import os"]
        new_app_content = "\n".join(app_lines)
        # Update main() to call utils.notify
        new_app_content = new_app_content.replace(
            "return app.run()",
            "utils.notify('running')\n    return app.run()",
        )
        app_py.write_text(new_app_content, encoding="utf-8")

        self.repo.index.add(["app.py", "utils.py"])
        self.commit2 = self.repo.index.commit("Commit 2: Add notify, call it from main, remove os import")

    def tearDown(self):
        self.repo.close()
        shutil.rmtree(self.temp_repo_dir, ignore_errors=True)

    def test_end_to_end_diff_graphs(self):
        """
        Verify programmatic diff_graphs between HEAD~1 and HEAD.
        """
        graph_old = get_graph_at_revision(str(self.repo_path), "HEAD~1")
        graph_new = get_graph_at_revision(str(self.repo_path), "HEAD")

        diff = diff_graphs(graph_old, graph_new)
        summary = diff["summary"]

        # Confirm 1 node added: utils.notify
        self.assertEqual(summary["nodes_added"], 1)
        self.assertEqual(len(diff["nodes_added"]), 1)
        added_node = diff["nodes_added"][0]
        self.assertEqual(added_node["id"], "utils.notify")
        self.assertEqual(added_node["type"], "function")

        # Confirm 0 nodes removed
        self.assertEqual(summary["nodes_removed"], 0)
        self.assertEqual(len(diff["nodes_removed"]), 0)

        # Confirm 1 edge removed: app -> os import edge
        self.assertEqual(summary["edges_removed"], 1)
        self.assertEqual(len(diff["edges_removed"]), 1)
        removed_edge = diff["edges_removed"][0]
        self.assertEqual(removed_edge["type"], "imports")
        self.assertEqual(removed_edge["source"], "app")
        self.assertEqual(removed_edge.get("module") or removed_edge.get("target"), "os")

        # Confirm 2 edges added: contains (utils -> utils.notify), calls (main -> utils.notify)
        self.assertEqual(summary["edges_added"], 2)
        self.assertEqual(len(diff["edges_added"]), 2)
        added_edge_types = {(e["source"], e["target"], e["type"]) for e in diff["edges_added"]}
        self.assertIn(("utils", "utils.notify", "contains"), added_edge_types)
        self.assertIn(("main", "utils.notify", "calls"), added_edge_types)

    def test_cli_diff_graph(self):
        """
        Verify CLI invocation diff_graph.py <repo> [from_rev] [to_rev] -o output.json
        """
        cli_script = self.repo_root / "diff_graph.py"
        output_json = self.repo_path / "diff_output.json"

        # Explicit revisions
        proc = subprocess.run(
            [
                sys.executable,
                str(cli_script),
                str(self.repo_path),
                "HEAD~1",
                "HEAD",
                "-o",
                str(output_json),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        expected_summary = "1 nodes added, 0 removed, 2 edges added, 1 removed"
        self.assertEqual(proc.stdout.strip(), expected_summary)
        self.assertTrue(output_json.exists())

        with open(output_json, "r", encoding="utf-8") as f:
            diff_data = json.load(f)

        self.assertEqual(diff_data["summary"]["nodes_added"], 1)
        self.assertEqual(diff_data["summary"]["nodes_removed"], 0)
        self.assertEqual(diff_data["summary"]["edges_added"], 2)
        self.assertEqual(diff_data["summary"]["edges_removed"], 1)
        self.assertEqual(diff_data["nodes_added"][0]["id"], "utils.notify")

        # Default revisions (omitted from_rev and to_rev default to HEAD~1 and HEAD)
        output_default = self.repo_path / "default_out.json"
        proc_default = subprocess.run(
            [
                sys.executable,
                str(cli_script),
                str(self.repo_path),
                "-o",
                str(output_default),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(proc_default.stdout.strip(), expected_summary)
        self.assertTrue(output_default.exists())


if __name__ == "__main__":
    unittest.main()
