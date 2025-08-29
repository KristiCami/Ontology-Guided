import argparse
import os
from dotenv import load_dotenv
import sys
import logging
import json
from typing import Iterable, Optional, Union

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
    "Convert the following requirement into OWL axioms in Turtle syntax. "
    "Use base IRI {base} and prefix {prefix}.\n\n"
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
    temperature: float = 0.0,
    examples=None,
    repair=False,
    kmax=5,
    reason=False,
    spacy_model="en_core_web_sm",
    inference="rdfs",
    load_rbo=False,
    load_lexical=False,
    use_terms: bool = True,
    validate: bool = True,
    use_async: bool = False,
    strict_terms: bool = False,
    keywords: Optional[Union[Iterable[str], None]] = None,
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
    control reasoning behaviour within the repair loop. ``use_terms`` controls
    whether ontology terms are supplied to the language model. ``validate``
    toggles SHACL validation and the subsequent repair loop. ``strict_terms``
    discards triples that contain unknown ontology terms.
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
            for sent_text in loader.preprocess_text(text, keywords=keywords):
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
    avail_terms = builder.get_available_terms() if use_terms else None

    llm = LLMInterface(
        api_key=api_key,
        model=model,
        temperature=temperature,
        examples=examples,
    )

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
            if use_async:
                owl_batch = llm.async_generate_owl(
                    batch,
                    PROMPT_TEMPLATE,
                    base=base_iri,
                    prefix=builder.prefix,
                    available_terms=avail_terms,
                )
            else:
                owl_batch = llm.generate_owl(
                    batch,
                    PROMPT_TEMPLATE,
                    base=base_iri,
                    prefix=builder.prefix,
                    available_terms=avail_terms,
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
                        strict_terms=strict_terms,
                    )
                    builder.add_provenance(sent, triples)
                    if use_terms:
                        avail_terms = builder.get_available_terms()
                except InvalidTurtleError:
                    logger.warning(
                        "Skipping invalid OWL snippet for sentence: %s", sent
                    )
                    failed_snippets.append({"sentence": sent, "snippet": snippet})
            batch = []
    if batch:
        if use_async:
            owl_batch = llm.async_generate_owl(
                batch,
                PROMPT_TEMPLATE,
                base=base_iri,
                prefix=builder.prefix,
                available_terms=avail_terms,
            )
        else:
            owl_batch = llm.generate_owl(
                batch,
                PROMPT_TEMPLATE,
                base=base_iri,
                prefix=builder.prefix,
                available_terms=avail_terms,
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
                    strict_terms=strict_terms,
                )
                builder.add_provenance(sent, triples)
                if use_terms:
                    avail_terms = builder.get_available_terms()
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

    if reason:
        try:
            from ontology_guided.reasoner import run_reasoner

            _, is_consistent, inconsistent = run_reasoner(pipeline["combined_owl"])
            inconsistent_path = os.path.join("results", "inconsistent_classes.txt")
            with open(inconsistent_path, "w", encoding="utf-8") as f:
                for iri in inconsistent:
                    f.write(iri + "\n")
            logger.info(
                "Consistency: %s, Unsatisfiable classes: %d",
                is_consistent,
                len(inconsistent),
            )
            pipeline["reasoning_log"] = "Reasoner completed successfully"
            pipeline["inconsistent_classes"] = {
                "path": inconsistent_path,
                "iris": inconsistent,
                "count": len(inconsistent),
            }
            pipeline["is_consistent"] = is_consistent
        except Exception as exc:  # pragma: no cover - log unexpected errors
            pipeline["reasoning_log"] = str(exc)

    if validate:
        validator = SHACLValidator(pipeline["combined_ttl"], shapes, inference=inference)
        conforms, report, summary = validator.run_validation()
        logger.info("Conforms: %s", conforms)
        logger.info("SHACL Report: %s", report)
        shacl_report_path = "results/shacl_report.txt"
        with open(shacl_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        pipeline["shacl_conforms"] = conforms
        pipeline["shacl_report"] = report
        pipeline["shacl_report_path"] = shacl_report_path
        pipeline["shacl_summary"] = summary

        if not conforms and repair:
            logger.info("Running repair loop...")
            repairer = RepairLoop(
                pipeline["combined_ttl"], shapes, api_key, kmax=kmax, base_iri=base_iri
            )
            repaired_ttl, repaired_report, violations, stats = repairer.run(
                reason=reason, inference=inference
            )
            logger.info("Repair loop stats: %s", stats)
            pipeline["repaired_report"] = {"path": repaired_report, "violations": violations}
            pipeline["violation_stats"] = stats
            if repaired_ttl:
                pipeline["repaired_ttl"] = repaired_ttl
    else:
        pipeline["shacl_conforms"] = None
        pipeline["shacl_report"] = {}
        pipeline["shacl_report_path"] = None

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
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for the language model",
    )
    parser.add_argument(
        "--examples",
        default=None,
        help="Path to JSON file with few-shot examples",
    )
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
    parser.add_argument(
        "--no-terms",
        action="store_true",
        help="Do not supply available ontology terms to the language model",
    )
    parser.add_argument(
        "--no-shacl",
        action="store_true",
        help="Skip SHACL validation and the repair loop",
    )
    parser.add_argument(
        "--strict-terms",
        action="store_true",
        help="Απόρριψη triples με άγνωστους όρους",
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Generate OWL snippets asynchronously",
    )
    parser.add_argument(
        "--keywords",
        default=None,
        help="Comma-separated keywords for sentence filtering",
    )
    args = parser.parse_args()

    try:
        examples = None
        if args.examples:
            with open(args.examples, "r", encoding="utf-8") as f:
                examples = json.load(f)
        keywords = (
            [k.strip() for k in args.keywords.split(",") if k.strip()]
            if args.keywords
            else None
        )
        run_pipeline(
            args.inputs,
            args.shapes,
            args.base_iri,
            ontologies=args.ontologies,
            ontology_dir=args.ontology_dir,
            model=args.model,
            temperature=args.temperature,
            examples=examples,
            repair=args.repair,
            kmax=args.kmax,
            reason=args.reason,
            spacy_model=args.spacy_model,
            inference=args.inference,
            load_rbo=args.rbo,
            load_lexical=args.lexical,
            use_terms=not args.no_terms,
            validate=not args.no_shacl,
            use_async=args.use_async,
            strict_terms=args.strict_terms,
            keywords=keywords,
        )
    except RuntimeError as exc:
        logging.getLogger(__name__).error("Pipeline aborted: %s", exc)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
