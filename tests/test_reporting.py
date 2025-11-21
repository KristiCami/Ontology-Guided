"""Tests for report construction utilities."""

import unittest

from og_nsd.llm import LLMResponse
from og_nsd.reporting import build_report
from og_nsd.shacl import ShaclReport


class BuildReportTests(unittest.TestCase):
    def test_includes_shacl_graph_when_available(self) -> None:
        llm_response = LLMResponse(turtle="", reasoning_notes="notes")
        shacl_report = ShaclReport(
            conforms=True,
            text_report="All good",
            report_graph_ttl="@prefix ex: <http://example.org/> .",
        )

        report = build_report(llm_response=llm_response, shacl_report=shacl_report)

        self.assertEqual(
            "@prefix ex: <http://example.org/> .",
            report["shacl"].get("report_graph_ttl"),
        )


if __name__ == "__main__":
    unittest.main()
