import argparse
import os
from dotenv import load_dotenv
import sys

# Ensure the project root is on the Python path when executed directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ontology_guided.data_loader import DataLoader
from ontology_guided.llm_interface import LLMInterface
from ontology_guided.ontology_builder import OntologyBuilder
from ontology_guided.validator import SHACLValidator
from ontology_guided.repair_loop import RepairLoop

PROMPT_TEMPLATE = (
    "Convert the following requirement into OWL axioms in Turtle syntax:\n\n"
    "Requirement: {sentence}\n\nOWL:"
)


def run_pipeline(inputs, shapes, base_iri, ontologies=None, model="gpt-4", repair=False, reason=False):
    """Execute the ontology drafting pipeline.

    Parameters mirror the command line flags used in ``main``. The function now
    returns a dictionary describing the intermediate artefacts so callers such
    as the web interface can display each stage to the user.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env")

    pipeline = {}

    loader = DataLoader()
    texts = loader.load_requirements(inputs)
    pipeline["texts"] = texts
    sentences = []
    for text in texts:
        sentences.extend(loader.preprocess_text(text))
    if not sentences:
        raise RuntimeError("No requirements found in inputs")
    pipeline["sentences"] = sentences

    builder = OntologyBuilder(base_iri, ontology_files=ontologies)
    avail_terms = builder.get_available_terms()

    llm = LLMInterface(api_key=api_key, model=model)
    owl_snippets = llm.generate_owl(sentences, PROMPT_TEMPLATE, available_terms=avail_terms)
    pipeline["owl_snippets"] = owl_snippets

    os.makedirs("results", exist_ok=True)
    for snippet in owl_snippets:
        builder.parse_turtle(snippet)
    builder.save("results/combined.ttl", fmt="turtle")
    builder.save("results/combined.owl", fmt="xml")
    pipeline["combined_ttl"] = "results/combined.ttl"
    pipeline["combined_owl"] = "results/combined.owl"
    print("Saved results/combined.ttl and results/combined.owl")

    if reason:
        from ontology_guided.reasoner import run_reasoner, ReasonerError
        print("Running OWL reasoner...")
        try:
            run_reasoner(pipeline["combined_owl"])
            pipeline["reasoner"] = "OWL reasoning completed successfully."
        except ReasonerError as exc:
            print(exc)
            pipeline["reasoner"] = f"Reasoner error: {exc}"

    validator = SHACLValidator(pipeline["combined_ttl"], shapes)
    conforms, report_text, _ = validator.run_validation()
    print("Conforms:", conforms)
    print(report_text)
    pipeline["shacl_conforms"] = conforms
    pipeline["shacl_report"] = report_text

    if not conforms and repair:
        print("Running repair loop...")
        repairer = RepairLoop(pipeline["combined_ttl"], shapes, api_key)
        repairer.run()
        pipeline["repaired_ttl"] = "results/repaired.ttl"

    return pipeline


def main():
    parser = argparse.ArgumentParser(description="Run the OWL generation pipeline")
    parser.add_argument("--inputs", nargs="+", default=["demo.txt"], help="Requirement files (.txt/.docx)")
    parser.add_argument("--shapes", default="shapes.ttl", help="SHACL shapes file")
    parser.add_argument("--base-iri", default="http://example.com/atm#", help="Base IRI for ontology")
    parser.add_argument("--ontologies", nargs="*", default=[], help="Additional ontology files to load")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model")
    parser.add_argument("--repair", action="store_true", help="Run repair loop if validation fails")
    parser.add_argument("--reason", action="store_true", help="Run OWL reasoner before validation")
    args = parser.parse_args()

    run_pipeline(
        args.inputs,
        args.shapes,
        args.base_iri,
        ontologies=args.ontologies,
        model=args.model,
        repair=args.repair,
        reason=args.reason,
    )

if __name__ == "__main__":
    main()
