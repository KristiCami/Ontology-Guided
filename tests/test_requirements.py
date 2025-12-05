"""Tests for requirement ingestion utilities."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from og_nsd.requirements import RequirementLoader


class RequirementLoaderTests(unittest.TestCase):
    def _write_requirement_file(self, content: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "reqs.jsonl"
        path.write_text(content)
        return path

    def test_uses_description_when_text_missing(self) -> None:
        path = self._write_requirement_file('{"id": "1", "description": "Fallback requirement"}')

        requirement = RequirementLoader(path).load()[0]

        self.assertEqual("Fallback requirement", requirement.text)

    def test_prefers_text_over_description(self) -> None:
        path = self._write_requirement_file(
            '{"id": "2", "text": "Primary text", "description": "Secondary description"}'
        )

        requirement = RequirementLoader(path).load()[0]

        self.assertEqual("Primary text", requirement.text)


if __name__ == "__main__":
    unittest.main()
