"""Reporting utilities for the OG-NSD pipeline."""
from __future__ import annotations

import json
from dataclasses import asdict
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
    iterations: Optional[List[Dict[str, Any]]] = None,
    patch_notes: Optional[List[str]] = None,
    unmatched_split_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "llm_notes": llm_response.reasoning_notes,
        "token_usage": llm_response.token_usage,
        "few_shot_exemplars": llm_response.exemplar_ids,
        "shacl": {
            "conforms": shacl_report.conforms,
            "text_report": shacl_report.text_report,
            "results": [asdict(res) for res in shacl_report.results],
        },
    }
    if cq_results is not None:
        report["competency_questions"] = [asdict(result) for result in cq_results]
    if reasoner_report is not None:
        report["reasoner"] = asdict(reasoner_report)
    if iterations is not None:
        report["iterations"] = [
            {
                "iteration": item["iteration"],
                "conforms": item["conforms"],
                "shacl": {
                    "conforms": item["shacl"].conforms,
                    "text_report": item["shacl"].text_report,
                    "results": [asdict(res) for res in item["shacl"].results],
                },
                "reasoner": asdict(item["reasoner"]) if item["reasoner"] else None,
                "cq_results": [asdict(r) for r in item["cq_results"]]
                if item["cq_results"]
                else None,
            }
            for item in iterations
        ]
    if patch_notes:
        report["patch_notes"] = patch_notes
    if unmatched_split_ids:
        report["unmatched_split_ids"] = unmatched_split_ids
    return report


def save_report(report: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
