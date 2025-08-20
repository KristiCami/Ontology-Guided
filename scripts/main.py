import argparse
import os
from dotenv import load_dotenv
import sys
import logging

# Ensure the project root is on the Python path when executed directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ontology_guided.data_loader import DataLoader, clean_text
from ontology_guided.llm_interface import LLMInterface
from ontology_guided.ontology_builder import OntologyBuilder, InvalidTurtleError
from ontology_guided.validator import SHACLValidator
from ontology_guided.repair_loop import RepairLoop

PROMPT_TEMPLATE = (
    "Convert the following requirement into OWL axioms in Turtle syntax:\n\n"
    "Requirement: {sentence}\n\nOWL:"
)

# Default ontology locations used by optional command-line flags
ONTOLOGIES_DIR = os.path.join(PROJECT_ROOT, "ontologies")
RBO_ONTOLOGY_PATH = os.path.join(ONTOLOGIES_DIR, "rbo.ttl")
LEXICAL_ONTOLOGY_PATH = os.path.join(ONTOLOGIES_DIR, "lexical.ttl")


def run_pipeline(
    inputs,
    shapes,
    base_iri,
    ontologies=None,
    ontology_dir=None,
    model="gpt-4",
    repair=False,
    kmax=5,
    reason=False,
    spacy_model="en_core_web_sm",
    inference="rdfs",
    load_rbo=False,
    load_lexical=False,
):
    """Execute the ontology drafting pipeline.

    Parameters mirror the command line flags used in ``main``. The function now
    returns a dictionary describing the intermediate artefacts so callers such
    as the web interface can display each stage to the user. When ``load_rbo``
    or ``load_lexical`` are ``True``, the predefined ontology files at
    ``RBO_ONTOLOGY_PATH`` and ``LEXICAL_ONTOLOGY_PATH`` are included
    automatically.  ``ontology_dir`` allows specifying a directory from which
    all ``.ttl`` files will be loaded as additional ontologies. ``kmax`` sets
    the maximum number of repair iterations, while ``reason`` and ``inference``
    control reasoning behaviour within the repair loop.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env")

    pipeline = {}
    failed_snippets = pipeline["failed_snippets"] = []

    loader = DataLoader(spacy_model=spacy_model)
    texts_iter = loader.load_requirements(inputs)
    pipeline["texts"] = []

    # Store only a small preview of sentences for display purposes
    sentences_preview = pipeline["sentences"] = []
    PREVIEW_LIMIT = 20

    def sentence_iterator():
        for text in texts_iter:
            pipeline["texts"].append(text)
            lines = (line for line in text.splitlines() if line.strip())
            cleaned_iter = (clean_text(line) for line in lines)
            for doc in loader.nlp.pipe(cleaned_iter, batch_size=100, n_process=1):
                for sent in doc.sents:
                    sent_text = sent.text.strip()
                    if len(sentences_preview) < PREVIEW_LIMIT:
                        sentences_preview.append(sent_text)
                    yield sent_text
    sentences_iter = sentence_iterator()

    ontology_files = list(ontologies or [])
    if ontology_dir:
        for name in os.listdir(ontology_dir):
            if name.endswith(".ttl"):
                ontology_files.append(os.path.join(ontology_dir, name))
    if load_rbo:
        ontology_files.append(RBO_ONTOLOGY_PATH)
    if load_lexical:
        ontology_files.append(LEXICAL_ONTOLOGY_PATH)

    builder = OntologyBuilder(base_iri, ontology_files=ontology_files)
    logger = logging.getLogger(__name__)
    avail_terms = builder.get_available_terms()

    llm = LLMInterface(api_key=api_key, model=model)

    snippets_preview = pipeline["owl_snippets"] = []
    BATCH_SIZE = 100

    os.makedirs("results", exist_ok=True)
    batch: list[str] = []
    any_sentence = False
    snippet_counter = 0
    for sentence in sentences_iter:
        any_sentence = True
        batch.append(sentence)
        if len(batch) >= BATCH_SIZE:
            owl_batch = llm.generate_owl(
                batch, PROMPT_TEMPLATE, available_terms=avail_terms
            )
            for sent, snippet in zip(batch, owl_batch):
                if len(snippets_preview) < PREVIEW_LIMIT:
                    snippets_preview.append(snippet)
                snippet_counter += 1
                try:
                    triples = builder.parse_turtle(
                        snippet,
                        logger=logger,
                        requirement=sent,
                        snippet_index=snippet_counter,
                    )
                    builder.add_provenance(sent, triples)
                except InvalidTurtleError:
                    logger.warning(
                        "Skipping invalid OWL snippet for sentence: %s", sent
                    )
                    failed_snippets.append({"sentence": sent, "snippet": snippet})
            batch = []
    if batch:
        owl_batch = llm.generate_owl(batch, PROMPT_TEMPLATE, available_terms=avail_terms)
        for sent, snippet in zip(batch, owl_batch):
            if len(snippets_preview) < PREVIEW_LIMIT:
                snippets_preview.append(snippet)
            snippet_counter += 1
            try:
                triples = builder.parse_turtle(
                    snippet,
                    logger=logger,
                    requirement=sent,
                    snippet_index=snippet_counter,
                )
                builder.add_provenance(sent, triples)
            except InvalidTurtleError:
                logger.warning(
                    "Skipping invalid OWL snippet for sentence: %s", sent
                )
                failed_snippets.append({"sentence": sent, "snippet": snippet})
        any_sentence = True
    if not any_sentence:
        raise RuntimeError("No requirements found in inputs")
    builder.save("results/combined.ttl", fmt="turtle")
    builder.save("results/combined.owl", fmt="xml")
    pipeline["combined_ttl"] = "results/combined.ttl"
    pipeline["combined_owl"] = "results/combined.owl"
    pipeline["provenance"] = builder.triple_provenance
    logger.info("Saved results/combined.ttl and results/combined.owl")

    validator = SHACLValidator(pipeline["combined_ttl"], shapes, inference=inference)
    conforms, report = validator.run_validation()
    logger.info("Conforms: %s", conforms)
    logger.info("SHACL Report: %s", report)
    pipeline["shacl_conforms"] = conforms
    pipeline["shacl_report"] = report

    if not conforms and repair:
        logger.info("Running repair loop...")
        repairer = RepairLoop(pipeline["combined_ttl"], shapes, api_key, kmax=kmax)
        repairer.run(reason=reason, inference=inference)
        pipeline["repaired_ttl"] = "results/repaired.ttl"

    return pipeline


def main():
    parser = argparse.ArgumentParser(description="Run the OWL generation pipeline")
    parser.add_argument("--inputs", nargs="+", default=["demo.txt"], help="Requirement files (.txt/.docx)")
    parser.add_argument("--shapes", default="shapes.ttl", help="SHACL shapes file")
    parser.add_argument("--base-iri", default="http://example.com/atm#", help="Base IRI for ontology")
    parser.add_argument("--ontologies", nargs="*", default=[], help="Additional ontology files to load")
    parser.add_argument(
        "--ontology-dir",
        default=None,
        help="Directory from which to load all .ttl ontology files",
    )
    parser.add_argument("--rbo", action="store_true", help="Include the RBO ontology")
    parser.add_argument("--lexical", action="store_true", help="Include the lexical ontology")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model")
    parser.add_argument("--repair", action="store_true", help="Run repair loop if validation fails")
    parser.add_argument("--kmax", type=int, default=5, help="Maximum repair iterations")
    parser.add_argument(
        "--reason",
        action="store_true",
        help="Run OWL reasoner during repair loop",
    )
    parser.add_argument(
        "--spacy-model",
        default="en_core_web_sm",
        help="spaCy model for sentence segmentation",
    )
    parser.add_argument(
        "--inference",
        default="rdfs",
        choices=["none", "rdfs", "owlrl"],
        help="Inference to apply during SHACL validation and repair loop",
    )
    args = parser.parse_args()

    run_pipeline(
        args.inputs,
        args.shapes,
        args.base_iri,
        ontologies=args.ontologies,
        ontology_dir=args.ontology_dir,
        model=args.model,
        repair=args.repair,
        kmax=args.kmax,
        reason=args.reason,
        spacy_model=args.spacy_model,
        inference=args.inference,
        load_rbo=args.rbo,
        load_lexical=args.lexical,
    )

if __name__ == "__main__":
    main()
