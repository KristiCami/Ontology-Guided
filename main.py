import argparse
import os
from dotenv import load_dotenv
from data_loader import DataLoader
from llm_interface import LLMInterface
from ontology_builder import OntologyBuilder
from validator import SHACLValidator
from repair_loop import RepairLoop

PROMPT_TEMPLATE = (
    "Convert the following requirement into OWL axioms in Turtle syntax:\n\n"
    "Requirement: {sentence}\n\nOWL:"
)


def run_pipeline(inputs, shapes, base_iri, model="gpt-4", repair=False):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env")

    loader = DataLoader()
    texts = loader.load_requirements(inputs)
    sentences = []
    for text in texts:
        sentences.extend(loader.preprocess_text(text))
    if not sentences:
        raise RuntimeError("No requirements found in inputs")

    llm = LLMInterface(api_key=api_key, model=model)
    owl_snippets = llm.generate_owl(sentences, PROMPT_TEMPLATE)

    os.makedirs("results", exist_ok=True)
    builder = OntologyBuilder(base_iri)
    for snippet in owl_snippets:
        builder.parse_turtle(snippet)
    builder.save("results/combined.ttl", fmt="turtle")
    builder.save("results/combined.owl", fmt="xml")
    print("Saved results/combined.ttl and results/combined.owl")

    validator = SHACLValidator("results/combined.ttl", shapes)
    conforms, report_text, _ = validator.run_validation()
    print("Conforms:", conforms)
    print(report_text)

    if not conforms and repair:
        print("Running repair loop...")
        repairer = RepairLoop("results/combined.ttl", shapes, api_key)
        repairer.run()


def main():
    parser = argparse.ArgumentParser(description="Run the OWL generation pipeline")
    parser.add_argument("--inputs", nargs="+", default=["demo.txt"], help="Requirement files (.txt/.docx)")
    parser.add_argument("--shapes", default="shapes.ttl", help="SHACL shapes file")
    parser.add_argument("--base-iri", default="http://example.com/atm#", help="Base IRI for ontology")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model")
    parser.add_argument("--repair", action="store_true", help="Run repair loop if validation fails")
    args = parser.parse_args()

    run_pipeline(args.inputs, args.shapes, args.base_iri, model=args.model, repair=args.repair)


if __name__ == "__main__":
    main()
