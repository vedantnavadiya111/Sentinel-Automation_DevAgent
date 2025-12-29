import os
import tempfile
import unittest
from pathlib import Path


class TestSentinelMcpServer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        os.environ["WORKSPACE_ROOT"] = str(self.workspace)

        from sentinel_mcp import core

        self.core = core

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_in_workspace_blocks_escape(self) -> None:
        with self.assertRaises(ValueError):
            self.core.resolve_in_workspace("../outside.txt", root=self.workspace)

    def test_apply_patch_requires_unique_match(self) -> None:
        p = self.workspace / "a.txt"
        p.write_text("hello\nhello\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.core.apply_patch_impl(str(p), "hello", "hi", root=self.workspace)

    def test_apply_patch_replaces_single_match(self) -> None:
        p = self.workspace / "b.txt"
        p.write_text("start\nneedle\nend\n", encoding="utf-8")

        result = self.core.apply_patch_impl(str(p), "needle", "replaced", root=self.workspace)
        self.assertTrue(result["replaced"])

        updated = p.read_text(encoding="utf-8")
        self.assertIn("replaced", updated)
        self.assertNotIn("needle\n", updated)


if __name__ == "__main__":
    unittest.main()
