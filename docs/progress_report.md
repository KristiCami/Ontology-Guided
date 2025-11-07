# Πρόοδος Πειραμάτων Νευρο-Συμβολικού Συστήματος

## Εκτελεστική Περίληψη
- Ολοκληρώθηκε η offline αξιολόγηση του ATM domain για τα βασικά σενάρια E1–E4 με χρήση του cache backend· τα αποτελέσματα έχουν εξαχθεί από τα CSV/JSON αρχεία που παράγονται από το `evaluation/run_benchmark.py`.
- Τεκμηριώθηκε πλήρως η προέλευση των μετρικών (αρχεία εισόδου, scripts, ενδιάμεσα artefacts) ώστε να διευκολύνεται η αναπαραγωγή και ο έλεγχος.
- Οι σταυρο-τομεακές εκτελέσεις (E5–E6) και οι σαρώσεις απαλοιφών A1–A14 παραμένουν σε εξέλιξη· τα απαιτούμενα βήματα και οι εκκρεμότητες καταγράφονται αναλυτικά.

## Δεδομένα & Pipeline Αξιολόγησης
| Συνιστώσα | Αρχείο / Πηγή | Περιγραφή | Χρήση |
|-----------|----------------|-----------|-------|
| Απαιτήσεις (ATM) | `evaluation/atm_requirements.jsonl` | JSONL με τα sentence-level requirements και τις αντιστοιχίες χρυσών αξιωμάτων. | Είσοδος στο pipeline (E1–E4). |
| SHACL Shapes | `shapes.ttl` | Καλύπτει constraint κανόνες ATM domain. | Ενεργοποιείται όταν `validate=true` (E3–E4). |
| Gold Ontology | `gold/atm_gold.ttl` | Στόχος αξιολόγησης F1/precision/recall. | Σύγκριση με τα παραγόμενα triples. |
| CQ Suite | `evaluation/atm_cqs.rq` | SPARQL ASK queries (21 ερωτήσεις). | Μέτρηση CQ pass rate. |
| Dev/Test Splits | `splits/dev.txt`, `evaluation/table1.csv` export | Ορίζει sentence IDs που χρησιμοποιούνται στο filtering των απαιτήσεων. | Διασφαλίζει μη διαρροή μεταξύ dev/test. |
| Configurations | `evaluation/presentation_main.json` | Ορίζει τα flags `use_terms`, `validate`, `repair`, `reason` ανά πείραμα. | Χρησιμοποιείται από `run_benchmark.py` για E1–E4. |

**Εκτέλεση**
```bash
python -m evaluation.run_benchmark \
  --pairs "evaluation/atm_requirements.jsonl:gold/atm_gold.ttl" \
  --settings-file evaluation/presentation_main.json \
  --cq-paths evaluation/atm_cqs.rq \
  --base-iri "http://lod.csd.auth.gr/atm/atm.ttl#" \
  --output-dir results/offline_report
```
- Το script καλεί εσωτερικά το `scripts/main.py::run_pipeline` και γράφει τις αναφορές σε `results/` (προβλέψεις, SHACL log, reasoner outputs) και σε `evaluation/table*.csv|md`.
- Η cache επιλογή (`"backend": "cache"`) επαναχρησιμοποιεί προϋπάρχουσες γεννήσεις από `results/combined.ttl` και `results/prompts.log` για επαναληπτική αξιολόγηση χωρίς νέα κλήση LLM.

## Κύρια Πειράματα (E1–E4)
| ID | Διαμόρφωση | Ρύθμιση (από `presentation_main.json`) | P / R / F1 | SHACL Violations (αρχικές→τελικές) | CQ Pass Rate | Artefacts |
|----|-------------|----------------------------------------|------------|------------------------------------|--------------|-----------|
| E1 | LLM-only | `use_terms=true`, `validate=false`, `repair=false`, `reason=false` | 0.985 / 1.000 / 0.992 | n/a (validation off) | 57.1 % | `evaluation/table1.csv`, `results/combined.ttl` |
| E2 | Symbolic-only | `use_terms=false`, `strict_terms=true`, `validate=false` | 0.305 / 1.000 / 0.468 | n/a (validation off) | 57.1 % | `evaluation/table2.csv` |
| E3 | Ours (no-repair) | `use_terms=true`, `validate=true`, `repair=false`, `reason=true` | 0.985 / 1.000 / 0.992 | 0 → 0 | 57.1 % | `evaluation/table3.csv`, `results/shacl_report.txt` |
| E4 | Ours (full loop) | `use_terms=true`, `validate=true`, `repair=true`, `reason=true`, `kmax=5` | 0.305 / 1.000 / 0.468 | 0 → 0 | 57.1 % | `evaluation/table4.csv`, `results/prompts.log` |
| E5 | Cross-domain | Pending config (healthcare/auto cache) | — | — | — | Απαιτεί νέα cache (`results/healthcare_combined.ttl` σε εκκρεμότητα) |
| E6 | CQ-oriented | Requires repair-inducing snippets & CQ sweeps | — | — | — | Θα εξαχθούν μέσω `evaluation/run_benchmark.py` μόλις δημιουργηθούν violations |

