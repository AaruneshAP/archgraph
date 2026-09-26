"""
Unit and integration tests for Phase 5 Vercel Serverless Function (api/analyze.py).
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from api.analyze import parse_github_url, handler


class TestApiAnalyze(unittest.TestCase):
    def test_parse_github_url(self):
        # Full URLs
        self.assertEqual(
            parse_github_url("https://github.com/pallets/click"),
            ("pallets", "click"),
        )
        self.assertEqual(
            parse_github_url("http://github.com/pallets/click/"),
            ("pallets", "click"),
        )
        self.assertEqual(
            parse_github_url("https://github.com/pallets/click.git"),
            ("pallets", "click"),
        )
        self.assertEqual(
            parse_github_url("github.com/pallets/click"),
            ("pallets", "click"),
        )

        # Shorthand
        self.assertEqual(
            parse_github_url("pallets/click"),
            ("pallets", "click"),
        )

        # URLs with branch/tree path
        self.assertEqual(
            parse_github_url("https://github.com/pallets/click/tree/main"),
            ("pallets", "click"),
        )

        # Invalid URLs
        self.assertIsNone(parse_github_url(""))
        self.assertIsNone(parse_github_url("https://gitlab.com/owner/repo"))
        self.assertIsNone(parse_github_url("just-a-string"))

    def test_in_memory_build_graph(self):
        """
        Verify that build_graph_from_sources produces nodes and edges from in-memory code.
        """
        from codebase_graph import build_graph_from_sources

        sources = {
            "app.py": "from utils import helper\ndef main(): return helper()\n",
            "utils.py": "def helper(): return 42\n",
        }
        graph, files_scanned, nodes, edges, errors = build_graph_from_sources(sources)
        self.assertEqual(files_scanned, 2)
        self.assertEqual(errors, 0)
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn("app", node_ids)
        self.assertIn("app.main", node_ids)
        self.assertIn("utils", node_ids)
        self.assertIn("utils.helper", node_ids)

        edge_pairs = {(e["source"], e["target"], e["type"]) for e in graph["edges"]}
        self.assertIn(("app", "utils.helper", "imports"), edge_pairs)
        self.assertIn(("main", "helper", "calls"), edge_pairs)

    def test_nonexistent_repo_error(self):
        """
        Verify that attempting to fetch a nonexistent repo returns a 404 error tuple.
        """
        from api.analyze import fetch_repo_tree
        tree, err = fetch_repo_tree("nonexistent-user-12345", "fake-repo-98765", None)
        self.assertIsNone(tree)
        self.assertIsNotNone(err)
        status_code, msg = err
        self.assertEqual(status_code, 404)
        self.assertEqual(msg, "Repo not found or private")

    @patch("api.analyze.fetch_repo_tree")
    def test_zero_python_files_error(self, mock_fetch_tree):
        """
        Verify that a repo with no .py files returns 'No Python files found in this repo'.
        """
        # Mock tree with only markdown files
        mock_fetch_tree.return_value = (
            [
                {"path": "README.md", "type": "blob"},
                {"path": "LICENSE", "type": "blob"},
            ],
            None,
        )

        import io
        from api.analyze import handler

        mock_req = MagicMock()
        mock_req.makefile.return_value = io.BytesIO(b'{"url": "https://github.com/foo/bar"}')
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = MagicMock()

        # Instantiate handler and intercept send_json
        sent_status = None
        sent_data = None

        def capture_json(status, data):
            nonlocal sent_status, sent_data
            sent_status = status
            sent_data = data

        with patch.object(handler, "__init__", lambda self, *args, **kwargs: None):
            h = handler()
            h.headers = {"Content-Length": "38"}
            h.rfile = io.BytesIO(b'{"url": "https://github.com/foo/bar"}')
            h.send_json = capture_json
            h.do_POST()

        self.assertEqual(sent_status, 400)
        self.assertEqual(sent_data, {"error": "No Python files found in this repo"})

    @patch("urllib.request.urlopen")
    def test_rate_limit_error(self, mock_urlopen):
        """
        Verify that a 403/429 HTTPError from GitHub returns a 429 error tuple with minutes calculation.
        """
        import time
        from email.message import Message
        from urllib.error import HTTPError
        from api.analyze import fetch_repo_tree

        headers = Message()
        headers["x-ratelimit-remaining"] = "0"
        reset_time = int(time.time() + 15 * 60)
        headers["x-ratelimit-reset"] = str(reset_time)

        mock_urlopen.side_effect = HTTPError(
            url="https://api.github.com/repos/foo/bar/git/trees/HEAD?recursive=1",
            code=403,
            msg="rate limit exceeded",
            hdrs=headers,
            fp=None,
        )

        tree, err = fetch_repo_tree("foo", "bar", None)
        self.assertIsNone(tree)
        self.assertIsNotNone(err)
        status_code, msg = err
        self.assertEqual(status_code, 429)
        self.assertIn("GitHub rate limit reached, try again in", msg)

    def test_import_isolation_never_pulls_git_or_diff_graph(self):
        """
        Confirm api/analyze.py's import chain NEVER pulls in diff_graph.py
        or gitpython at module load time.
        """
        import subprocess
        import sys

        code = (
            "import sys\n"
            "import api.analyze\n"
            "assert 'git' not in sys.modules, f'git was imported: {sys.modules[\"git\"]}'\n"
            "assert 'diff_graph' not in sys.modules, f'diff_graph was imported: {sys.modules[\"diff_graph\"]}'\n"
        )
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Import isolation failed: {res.stderr}")

    @patch("api.analyze.fetch_repo_tree")
    @patch("api.analyze.fetch_raw_file")
    def test_rendered_edge_count_in_api_response(self, mock_fetch_raw, mock_fetch_tree):
        """
        Verify that the stats returned by do_POST counts only rendered edges,
        not pre-filtered raw edges.
        """
        import io
        from api.analyze import handler

        mock_fetch_tree.return_value = (
            [
                {"path": "app.py", "type": "blob"},
                {"path": "utils.py", "type": "blob"},
            ],
            None,
        )

        sample_sources = {
            "app.py": "import os\nfrom utils import helper\ndef main():\n    os.getenv('FOO')\n    return helper()\n",
            "utils.py": "def helper():\n    return 42\n",
        }

        def mock_raw(owner, repo, path, token):
            return path, sample_sources.get(path)

        mock_fetch_raw.side_effect = mock_raw

        sent_status = None
        sent_data = None

        def capture_json(status, data):
            nonlocal sent_status, sent_data
            sent_status = status
            sent_data = data

        with patch.object(handler, "__init__", lambda self, *args, **kwargs: None):
            h = handler()
            h.headers = {"Content-Length": "38"}
            h.rfile = io.BytesIO(b'{"url": "https://github.com/foo/bar"}')
            h.send_json = capture_json
            h.do_POST()

        self.assertEqual(sent_status, 200)
        self.assertIsNotNone(sent_data)
        stats = sent_data["stats"]
        # Raw edges include unresolved os.getenv call and module imports,
        # but rendered edges count only the valid diagram edges between known nodes.
        self.assertIn("edges", stats)
        # There are 2 rendered edges: contains app->main, contains utils->helper, imports app->utils.helper, calls main->helper
        self.assertGreater(stats["edges"], 0)
        # Verify edge count matches actual edge lines in returned Mermaid string
        lines = [l.strip() for l in sent_data["mermaid"].splitlines()]
        mermaid_edges = [l for l in lines if (" --> " in l or " -.- " in l) and not l.startswith("%%") and not "classDef" in l and not "linkStyle" in l]
        self.assertEqual(stats["edges"], len(mermaid_edges))

    @patch("api.analyze.fetch_repo_tree")
    @patch("api.analyze.fetch_raw_file")
    def test_api_collapse_stats_tier1_and_tier2(self, mock_fetch_raw, mock_fetch_tree):
        """
        Verify that do_POST correctly reports collapse stats for:
        - Tier 1 (functions-hidden): total > 150, but modules + classes <= 150.
        - Tier 2 (functions-and-classes-hidden): modules + classes still > 150.
        """
        import io
        from api.analyze import handler

        # 1. Tier 1: 20 files, each has 2 classes and 6 functions = 20 mods + 40 classes + 120 funcs = 180 nodes (>150)
        # mod + class = 60 <= 150 -> functions-hidden
        tree_entries_t1 = [{"path": f"mod_{i}.py", "type": "blob"} for i in range(20)]
        mock_fetch_tree.return_value = (tree_entries_t1, None)

        def mock_raw_t1(owner, repo, path, token):
            return path, "class A: pass\nclass B: pass\ndef f1(): pass\ndef f2(): pass\ndef f3(): pass\ndef f4(): pass\ndef f5(): pass\ndef f6(): pass\n"

        mock_fetch_raw.side_effect = mock_raw_t1

        sent_status = None
        sent_data = None

        def capture_json(status, data):
            nonlocal sent_status, sent_data
            sent_status = status
            sent_data = data

        body = b'{"url": "https://github.com/foo/tier1-repo"}'
        with patch.object(handler, "__init__", lambda self, *args, **kwargs: None):
            h = handler()
            h.headers = {"Content-Length": str(len(body))}
            h.rfile = io.BytesIO(body)
            h.send_json = capture_json
            h.do_POST()

        self.assertEqual(sent_status, 200)
        stats = sent_data["stats"]
        self.assertTrue(stats["collapsed"])
        self.assertEqual(stats["collapse_level"], "functions-hidden")
        self.assertEqual(stats["functions_hidden"], 120)
        self.assertEqual(stats["classes_hidden"], 0)
        self.assertEqual(stats["nodes"], 60)  # 20 modules + 40 classes
        self.assertEqual(stats["raw_nodes"], 180)
        self.assertIn("Showing modules and classes only", stats["banner_text"])
        self.assertNotIn("FUNCTION", sent_data["mermaid"])
        self.assertIn("CLASS", sent_data["mermaid"])

        # 2. Tier 2: 50 files, each has 4 classes and 2 functions = 50 mods + 200 classes + 100 funcs = 350 nodes (>150)
        # mod + class = 250 > 150 -> functions-and-classes-hidden
        tree_entries_t2 = [{"path": f"mod_{i}.py", "type": "blob"} for i in range(50)]
        mock_fetch_tree.return_value = (tree_entries_t2, None)

        def mock_raw_t2(owner, repo, path, token):
            return path, "class A: pass\nclass B: pass\nclass C: pass\nclass D: pass\ndef f1(): pass\ndef f2(): pass\n"

        mock_fetch_raw.side_effect = mock_raw_t2

        body2 = b'{"url": "https://github.com/foo/tier2-repo"}'
        with patch.object(handler, "__init__", lambda self, *args, **kwargs: None):
            h = handler()
            h.headers = {"Content-Length": str(len(body2))}
            h.rfile = io.BytesIO(body2)
            h.send_json = capture_json
            h.do_POST()

        self.assertEqual(sent_status, 200)
        stats2 = sent_data["stats"]
        self.assertTrue(stats2["collapsed"])
        self.assertEqual(stats2["collapse_level"], "functions-and-classes-hidden")
        self.assertEqual(stats2["functions_hidden"], 100)
        self.assertEqual(stats2["classes_hidden"], 200)
        self.assertEqual(stats2["nodes"], 50)  # 50 modules only
        self.assertEqual(stats2["raw_nodes"], 350)
        self.assertIn("Showing modules only — 200 classes and 100 functions hidden", stats2["banner_text"])
        self.assertNotIn("FUNCTION", sent_data["mermaid"])
        self.assertNotIn("CLASS", sent_data["mermaid"])
        self.assertIn("MODULE", sent_data["mermaid"])


if __name__ == "__main__":
    unittest.main()
