# Τεχνική αναφορά υλοποίησης απαιτήσεων

Η ποιότητα μιας οντολογίας δεν είναι μονοδιάστατη: μπορεί να είναι (α) συντακτικά σωστή, (β) σημασιολογικά σωστή, (γ) λογικά συνεπής και (δ) λειτουργικά επαρκής για το domain. Κάθε metric καλύπτει διαφορετική διάσταση, γι’ αυτό ο στόχος του συστήματος είναι να βελτιώνει και τα τέσσερα επίπεδα ταυτόχρονα (βλ. πίνακες E1–E6/A1–A14 στο `README.md` και τη συνοπτική μεθοδολογία στο `docs/evaluation_methodology.md`).

## Χάρτης 4 επιπέδων και υλοποίηση
| Επίπεδο | Απαίτηση | Υλοποίηση |
| --- | --- | --- |
| Συντακτικό | **Exact Matching**: σύγκριση raw RDF triples μεταξύ gold και pred. | `og_nsd/metrics.py::compute_exact_metrics` φορτώνει/ενώνει triples και υπολογίζει P/R/F1. Τα scripts `scripts/run_e1_llm_only.py` και `scripts/run_e4_iterative.py` αποθηκεύουν `metrics_exact.json` για τις αντίστοιχες εκτελέσεις. |
| Σημασιολογικό | **Semantic (Entailment) Matching**: σύγκριση closures μετά από reasoning. | `og_nsd/metrics.py::_materialize_closure` υλοποιεί OWL 2 RL expansion (με `owlrl` όταν υπάρχει) και `compute_semantic_metrics` υπολογίζει P/R/F1 στα κανονικοποιημένα closures, εξασφαλίζοντας ότι διαφορετικές αναπαραστάσεις με το ίδιο νόημα μετρώνται σωστά. |
| Δομικό/Λογικό | **SHACL + Reasoner**: δομική εγκυρότητα και συνεκτικότητα. | `og_nsd/shacl.py::ShaclValidator` τρέχει PySHACL με RDFS inference, μετατρέπει το report σε δομημένα results και εντοπίζει μη-έγκυρα decimals πριν το validation. `og_nsd/reasoning.py::OwlreadyReasoner` καθαρίζει αριθμητικά/datetime literals, εκτελεί Pellet (όταν διαθέσιμο) και αναφέρει consistency/unsat classes. Η αλληλουχία Reasoner→SHACL ενσωματώνεται στον βρόχο της `OntologyDraftingPipeline.run`. |
| Λειτουργικό | **Competency Questions (CQs)**: domain adequacy με SPARQL ASK. | `og_nsd/queries.py::CompetencyQuestionRunner` φορτώνει/ομαδοποιεί ASK queries (π.χ. `atm_cqs.rq`) και τα εκτελεί ανά iteration. Τα αποτελέσματα γράφονται σε `cq_results.json` από τα scripts E1/E4 και εντάσσονται στο τελικό report του pipeline. |

## Βρόχος παραγωγής και επιδιόρθωσης (E3/E4)
- **LLM drafting:** `og_nsd/llm.py` παρέχει `OpenAILLM` (πλήρες prompt με ontology-aware context/few-shots) και `HeuristicLLM` (offline, ντετερμινιστικό fallback). Η αρχική παραγωγή γίνεται σε παρτίδες με `chunk_requirements` και συντίθεται στο `OntologyAssembler` (`og_nsd/ontology.py`).
- **Validation/repair loop:** Στο `og_nsd/pipeline.py` κάθε iteration εκτελεί Reasoner → SHACL → CQs και καταγράφει reports. Όταν υπάρχουν παραβιάσεις, `_synthesize_repair_prompts` μετατρέπει τα SHACL results σε prompts και ο LLM επιστρέφει Turtle patch που συγχωνεύεται στο state graph.
- **Patch calculus:** Η δομή `Patch` στο `og_nsd/repair.py` κωδικοποιεί SHACL violations σε JSON-friendly σχέδιο (`shacl_report_to_patches`), και το `HeuristicLLM.apply_patches` εφαρμόζει ντετερμινιστικά τις εντολές (domain/range/type), επιτρέποντας repeatable “typed” repairs ακόμη και χωρίς απομακρυσμένο LLM.
- **Stop policies & safety:** `og_nsd/repair.py::should_stop` υποστηρίζει πολιτικές `default`, `hard_and_cq`, `ignore_no_hard`, `max_only`, χρησιμοποιώντας σκληρές/ήπιες παραβιάσεις (hard/soft) από `summarize_shacl_report`, την πρόοδο CQs και τη στασιμότητα patches για να αποφύγει άσκοπες ή επικίνδυνες επαναλήψεις.
- **Τήρηση iteration logs:** Τα scripts γράφουν ανά iteration τα SHACL summaries, CQ pass rates, reasoning diagnostics και τύπους patches (`repair_log.json`), επιτρέποντας υπολογισμό “repair efficiency” (iters to conform, διανομή) σύμφωνα με τις απαιτήσεις.

