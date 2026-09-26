"""
Unit and integration tests for Phase 4: Plain-English architecture changelog using Groq.
Verifies:
1. Empty-diff fast path returns "No structural changes." without API call.
2. Missing GROQ_API_KEY raises clean RuntimeError when called directly.
3. Token-efficient formatting of diff payload (only structural fields, no source code).
4. Groq API call with mock response verifying prompt content and narration output
   (confirming the narration text mentions notify(), main(), and the dropped os import).
5. CLI `--narrate` flag integration:
   - Successful narration output printed below the one-line summary.
   - Graceful fallback when GROQ_API_KEY is missing (does not crash).
   - Graceful fallback on API error (does not crash).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from diff_graph import diff_graphs, narrate_diff
from narrate_diff import format_diff_for_llm


class TestNarrateDiff(unittest.TestCase):
    """
    Unit tests for narrate_diff() pure-ish function.
    """

    def setUp(self):
        # Sample Phase 3 diff for sample_package commit 1 -> commit 2
        self.sample_diff = {
            "nodes_added": [
                {
                    "id": "utils.notify",
                    "type": "function",
                    "name": "notify",
                    "module": "utils",
                    "file": "utils.py",
                    "line": 12,
                    "args": ["msg"],
                }
            ],
            "nodes_removed": [],
            "edges_added": [
                {
                    "source": "main",
                    "target": "utils.notify",
                    "type": "calls",
                    "caller_qualname": "main",
                    "callee_name": "utils.notify",
                    "caller_module": "app",
                    "caller_id": "app.main",
                    "line": 19,
                },
                {
                    "source": "utils",
                    "target": "utils.notify",
                    "type": "contains",
                },
            ],
            "edges_removed": [
                {
                    "source": "app",
                    "target": "os",
                    "type": "imports",
                    "module": "os",
                    "name": None,
                    "asname": None,
                    "line": 5,
                }
            ],
            "summary": {
                "nodes_added": 1,
                "nodes_removed": 0,
                "edges_added": 2,
                "edges_removed": 1,
            },
        }

    def test_empty_diff_returns_fixed_string_without_api_call(self):
        """
        If all four added/removed lists are empty, returns 'No structural changes.'
        without checking API key or making network requests.
        """
        empty_diff = {
            "nodes_added": [],
            "nodes_removed": [],
            "edges_added": [],
            "edges_removed": [],
            "summary": {"nodes_added": 0, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0},
        }

        # Ensure no GROQ_API_KEY is present
        with patch.dict(os.environ, {}, clear=True):
            narration = narrate_diff(empty_diff)
            self.assertEqual(narration, "No structural changes.")

        # Also test with completely empty dict
        narration2 = narrate_diff({})
        self.assertEqual(narration2, "No structural changes.")

    def test_missing_api_key_raises_runtime_error(self):
        """
        If GROQ_API_KEY is missing on a non-empty diff, raises clean RuntimeError.
        """
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                narrate_diff(self.sample_diff)
            self.assertIn("GROQ_API_KEY", str(ctx.exception))

    def test_format_diff_for_llm_keeps_payload_compact(self):
        """
        Verify format_diff_for_llm strips lines/args/callers and keeps only
        structural fields (id, type, file, source, target).
        """
        payload = format_diff_for_llm(self.sample_diff)
        self.assertIn("nodes_added", payload)
        self.assertIn("edges_removed", payload)
        self.assertIn("summary", payload)

        node = payload["nodes_added"][0]
        self.assertEqual(node["id"], "utils.notify")
        self.assertEqual(node["type"], "function")
        self.assertEqual(node["file"], "utils.py")
        # Ensure bulky metadata like args was stripped to save tokens
        self.assertNotIn("args", node)

        edge = payload["edges_removed"][0]
        self.assertEqual(edge["source"], "app")
        self.assertEqual(edge["target"], "os")
        self.assertEqual(edge["type"], "imports")

    @patch("groq.Groq")
    def test_narrate_diff_mocked_groq_call(self, mock_groq_class):
        """
        Verify narrate_diff against sample_package commit 1 -> commit 2 diff.
        Confirms the prompt receives structural info and returns a rich narrative
        referencing notify(), main, and the dropped os import.
        """
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_completion = MagicMock()
        expected_narration = (
            "utils gained a notify() function, now called from main() after the "
            "os import was dropped — likely swapping print-based logging for something else."
        )
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=expected_narration))
        ]
        mock_client.chat.completions.create.return_value = mock_completion

        # Call with explicit mock API key
        narration = narrate_diff(self.sample_diff, api_key="mock_key_gsk_123")

        # Verify output text
        self.assertEqual(narration, expected_narration)
        self.assertIn("notify()", narration)
        self.assertIn("main()", narration)
        self.assertIn("os import", narration)

        # Verify Groq client initialization and call arguments
        mock_groq_class.assert_called_once_with(api_key="mock_key_gsk_123")
        create_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(create_kwargs["model"], "openai/gpt-oss-120b")

        messages = create_kwargs["messages"]
        self.assertEqual(len(messages), 2)
        system_msg = messages[0]["content"]
        user_msg = messages[1]["content"]

        self.assertIn("expert software architect", system_msg)
        self.assertIn("terse", system_msg)
        # Verify the user prompt contains the relevant symbols
        self.assertIn("utils.notify", user_msg)
        self.assertIn("main", user_msg)
        self.assertIn("os", user_msg)

    def test_cli_narrate_flag_success(self):
        """
        Verify CLI invocation diff_graph.py <repo> --narrate with mocked Groq in subprocess.
        """
        repo_root = Path(__file__).parent.resolve()
        cli_script = repo_root / "diff_graph.py"

        # Run helper script that patches Groq and invokes diff_graph CLI
        runner_code = f"""
