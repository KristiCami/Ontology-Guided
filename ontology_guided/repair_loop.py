import os
import logging
from dotenv import load_dotenv

from .validator import SHACLValidator
from .llm_interface import LLMInterface
from .ontology_builder import OntologyBuilder
from .reasoner import run_reasoner, ReasonerError

BASE_IRI = "http://example.com/atm#"
SHAPES_FILE = "shapes.ttl"
DATA_FILE = "results/combined.ttl"

PROMPT_TEMPLATE = (
    "Given the SHACL validation report, repair the ontology axioms.\n"
    "Violations:\n{violations}\n\n"
    "Provide additional Turtle triples to fix the violations."
)


class RepairLoop:
    def __init__(
        self,
        data_path: str,
        shapes_path: str,
        api_key: str,
        *,
        kmax: int = 5,
        reason: bool = False,
        inference: str = "rdfs",
    ):
        self.data_path = data_path
        self.shapes_path = shapes_path
        self.kmax = kmax
        self.reason = reason
        self.inference = inference
        self.llm = LLMInterface(api_key=api_key)
        self.builder = OntologyBuilder(BASE_IRI)

    def run(self):
        logger = logging.getLogger(__name__)
        os.makedirs("results", exist_ok=True)
        current_data = self.data_path
        k = 0
        while True:
            validator = SHACLValidator(current_data, self.shapes_path, inference=self.inference)
            conforms, violations = validator.run_validation()
            report_path = os.path.join("results", f"report_{k}.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                if conforms:
                    f.write("Conforms\n")
                else:
                    for v in violations:
                        f.write(
                            f"focusNode: {v['focusNode']}, resultPath: {v['resultPath']}, message: {v['message']}\n"
                        )
            if conforms:
                logger.info("SHACL validation passed on iteration %d", k)
                break
            if k == self.kmax:
                logger.warning("Reached maximum iterations (%d)", self.kmax)
                break

            logger.info("SHACL Violations: %s", violations)
            prompts = []
            for v in violations:
                report_text = (
                    f"focusNode: {v['focusNode']}, resultPath: {v['resultPath']}, message: {v['message']}"
                )
                prompts.append(PROMPT_TEMPLATE.format(violations=report_text))
            repair_snippets = self.llm.generate_owl(prompts, "{sentence}")
            with open(current_data, "r", encoding="utf-8") as f:
                original = f.read()
            merged = original + "\n\n" + "\n\n".join(repair_snippets)
            self.builder = OntologyBuilder(BASE_IRI)
            self.builder.parse_turtle(merged, logger=logger)
            ttl_path = os.path.join("results", f"repaired_{k + 1}.ttl")
            owl_path = os.path.join("results", f"repaired_{k + 1}.owl")
            self.builder.save(ttl_path, fmt="turtle")
            self.builder.save(owl_path, fmt="xml")
            if self.reason:
                try:
                    run_reasoner(owl_path)
                except ReasonerError as exc:
                    logger.warning("Reasoner failed: %s", exc)
            current_data = ttl_path
            k += 1


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env for repair loop.")
    kmax = int(os.getenv("REPAIR_KMAX", 5))
    reason = os.getenv("REPAIR_REASON", "false").lower() == "true"
    inference = os.getenv("REPAIR_INFERENCE", "rdfs")
    repairer = RepairLoop(
        DATA_FILE,
        SHAPES_FILE,
        api_key,
        kmax=kmax,
        reason=reason,
        inference=inference,
    )
    repairer.run()


if __name__ == "__main__":
    main()