## Κάλυψη πειραμάτων E1–E6
- **E1 (LLM-only):** `scripts/run_e1_llm_only.py` τρέχει μόνο drafting (χωρίς SHACL/Reasoner), αποθηκεύει exact/semantic metrics, CQ pass rate και δείγματα drift/redundancy στο `run_report.json`.
- **E2 (Symbolic-only):** `scripts/run_e2_symbolic_only.py` παραλείπει LLM drafting και χρησιμοποιεί κανόνες/alignment από `og_nsd/ontology.py` + SHACL/Reasoner για high-precision baseline.
- **E3 (No-repair):** `scripts/run_e3_no_repair.py` εκτελεί ένα validation pass χωρίς feedback loop, ώστε το iter0 να λειτουργεί ως baseline πριν από τις επισκευές.
- **E4 (Full):** `scripts/run_e4_iterative.py` υλοποιεί κλειστό βρόχο CEGIR με SHACL→patch plan→LLM patch application, πολλαπλές stop policies, και τελικά exact/semantic metrics σε reasoned graph.
- **E5 (Cross-domain):** `scripts/run_e5_cross_domain.py` επαναχρησιμοποιεί την ίδια στοίβα (LLM, prompts, loop) με διαφορετικά ζεύγη ontology/shapes για να επιβεβαιώσει domain portability.
- **E6 (CQ-oriented):** `scripts/run_e6_cq_oriented.py` δίνει έμφαση στην πρόοδο των CQs ανά iteration και στηρίζει τις απαιτήσεις λειτουργικής επάρκειας.

## Αblations & ευαισθησίες (A1–A14) – διαθέσιμα hooks
- **wSHACL / hard-soft bands (A1, A9):** Οι severity τιμές του SHACL report χαρτογραφούνται σε hard/soft μετρώντας ξεχωριστά violations· οι stop policies μπορούν να απαιτούν μηδενικά hard ή CQ-threshold, καλύπτοντας σενάρια χωρίς “βάρη” αλλά με διακριτή προτεραιοποίηση.
- **Patch calculus toggle (A2):** Στο E4 χρησιμοποιείται δομημένο `Patch` σχέδιο· ρυθμίσεις χωρίς typed patches μπορούν να μιμηθούν το A2 καλώντας `generate_patch` αντί `apply_patches` (raw Turtle).
- **Admissibility (A3):** Η `should_stop` αποφεύγει επανάληψη όταν τα ίδια patches επιστρέφουν (προστασία από regressions), ενώ το parsing guard στο E4 σταματά σε μη έγκυρο Turtle πριν γίνει commit.
- **Ontology-aware prompting (A4):** Τα config flags `use_ontology_context` και `grounding_ontology_path` στους constructors του LLM/pipeline ενεργοποιούν ή απενεργοποιούν την άντληση labels/synonyms, καλύπτοντας το -OntoAwarePrompt σενάριο.
- **Reasoner ordering (A5):** Η τρέχουσα αλληλουχία Reasoner→SHACL μπορεί να αντιστραφεί εύκολα σε scripts (μία παράμετρος στο loop) για πειράματα A/B.
- **LLM swap (A6):** Το `llm_mode` (heuristic/openai) και το `model` argument του `OpenAILLM` επιτρέπουν αλλαγή μοντέλου/temperature. Τα scripts δέχονται config overrides.
- **Budget & hints (A7, A8):** Το `max_iterations` (config/CLI) καθορίζει το $K_{max}$· οι παράμετροι `requirements_chunk_size`, `use_ontology_context` και temperatures επιτρέπουν πειραματισμό με hints/grounding ισχύ.
- **Θόρυβος, μήκος, shapes coverage, aligners, CQ density (A10–A14):** Τα scripts διαβάζουν requirements/shapes/CQ αρχεία από paths στο config, οπότε εκδοχές με θόρυβο, παραλλαγές σχήματος ή διαφορετικά ASK sets μπορούν να τροφοδοτηθούν χωρίς αλλαγή κώδικα.

## Πώς ελέγχεται η συμμόρφωση
1. **Exact/Semantic:** Τρέξτε E1 ή E4 scripts και ελέγξτε `metrics_exact.json` / `metrics_semantic.json`. Η semantic σύγκριση χρησιμοποιεί closure όταν υπάρχει το `owlrl` dependency (`requirements.txt`).
2. **SHACL/Reasoner:** Δείτε τα `shacl_report.ttl`/`validation_summary.json` και τα reasoning diagnostics σε `repair_log.json` ανά iteration.
3. **CQs:** Τα `cq_results.json` δείχνουν pass rate/failed queries ανά iteration.
4. **Repair efficiency:** Το `repair_log.json` καταγράφει violations per iter, αριθμό/τύπους patches και stop reason, επιτρέποντας τον υπολογισμό μέσου #iterations και buckets 1/2/3/>3.

Με την παραπάνω χαρτογράφηση, όλες οι απαιτήσεις του specification (exact, semantic, SHACL+reasoner, CQs, repair efficiency, πειράματα και ablations) υποστηρίζονται από υπάρχον κώδικα και παραμετροποίηση χωρίς επιπλέον αλλαγές runtime. Για νέα domains/πρωτόκολλα, αρκεί η προσαρμογή των config αρχείων και των αντίστοιχων requirement/shape/CQ artifacts.