**Παρατηρήσεις**
- Τα CSV/Markdown που δημιουργεί το `run_benchmark.py` (`evaluation/table1.md`–`table4.md`) αναφέρουν αναλυτικά precision/recall/F1, κατανομές επαναλήψεων και ποσοστά συμμόρφωσης ανά διαμόρφωση.
- Η μέτρηση CQ προκύπτει από το `competency_questions.evaluate_cqs`, με ολικό pass rate 12/21 (`results/atm_cq_results.json`).
- Στις cache εκτελέσεις ο βρόχος επιδιόρθωσης δεν ενεργοποιήθηκε (0 iterations), με αποτέλεσμα το E4 να ανακυκλώσει τις υποβαθμισμένες προβλέψεις του degradation cache (ίδια P/R/F1 με E2). Η συμπεριφορά αυτή θα αλλάξει σε runs χωρίς caching.

## Ανάλυση Εξαγωγής Αξιωμάτων
| Τύπος Αξιώματος | Precision | Recall | F1 |
|-----------------|-----------|--------|----|
| Classes | 0.114 | 0.643 | 0.194 |
| ObjectProperty | 0.015 | 0.091 | 0.025 |
| DatatypeProperty | 0.143 | 0.143 | 0.143 |
| SubClassOf | 0.000 | 0.000 | 0.000 |
| Domain | 0.012 | 0.056 | 0.019 |
| Range | 0.023 | 0.111 | 0.038 |
| EquivalentClasses | 0.000 | 0.000 | 0.000 |

- Οι παραπάνω τιμές υπολογίζονται με το `evaluation/axiom_metrics.py` (syntactic matching) πάνω στα αρχεία `results/combined_test.ttl` και `results/gold_test.ttl`. Το συνολικό macro-F1 ισούται με 0.060, ενώ οι micro μετρικές (precision=0.0188, recall=0.1972, F1=0.0344) είναι διαθέσιμες στο `results/axiom_metrics.json`.
- Τα χαμηλά σκορ σε SubClassOf/Range αντανακλούν την περιορισμένη κάλυψη του cache baseline και καταγράφονται ως στόχοι βελτίωσης για runs χωρίς caching.

## Συμμόρφωση & Λογική Συνοχή
- **SHACL**: Το `ontology_guided.validator.SHACLValidator` αναφέρει μηδενικές παραβάσεις στο `results/shacl_report.txt` για E3/E4 (ενεργοποιημένη επαλήθευση).
- **Reasoner**: Το `ontology_guided.reasoner.run_reasoner` δημιουργεί τα artefacts `results/combined.owl` και `results/inconsistent_classes.txt`; το τελευταίο περιλαμβάνει τις ασυνεπείς κλάσεις `owl:Nothing` και `error:Error1`, οι οποίες πρέπει να διερευνηθούν στο επόμενο iteration.
- **Prompt Loop**: Το `results/prompts.log` σε συνδυασμό με το `results/prompt_config.json` τεκμηριώνει ότι δεν παρήχθησαν patches (καθώς δεν υπήρξαν SHACL violations), επιβεβαιώνοντας μηδενικές σκληρές παλινδρομήσεις.

## Competency Questions
- Η αξιολόγηση SPARQL ASK υλοποιείται από το `evaluation/competency_questions.py`. Το JSON `results/atm_cq_results.json` συγκρίνει το παραγόμενο ontology με το επιχειρησιακό: 12/21 επιτυχημένες ερωτήσεις για το gold snapshot έναντι 21/21 για το production ontology.
- Εκκρεμεί ανάλυση των 9 αποτυχημένων ASK (π.χ. με trace από `evaluation/competency_questions.py --dump`), ώστε να σχεδιαστούν targeted repairs στο E4/E6.

