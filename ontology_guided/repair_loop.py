import os
import logging
from dotenv import load_dotenv

from .validator import SHACLValidator
from .llm_interface import LLMInterface
from .ontology_builder import OntologyBuilder

BASE_IRI = "http://example.com/atm#"
SHAPES_FILE = "shapes.ttl"
DATA_FILE = "results/combined.ttl"

PROMPT_TEMPLATE = (
    "Given the SHACL validation report, repair the ontology axioms.\n"
    "Violations:\n{violations}\n\n"
    "Provide additional Turtle triples to fix the violations."
)


class RepairLoop:
    def __init__(self, data_path: str, shapes_path: str, api_key: str):
        self.data_path = data_path
        self.shapes_path = shapes_path
        self.llm = LLMInterface(api_key=api_key)
        self.builder = OntologyBuilder(BASE_IRI)

    def run(self):
        logger = logging.getLogger(__name__)
        validator = SHACLValidator(self.data_path, self.shapes_path)
        conforms, violations = validator.run_validation()
        if conforms:
            logger.info("No SHACL violations detected. No repair needed.")
            return
        logger.info("SHACL Violations: %s", violations)
        report_text = "\n".join(
            f"focusNode: {v['focusNode']}, resultPath: {v['resultPath']}, message: {v['message']}"
            for v in violations
        )
        prompt = PROMPT_TEMPLATE.format(violations=report_text)
        logger.info("Repair prompt:\n%s", prompt)
        repair_triples = self.llm.generate_owl([prompt], "{sentence}")[0]
        with open(self.data_path, "r", encoding="utf-8") as f:
            original = f.read()
        merged = original + "\n\n" + repair_triples
        self.builder.parse_turtle(merged, logger=logger)
        os.makedirs("results", exist_ok=True)
        self.builder.save("results/repaired.ttl", fmt="turtle")
        self.builder.save("results/repaired.owl", fmt="xml")
        logger.info("Repaired ontology saved to results/repaired.ttl and results/repaired.owl")

        repaired_validator = SHACLValidator("results/repaired.ttl", self.shapes_path)
        repaired_conforms, repaired_report = repaired_validator.run_validation()
        if not repaired_conforms:
            logger.error("Remaining SHACL violations:\n%s", repaired_report)
            raise RuntimeError(
                "Repaired ontology still violates SHACL constraints."
            )


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env for repair loop.")
    repairer = RepairLoop(DATA_FILE, SHAPES_FILE, api_key)
    repairer.run()


if __name__ == "__main__":
    main()
