# Οδηγός ανάγνωσης των αποτελεσμάτων στα `runs/` (E1–E6)

## Σκοπός
Το παρόν σημείωμα εξηγεί **πώς διαβάζονται** και **τι σημαίνουν** τα αρχεία που παράγονται για κάθε πείραμα (E1–E6) στον φάκελο `runs/`. Χρησιμοποιεί τα διαθέσιμα artefacts (E1, E2, E3, E4, E6) ως οδηγούς.

## Κοινή δομή αρχείων ανά run
- `pred.ttl`: το παραγόμενο ontology/tripleset του run.
- `metrics_exact.json` / `metrics_semantic.json`: Precision/Recall/F1, μαζί με πλήθος παραγόμενων, gold και επικαλυπτόμενων triples. Το "exact" απαιτεί ακριβή ταύτιση URI/literals, το "semantic" επιτρέπει ισοδυναμίες/στοιχειώδη εξαγωγή.
- `cq_results*.json`: αποτελέσματα competency questions (ένα αρχείο ανά iteration ή συνολικά, ανάλογα με το run).
- `validation_summary.json`: σύνολο και κατανομή SHACL παραβιάσεων (`hard`, `soft`). Χρήσιμο για γρήγορη εικόνα συμμόρφωσης.
- `run_report.json`: συγκεντρωτικό log με LLM σημειώσεις, SHACL αποτελέσματα, CQ λίστα (query/success/message) και πληροφορίες reasoner (consistency, unsatisfiable classes).
- `reasoning_report.json` (όπου υπάρχει): αναλυτική αναφορά ασυνεπών/unsatisfiable classes.
- SHACL αναφορές (`validation_report.ttl`, `shacl_report.ttl`): πλήρες output validator για debugging παραβιάσεων.
- Δευτερεύοντα αρχεία ανά run: `cq_summary.json` (ποσοστά CQ ανά iteration), `repair_log.json` (μετρικές repair), `patches.json` (προτεινόμενα patches ανά iteration).

## Δομή των JSON αρχείων (σχήματα πεδίων)
- **`metrics_exact.json` / `metrics_semantic.json`**: αντικείμενο με αριθμητικά πεδία `precision`, `recall`, `f1`, και πλήθος `pred_triples`, `gold_triples`, `overlap_triples`.
- **`cq_results*.json`**: αντικείμενο με `pass_rate` (0–1), `passed`, `total` και πίνακα `results`. Κάθε στοιχείο του `results` έχει `query` (κείμενο ASK), `success` (boolean), `message` (diagnostic string).
- **`cq_summary.json`**: πίνακας από αντικείμενα `{iteration, conforms, cq_pass_rate}`· χρησιμοποιείται όταν οι CQ αξιολογούνται ανά iteration χωρίς να αποθηκεύεται κάθε query.
- **`validation_summary.json`**: αντικείμενο με `total` και εμφωλευμένο `violations` που κρατά μετρητές `hard` και `soft`.
- **`reasoning_report.json`**: αντικείμενο με `unsat_classes` (λίστα IRIs/labels), `total_unsat` (ακέραιος), `notes` (string).
- **`run_report.json`**: συγκεντρώνει όσα προκύπτουν από την κλήση του pipeline: `llm_notes` (string), `competency_questions` (λίστα ASK), `iterations` (λίστα με ανά iteration `iteration`, `conforms`, `shacl`, `reasoner`, `cq_results`), καθώς και συνοπτικό `shacl` και `reasoner` στο ρίζα. Τα nested `shacl`/`reasoner` έχουν κλειδιά όπως `conforms`, `results` ή `unsatisfiable_classes`.
- **`repair_log.json`**: λεξικό όπου κάθε κλειδί είναι `iterX` και η τιμή είναι αντικείμενο `{hard, soft}` με τους μετρητές παραβιάσεων.
- **`patches.json`**: πίνακας προτάσεων επιδιόρθωσης, κάθε αντικείμενο φέρει `action`, `subject`, `predicate`, `object`, `severity`, `source_shape`, `message`.

## Πώς παράγονται τα JSON (ανά pipeline)
- **E1 (`scripts/run_e1_llm_only.py`)**: τρέχει το `OntologyDraftingPipeline` με `draft_only=True`, γράφει το `pred.ttl`, υπολογίζει metrics μέσω `compute_exact_metrics/compute_semantic_metrics` και αποθηκεύει CQ αποτελέσματα σε `cq_results.json`.
- **E2 (`scripts/run_e2_symbolic_only.py`)**: εκτελεί SHACL validator και reasoner, κρατά τα summaries σε `validation_summary.json` και `reasoning_report.json`, και χρησιμοποιεί τον reasoned graph για metrics/CQ. Το `run_report.json` περιλαμβάνει τα ίδια στοιχεία ανά iteration.
- **E3 (`scripts/run_atm_examples.py`)**: παράγει `iter0/pred.ttl`, τρέχει reasoner + SHACL, αποθηκεύει πλήρη `validation_report.ttl` και summary, γράφει metrics και `reasoning_report.json`, και κρατά CQ σε `cq_results_iter0.json`.
- **E4 (`scripts/run_e4_iterative.py`)**: υλοποιεί repair loop. Σε κάθε iteration αποθηκεύει `shacl_report.ttl` και `patches.json` (προτεινόμενες αλλαγές). Μετά το stopping criterion, τοποθετεί τα τελικά metrics/CQ/validation summary στο `final/` και τις μετρήσεις παραβιάσεων όλων των iterations στο `repair_log.json`.
- **E6 (`scripts/run_e6_cq_oriented.py`)**: κρατά το `run_report.json` με λίστα iterations, εξάγει συνοπτικά CQ ποσοστά σε `cq_summary.json` και γράφει metrics/validation summary πάνω στο reasoned graph.

