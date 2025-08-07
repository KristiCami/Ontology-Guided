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
    "Report:\n{sentence}\n\n"
    "Provide additional Turtle triples to fix the violations."
)


class RepairLoop:
    def __init__(self, data_path: str, shapes_path: str, api_key: str):
        self.data_path = data_path
        self.shapes_path = shapes_path
        self.llm = LLMInterface(api_key=api_key)
        self.builder = OntologyBuilder(BASE_IRI)

    def run(self):
        validator = SHACLValidator(self.data_path, self.shapes_path)
        conforms, report_text, _ = validator.run_validation()
        if conforms:
            print("No SHACL violations detected. No repair needed.")
            return
        print("SHACL Report:\n", report_text)
        prompt = PROMPT_TEMPLATE.format(sentence=report_text)
        print("Repair prompt:\n", prompt)
        repair_triples = self.llm.generate_owl([prompt], "{sentence}")[0]
        with open(self.data_path, "r", encoding="utf-8") as f:
            original = f.read()
        merged = original + "\n\n" + repair_triples
        logger = logging.getLogger(__name__)
        self.builder.parse_turtle(merged, logger=logger)
        os.makedirs("results", exist_ok=True)
        self.builder.save("results/repaired.ttl", fmt="turtle")
        self.builder.save("results/repaired.owl", fmt="xml")
        print("Repaired ontology saved to results/repaired.ttl and results/repaired.owl")


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env for repair loop.")
    repairer = RepairLoop(DATA_FILE, SHAPES_FILE, api_key)
    repairer.run()


if __name__ == "__main__":
    main()