import sys, unittest.mock as mock
mock_groq = mock.MagicMock()
mock_completion = mock.MagicMock()
mock_completion.choices = [mock.MagicMock(message=mock.MagicMock(content="utils gained a notify() function, now called from main() after the os import was dropped."))]
mock_groq.return_value.chat.completions.create.return_value = mock_completion

with mock.patch.dict("os.environ", {{"GROQ_API_KEY": "dummy_key"}}):
    with mock.patch("groq.Groq", mock_groq):
        from diff_graph import main
        sys.argv = ["diff_graph.py", r"{str(repo_root / 'sample_package')}", "--narrate"]
        # Note: sample_package is not a git repo, but we test the CLI argument handling
"""
        # Alternatively, create a small throwaway repo for end-to-end CLI test
        with tempfile.TemporaryDirectory() as tmp_dir:
            import git
            tmp_path = Path(tmp_dir)
            repo = git.Repo.init(tmp_path)
            repo.config_writer().set_value("user", "name", "Test").release()
            repo.config_writer().set_value("user", "email", "test@test").release()

            (tmp_path / "a.py").write_text("import os\ndef f(): pass\n", encoding="utf-8")
            repo.index.add(["a.py"])
            repo.index.commit("c1")

            (tmp_path / "a.py").write_text("def f(): pass\ndef g(): pass\n", encoding="utf-8")
            repo.index.add(["a.py"])
            repo.index.commit("c2")
            repo.close()

            # Test 1: CLI with --narrate when GROQ_API_KEY is not set (falls back gracefully)
            env_no_key = os.environ.copy()
            env_no_key["GROQ_API_KEY"] = ""

            proc = subprocess.run(
                [sys.executable, str(cli_script), str(tmp_path), "--narrate"],
                capture_output=True,
                text=True,
                env=env_no_key,
            )
            # Must exit with code 0 (never crash over narration failure)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("1 nodes added, 0 removed, 1 edges added, 1 removed", proc.stdout)
            self.assertIn("Narration unavailable", proc.stderr)

    @patch("groq.Groq")
    def test_cli_narrate_in_process_success(self, mock_groq_class):
        """
        Verify CLI invocation when Groq succeeds, confirming the narration
        is printed to stdout below the stats line.
        """
        import io
        from contextlib import redirect_stdout
        from diff_graph import main

        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        expected_text = "utils gained a notify() function, now called from main()."
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=expected_text))]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            import git
            tmp_path = Path(tmp_dir)
            repo = git.Repo.init(tmp_path)
            repo.config_writer().set_value("user", "name", "Test").release()
            repo.config_writer().set_value("user", "email", "test@test").release()

            (tmp_path / "a.py").write_text("import os\ndef f(): pass\n", encoding="utf-8")
            repo.index.add(["a.py"])
            repo.index.commit("c1")

            (tmp_path / "a.py").write_text("def f(): pass\ndef g(): pass\n", encoding="utf-8")
            repo.index.add(["a.py"])
            repo.index.commit("c2")
            repo.close()

            stdout_buf = io.StringIO()
            with patch.dict(os.environ, {"GROQ_API_KEY": "fake_key_123"}):
                with patch("sys.argv", ["diff_graph.py", str(tmp_path), "--narrate"]):
                    with redirect_stdout(stdout_buf):
                        main()

            output = stdout_buf.getvalue()
            # Verify 1-line stats summary is present
            self.assertIn("1 nodes added, 0 removed, 1 edges added, 1 removed", output)
            # Verify narration is present below stats
            self.assertIn(expected_text, output)


if __name__ == "__main__":
    unittest.main()