## Πίνακας Β – Ablations & Sensitivity (Κατάσταση)
| ID | Παράμετρος | Τρέχουσα Κατάσταση | Σημειώσεις/Ενέργειες |
|----|------------|--------------------|----------------------|
| A1 | -wSHACL | ⏳ Εκκρεμεί | Απαιτεί rerun με `lambda` weights ομοιόμορφα (τροποποίηση `run_benchmark.py` settings). |
| A2 | -PatchCalc | ⏳ Εκκρεμεί | Δημιουργία config με `repair_backend="raw_turtle"` και log validation. |
| A3 | -Admissibility | ⏳ Εκκρεμεί | Ενσωμάτωση flag παράκαμψης στο `scripts/main.py` πριν το commit των patches. |
| A4 | -OntoAwarePrompt | ⏳ Εκκρεμεί | Απενεργοποίηση `use_terms` + αφαίρεση grounding από `ontology_guided/prompts`. |
| A5 | Reasoner order | ⏳ Εκκρεμεί | Αντιστροφή σειράς `validator.run_validation()` / `run_reasoner()` στο loop. |
| A6 | LLM swap | ⏳ Εκκρεμεί | Προσθήκη backend configs για Claude/LLaMA σε `evaluation/presentation_main.json`. |
| A7 | K_max budget | ⏳ Εκκρεμεί | Sweep `kmax` μέσω command line (`--settings`). |
| A8 | Top-m hints | ⏳ Εκκρεμεί | Παραμετροποίηση `exemplar_selector.RETRIEVAL_METHOD` & `top_m` στο pipeline. |
| A9 | Weights λ | ⏳ Εκκρεμεί | Grid search και εξαγωγή καμπυλών Pareto (σύνδεση με `repair_efficiency.py`). |
| A10 | Noisy reqs | ⏳ Εκκρεμεί | Παραγωγή παραλλαγών με noise (βλ. `scripts/noise_injection.py` αν διαθέσιμο, αλλιώς νέο script). |
| A11 | Long docs | ⏳ Εκκρεμεί | Δημιουργία buckets μεγαλύτερου μήκους και μέτρηση χρόνου/μνήμης. |
| A12 | Shapes coverage | ⏳ Εκκρεμεί | Τροποποίηση `shapes.ttl` (+/-20%) με διατήρηση versioning. |
| A13 | Aligners | ⏳ Εκκρεμεί | Benchmark διαφορετικών matchers στο `ontology_guided/exemplar_selector`. |
| A14 | CQ design | ⏳ Εκκρεμεί | Διακύμανση πυκνότητας/αυστηρότητας στο `evaluation/atm_cqs.rq`. |

## Εκκρεμότητες & Επόμενα Βήματα
1. **Σταυρο-τομεακά Runs (E5)**: Δημιουργία cache για Healthcare (`evaluation/healthcare_requirements.txt`, `evaluation/healthcare_shapes.ttl`) και Automotive· επαλήθευση commands στο `run_benchmark.py` με κατάλληλα `--pairs`.
2. **CQ-Triggered Loop (E6)**: Προετοιμασία requirement snippets που ενεργοποιούν SHACL violations ώστε να δοκιμαστεί το repair loop end-to-end (logging patches σε `results/prompts.log`).
3. **Διάγνωση Αποτυχιών CQ**: Εφαρμογή `python -m evaluation.competency_questions results/combined.ttl evaluation/atm_cqs.rq --explain` (προσθήκη flag αν χρειάζεται) για να εντοπιστούν τα ελλείποντα axioms.
4. **Reasoner Fixes**: Ανάλυση των `owl:Nothing`/`error:Error1` από `results/inconsistent_classes.txt` και ενημέρωση των αντίστοιχων requirements/generation prompts.
5. **Οπτικοποιήσεις**: Μόλις συλλεχθούν runs με ενεργό repair, δημιουργία των προβλεπόμενων plots (repair dynamics, heatmaps ευαισθησίας) χρησιμοποιώντας τα δεδομένα από `results/` και `evaluation/table*.csv`.