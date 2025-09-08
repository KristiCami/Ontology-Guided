import argparse
import os
from dotenv import load_dotenv
import sys
import logging
import json
from typing import Iterable, Optional, Union
from pathlib import Path

# Ensure the project root and scripts directory are on the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
SCRIPTS_DIR = os.path.dirname(__file__)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from ontology_guided.data_loader import DataLoader, clean_text
from ontology_guided.llm_interface import LLMInterface
from ontology_guided.ontology_builder import OntologyBuilder, InvalidTurtleError
from ontology_guided.validator import SHACLValidator
from ontology_guided.repair_loop import RepairLoop
from ontology_guided import exemplar_selector
from save_prompt_config import save_prompt_config

PROMPT_TEMPLATE = (
    "Convert the following requirement into OWL axioms in Turtle syntax. "
    "Use base IRI {base} and prefix {prefix}.\n\n"
    "Requirement: {sentence}\n\nOWL:"
)


def load_dev_examples(requirements_path: str, split_path: str) -> tuple[list[dict[str, str]], list[str]]:
    """Load few-shot examples from the dev split.

    Parameters
    ----------
    requirements_path:
        Path to a JSONL file with requirements and their OWL annotations.
    split_path:
        Path to a text file containing one ``sentence_id`` per line that
        determines which records from ``requirements_path`` should be used.

    Returns
    -------
    examples, dev_ids_list
        ``examples`` is a list of dictionaries, each containing the natural
        language requirement (``user``), its OWL representation
        (``assistant``) and the corresponding ``sentence_id``. ``dev_ids_list``
        preserves the order of IDs from ``split_path`` so logging can reference
        them.
    """

    with open(split_path, "r", encoding="utf-8") as f:
        dev_ids_list = [line.strip() for line in f if line.strip()]
    dev_ids = set(dev_ids_list)

    examples: list[dict[str, str]] = []
    found_ids: set[str] = set()
    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            sid = str(record.get("sentence_id"))
            if sid not in dev_ids:
                continue
            sentence = record.get("meta", {}).get("description") or record.get("text", "")
            axioms = record.get("axioms", {})
            owl_parts: list[str] = []
            for key in ("tbox", "abox", "shacl"):
                part = axioms.get(key)
                if part:
                    owl_parts.extend(part)
            examples.append(
                {
                    "user": sentence,
                    "assistant": "\n".join(owl_parts),
                    "sentence_id": sid,
                }
            )
            found_ids.add(sid)
    missing = dev_ids - found_ids
    if missing:
        raise RuntimeError("Missing dev IDs: " + ", ".join(sorted(missing)))
    return examples, dev_ids_list

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
    backend: str = "openai",
    model_path: Optional[str] = None,
    temperature: float = 0.0,
    examples=None,
    *,
    use_retrieval: bool = False,
    dev_pool: Optional[Union[str, Path, list[dict[str, str]]]] = None,
    retrieve_k: int = 3,
    retrieval_method: Optional[str] = None,
    prompt_log: Optional[Union[str, Path]] = None,
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
    allowed_ids: Optional[Iterable[str]] = None,
    dev_sentence_ids: Optional[Iterable[str]] = None,
):
    """Execute the ontology drafting pipeline.

    Parameters mirror the command line flags used in ``main``. The function now
    returns a dictionary describing the intermediate artefacts so callers such
    as the web interface can display each stage to the user. The ``backend``
    argument selects the LLM provider (``openai`` or ``llama``) and
    ``model_path`` can override the model name for local backends. When
    ``load_rbo``
    or ``load_lexical`` are ``True``, the predefined ontology files at
    ``RBO_ONTOLOGY_PATH`` and ``LEXICAL_ONTOLOGY_PATH`` are included
    automatically.  ``ontology_dir`` allows specifying a directory from which
    all ``.ttl`` files will be loaded as additional ontologies. ``kmax`` sets
    the maximum number of repair iterations, while ``reason`` and ``inference``
    control reasoning behaviour within the repair loop. ``use_terms`` controls
    whether ontology terms are supplied to the language model. ``validate``
    toggles SHACL validation and the subsequent repair loop. ``strict_terms``
    discards triples that contain unknown ontology terms. ``use_retrieval``
    enables exemplar selection from ``dev_pool``; the ``retrieve_k`` most
    similar examples are used per sentence and their IDs are written to
    ``prompt_log``. If ``allowed_ids`` and ``dev_sentence_ids`` are both
    provided they must be disjoint, otherwise a ``RuntimeError`` is raised.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY") if backend == "openai" else ""
    if backend == "openai" and not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env")

    pipeline = {}
    failed_snippets = pipeline["failed_snippets"] = []

    loader = DataLoader(spacy_model=spacy_model)
    if examples is not None and dev_sentence_ids is None:
        raise RuntimeError("dev_sentence_ids must be provided when examples are supplied")
    if allowed_ids is not None and dev_sentence_ids is not None:
        overlap = set(allowed_ids).intersection(dev_sentence_ids)
        if overlap:
            raise RuntimeError("Dev and test IDs must be disjoint")
    if examples is not None and allowed_ids is not None:
        example_ids = {
            ex.get("sentence_id")
            for ex in examples
            if ex.get("sentence_id") is not None
        }
        overlap = set(example_ids).intersection(allowed_ids)
        if overlap:
            raise RuntimeError("Examples and allowed_ids must be disjoint")
    texts_iter = loader.load_requirements(inputs, allowed_ids=allowed_ids)
    pipeline["texts"] = []

    # Store only a small preview of sentences for display purposes
    sentences_preview = pipeline["sentences"] = []
    PREVIEW_LIMIT = 20

    def sentence_iterator():
        for item in texts_iter:
            if isinstance(item, dict):
                raw_text = item.get("text", "")
                sid = item.get("sentence_id")
            else:
                raw_text = item
                sid = None
            pipeline["texts"].append(raw_text)
            for sent_text in loader.preprocess_text(raw_text, keywords=keywords):
                if len(sentences_preview) < PREVIEW_LIMIT:
                    sentences_preview.append(sent_text)
                if sid is not None:
                    yield {"text": sent_text, "sentence_id": sid}
                else:
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
    initial_terms = builder.get_available_terms() if use_terms else None

    if use_retrieval and dev_pool is not None:
        if isinstance(dev_pool, (str, Path)):
            with open(dev_pool, "r", encoding="utf-8") as f:
                dev_pool_data = json.load(f)
        else:
            dev_pool_data = dev_pool
        if dev_sentence_ids is not None:
            pool_ids = {
                ex.get("sentence_id")
                for ex in dev_pool_data
                if ex.get("sentence_id") is not None
            }
            if set(dev_sentence_ids) != pool_ids:
                raise RuntimeError(
                    "Dev pool sentence IDs do not match dev_sentence_ids"
                )
        logger.info("Using retrieval with %d dev examples", len(dev_pool_data))
        dev_pool = dev_pool_data

    if not use_retrieval and dev_sentence_ids is not None:
        example_ids = {
            ex.get("sentence_id")
            for ex in (examples or [])
            if ex.get("sentence_id") is not None
        }
        if set(dev_sentence_ids) != example_ids:
            raise RuntimeError(
                "Example sentence IDs do not match dev_sentence_ids"
            )

    llm = LLMInterface(
        api_key=api_key,
        model=model,
        backend=backend,
        model_path=model_path,
        temperature=temperature,
        examples=examples,
        use_retrieval=use_retrieval,
        dev_pool=dev_pool,
        retrieve_k=retrieve_k,
        prompt_log=prompt_log,
    )

    if retrieval_method is None and use_retrieval:
        retrieval_method = getattr(
            exemplar_selector, "RETRIEVAL_METHOD", "tfidf_cosine"
        )

    # Save prompt configuration once before processing test sentences
    if dev_sentence_ids is not None:
        prompt_messages = llm.build_prompt("", initial_terms, log_examples=False)
        prompt_text = prompt_messages[0]["content"] if prompt_messages else ""
        hyperparams = {
            "lambda": None,
            "m": None,
            "kmax": kmax,
            "temperature": temperature,
            "model": model,
        }
        save_prompt_config(
            prompt_text,
            dev_sentence_ids,
            hyperparams,
            use_retrieval=use_retrieval,
            retrieve_k=retrieve_k,
            retrieval_method=retrieval_method,
            prompt_log=prompt_log,
        )

    snippets_preview = pipeline["owl_snippets"] = []
    BATCH_SIZE = 100

    os.makedirs("results", exist_ok=True)
    batch: list[Union[str, dict[str, str]]] = []
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
                    available_terms=initial_terms,
                )
            else:
                owl_batch = llm.generate_owl(
                    batch,
                    PROMPT_TEMPLATE,
                    base=base_iri,
                    prefix=builder.prefix,
                    available_terms=initial_terms,
                )
            for sent, snippet in zip(batch, owl_batch):
                sent_text = sent.get("text") if isinstance(sent, dict) else sent
                if len(snippets_preview) < PREVIEW_LIMIT:
                    snippets_preview.append(snippet)
                snippet_counter += 1
                try:
                    triples = builder.parse_turtle(
                        snippet,
                        logger=logger,
                        requirement=sent_text,
                        snippet_index=snippet_counter,
                        strict_terms=strict_terms,
                        update_terms=False,
                    )
                    builder.add_provenance(sent_text, triples)
                except InvalidTurtleError:
                    logger.warning(
                        "Skipping invalid OWL snippet for sentence: %s", sent_text
                    )
                    failed_snippets.append({"sentence": sent_text, "snippet": snippet})
            batch = []
    if batch:
        if use_async:
            owl_batch = llm.async_generate_owl(
                batch,
                PROMPT_TEMPLATE,
                base=base_iri,
                prefix=builder.prefix,
                available_terms=initial_terms,
            )
        else:
            owl_batch = llm.generate_owl(
                batch,
                PROMPT_TEMPLATE,
                base=base_iri,
                prefix=builder.prefix,
                available_terms=initial_terms,
            )
        for sent, snippet in zip(batch, owl_batch):
            sent_text = sent.get("text") if isinstance(sent, dict) else sent
            if len(snippets_preview) < PREVIEW_LIMIT:
                snippets_preview.append(snippet)
            snippet_counter += 1
            try:
                triples = builder.parse_turtle(
                    snippet,
                    logger=logger,
                    requirement=sent_text,
                    snippet_index=snippet_counter,
                    strict_terms=strict_terms,
                    update_terms=False,
                )
                builder.add_provenance(sent_text, triples)
            except InvalidTurtleError:
                logger.warning(
                    "Skipping invalid OWL snippet for sentence: %s", sent_text
                )
                failed_snippets.append({"sentence": sent_text, "snippet": snippet})
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

        pipeline["violation_stats"] = {
            "pre_count": summary.get("total", 0),
            "post_count": summary.get("total", 0),
            "iterations": 0,
            "first_conforms_iteration": 0 if conforms else None,
            "per_iteration": [
                {
                    "iteration": 0,
                    "total": summary.get("total", 0),
                    "bySeverity": summary.get("bySeverity", {}),
                    "is_consistent": pipeline.get("is_consistent"),
                    "unsat_count": pipeline.get("inconsistent_classes", {}).get("count", 0),
                    "prompt_count": 0,
                    "prompt_success_rate": 0.0,
                }
            ],
            "reduction": 0.0,
            "unsat_initial": pipeline.get("inconsistent_classes", {}).get("count", 0),
            "unsat_final": pipeline.get("inconsistent_classes", {}).get("count", 0),
            "consistency_transitions": [],
            "prompt_count": 0,
            "prompt_success_rate": 0.0,
        }

        if not conforms and repair:
            logger.info("Running repair loop...")
            repairer = RepairLoop(
                pipeline["combined_ttl"],
                shapes,
                api_key,
                kmax=kmax,
                base_iri=base_iri,
                allowed_terms=initial_terms,
            )
            repairer.llm = llm
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
    parser.add_argument("--model", default="gpt-4", help="Model name")
    parser.add_argument(
        "--backend",
        default="openai",
        choices=["openai", "llama"],
        help="LLM backend to use",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Local model path or identifier for llama backend",
    )
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
    parser.add_argument(
        "--use-retrieval",
        action="store_true",
        help="Select few-shot examples via retrieval from a dev pool",
    )
    parser.add_argument(
        "--dev-pool",
        default=None,
        help="JSON file with dev examples used for retrieval",
    )
    parser.add_argument(
        "--retrieve-k",
        type=int,
        default=3,
        help="Number of exemplars to retrieve for each sentence",
    )
    parser.add_argument(
        "--prompt-log",
        default=None,
        help="Where to log IDs of retrieved exemplars",
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
    parser.add_argument(
        "--split",
        default=None,
        help="Path to file with sentence_ids to include",
    )
    args = parser.parse_args()

    try:
        requirements_path = os.path.join(PROJECT_ROOT, "evaluation", "atm_requirements.jsonl")
        split_path = os.path.join(PROJECT_ROOT, "splits", "dev.txt")
        examples, dev_sentence_ids = load_dev_examples(requirements_path, split_path)
        if examples and not dev_sentence_ids:
            raise RuntimeError("dev_sentence_ids required when examples are provided")
        if args.examples:
            logging.getLogger(__name__).warning(
                "--examples is ignored; using dev split examples only"
            )
        with open(requirements_path, "r", encoding="utf-8") as f:
            all_sentence_ids = {
                str(json.loads(line).get("sentence_id"))
                for line in f
                if line.strip()
            }
        test_path = os.path.join(PROJECT_ROOT, "splits", "test.txt")
        with open(test_path, "r", encoding="utf-8") as f:
            test_sentence_ids = [line.strip() for line in f if line.strip()]
        missing_test = set(test_sentence_ids) - all_sentence_ids
        if missing_test:
            raise RuntimeError(
                "Test IDs not found in requirements: "
                + ", ".join(sorted(missing_test))
            )
        overlap_examples = set(dev_sentence_ids) & set(test_sentence_ids)
        if overlap_examples:
            raise RuntimeError(
                "Few-shot examples contain test IDs: "
                + ", ".join(sorted(overlap_examples))
            )
        keywords = (
            [k.strip() for k in args.keywords.split(",") if k.strip()]
            if args.keywords
            else None
        )
        allowed_ids = None
        if args.split:
            with open(args.split, "r", encoding="utf-8") as f:
                allowed_ids = [line.strip() for line in f if line.strip()]
            missing_allowed = set(allowed_ids) - all_sentence_ids
            if missing_allowed:
                raise RuntimeError(
                    "Input sentence IDs not found in requirements: "
                    + ", ".join(sorted(missing_allowed))
                )
            overlap_inputs = set(allowed_ids) & set(dev_sentence_ids)
            if overlap_inputs:
                raise RuntimeError(
                    "Input sentence IDs are in dev split: "
                    + ", ".join(sorted(overlap_inputs))
                )
            if examples:
                example_ids = {
                    ex.get("sentence_id")
                    for ex in examples
                    if ex.get("sentence_id") is not None
                }
                overlap_ex_allowed = example_ids & set(allowed_ids)
                if overlap_ex_allowed:
                    raise RuntimeError(
                        "Few-shot examples overlap with allowed IDs: "
                        + ", ".join(sorted(overlap_ex_allowed))
                    )
        run_pipeline(
            args.inputs,
            args.shapes,
            args.base_iri,
            ontologies=args.ontologies,
            ontology_dir=args.ontology_dir,
            model=args.model,
            backend=args.backend,
            model_path=args.model_path,
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
            allowed_ids=allowed_ids,
            dev_sentence_ids=dev_sentence_ids,
            use_retrieval=args.use_retrieval,
            dev_pool=args.dev_pool or examples,
            retrieve_k=args.retrieve_k,
            prompt_log=args.prompt_log,
        )
    except RuntimeError as exc:
        logging.getLogger(__name__).error("Pipeline aborted: %s", exc)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
