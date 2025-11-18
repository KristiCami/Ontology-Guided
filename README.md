# Ontology Guided Requirements Drafting

This repository implements a prototype of the pipeline described in the thesis *Ontology-Guided Ontology Drafting from Software Requirements: A Neuro-Symbolic Pipeline for OWL Generation, Validation, and Feedback Repair*. The goal is to translate natural-language requirements into OWL axioms, validate them with SHACL, and iteratively repair the output via LLM feedback.

## Repository layout

- `Ontology_drafting.pdf` – original thesis / concept document.
- `ontology_pipeline/` – Python package containing the neuro-symbolic pipeline.
- `shacl/atm_shapes.ttl` – Example SHACL constraints derived from ATM domain ontologies.
- `requirements/atm_requirement.txt` – Sample requirement text used in the demo.
- `main.py` – CLI entry point showcasing how to execute the pipeline end-to-end.

## How the pipeline works

1. **Prompt construction** (`ontology_pipeline/prompting.py`): The requirement text plus optional domain context are shaped into a drafting prompt for the LLM.
2. **LLM generation** (`ontology_pipeline/llm_interface.py`): An LLM (here mocked for reproducibility) emits JSON with OWL structures (classes, properties, restrictions, individuals).
3. **Parsing & graph construction** (`ontology_pipeline/parser.py`, `ontology_pipeline/ontology_builder.py`): The JSON payload is converted into dataclasses and materialized as an RDF graph using `rdflib`.
4. **Validation** (`ontology_pipeline/shacl_validator.py`): `pySHACL` checks the graph against SHACL shapes capturing ontology constraints. Violations become structured issues.
5. **Repair loop** (`ontology_pipeline/pipeline.py`, `ontology_pipeline/repair.py`): If validation fails, the issues are converted into repair prompts and sent back to the LLM. The loop repeats until the graph conforms or the iteration limit is hit.

## Running the demo

1. Install dependencies (Python 3.10+):

   ```bash
   pip install -r requirements.txt
   ```

2. Execute the CLI with the provided requirement:

   ```bash
   python main.py requirements/atm_requirement.txt
   ```

   The mocked LLM intentionally emits an incomplete ontology in the first iteration. The SHACL validator detects the missing `performedBy` relation, and the pipeline prompts the mock for a repaired ontology, resulting in a conformant graph in the second pass.

## Extending the system

- Replace `MockLLMClient` with a concrete implementation that calls GPT-4 or another LLM.
- Add more SHACL shapes to encode domain-specific ontologies or Requirement Boilerplate Ontology constraints.
- Implement exporters for `.owl` files or SPARQL endpoints using the generated RDF graphs.
- Integrate spaCy or other NLP tooling to pre-process large requirement corpora before prompting the LLM.
