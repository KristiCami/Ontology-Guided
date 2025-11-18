"""Reporting utilities for the OG-NSD pipeline."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm import LLMResponse
from .queries import CompetencyQuestionResult
from .reasoning import ReasonerReport
from .shacl import ShaclReport


def build_report(
    llm_response: LLMResponse,
    shacl_report: ShaclReport,
    cq_results: Optional[List[CompetencyQuestionResult]] = None,
    reasoner_report: Optional[ReasonerReport] = None,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "llm_notes": llm_response.reasoning_notes,
        "shacl": {
            "conforms": shacl_report.conforms,
            "text_report": shacl_report.text_report,
        },
    }
    if cq_results is not None:
        report["competency_questions"] = [asdict(result) for result in cq_results]
    if reasoner_report is not None:
        report["reasoner"] = asdict(reasoner_report)
    return report


def save_report(report: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