## Ανάγνωση ανά πείραμα

### E1 — `runs/E1_llm_only/`
- JSON: `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `run_report.json`.
- TTL: `pred.ttl`.
- Ερμηνεία: Ενιαίο iteration. Τα metrics δείχνουν την επικάλυψη με το gold· το CQ αρχείο έχει μία λίστα από ASK queries με πεδίο `success`.

### E2 — `runs/E2_symbolic_only/`
- JSON: `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `run_report.json`, `validation_summary.json`, `reasoning_report.json`.
- TTL: `pred.ttl`.
- Ερμηνεία: Χρησιμοποιήστε `validation_summary.json` για να επιβεβαιώσετε ότι δεν υπάρχουν παραβιάσεις, και `reasoning_report.json` για να δείτε αν υπάρχουν unsatisfiable classes.

### E3 — `runs/E3_no_repair/`
- JSON ρίζας: `metrics_exact.json`, `metrics_semantic.json`, `cq_results_iter0.json`, `run_report.json`, `reasoning_report.json`, `validation_summary.json`.
- TTL: `iter0/pred.ttl`, `validation_report.ttl`.
- Επιπλέον: `validation_report.ttl` δίνει λεπτομέρειες SHACL, πέρα από το σύνοψη `validation_summary.json`.
- Ερμηνεία: Διαβάστε `metrics_*` για συνολική ακρίβεια και `validation_report.ttl` για να εντοπίσετε ποια shapes παραβιάστηκαν.

### E4 — `runs/E4_full/`
- Δομή πολλαπλών iterations: `iter0/` και `iter1/` με `pred.ttl`, `patches.json`, `shacl_report.ttl` ανά iteration.
- Repair log: `repair_log.json` συγκεντρώνει τον αριθμό `hard`/`soft` παραβιάσεων ανά iteration.
- Τελικό αποτέλεσμα: ο φάκελος `final/` περιέχει `pred.ttl`, `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `validation_summary.json` (δηλαδή τις μετρικές μετά το repair loop).
- Ερμηνεία: Χρησιμοποιήστε `patches.json` για να δείτε τι προτάθηκε ανά iteration, `shacl_report.ttl` για λεπτομέρειες παραβιάσεων, και τα αρχεία στο `final/` για την τελική αποτίμηση.

### E6 — `runs/E6_cq_oriented/`
- JSON: `metrics_exact.json`, `metrics_semantic.json`, `validation_summary.json`, `cq_summary.json`, `run_report.json`.
- TTL: `pred.ttl`.
- Ερμηνεία: Το `cq_summary.json` δείχνει την πορεία CQ ανά iteration (παρά το ότι δεν υπάρχουν ξεχωριστοί φάκελοι per iteration). Το `validation_summary.json` καταγράφει συνολικά SHACL αποτελέσματα.

## Γρήγορη ροή ανάγνωσης
1. **Κάλυψη:** `metrics_exact.json` και `metrics_semantic.json` → precision/recall/F1 και μέτρηση overlapping triples.
2. **CQ ικανοποίηση:** `cq_results*.json` ή `cq_summary.json` → ποσοστό επιτυχίας (`success` ή `cq_pass_rate`).
3. **Συμμόρφωση:** `validation_summary.json` → αριθμός `hard`/`soft` παραβιάσεων. Για λεπτομέρειες δείτε `validation_report.ttl` ή `shacl_report.ttl`.
4. **Συνεκτικότητα:** `reasoning_report.json` ή πεδίο `reasoner` μέσα στο `run_report.json` → unsatisfiable classes / consistency.
5. **Παραγόμενο ontology:** `pred.ttl` (και, όπου υπάρχει, `final/pred.ttl`) → τελικό μοντέλο προς επιθεώρηση ή φόρτωση σε reasoner/editor.

Με τα παραπάνω βήματα μπορεί κανείς να αναγνώσει και να παρουσιάσει γρήγορα τα αποτελέσματα κάθε πειράματος E1–E6, χωρίς να χρειάζεται να ανοίξει όλα τα logs κάθε φορά.
