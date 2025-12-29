# Οδηγός ανάγνωσης των αποτελεσμάτων στα `runs/` (E1–E6)

## Σκοπός
Το παρόν σημείωμα εξηγεί **πώς διαβάζονται** και **τι σημαίνουν** τα αρχεία που παράγονται για κάθε πείραμα (E1–E6) στον φάκελο `runs/`. Χρησιμοποιεί τα διαθέσιμα artefacts (E1, E2, E3, E4, E6) ως οδηγούς.

## Κοινή δομή αρχείων ανά run
- `pred.ttl`: το παραγόμενο ontology/tripleset του run.
- JSON αξιολόγησης και ελέγχων (αναλύονται αναλυτικά στην επόμενη ενότητα):
  - `metrics_exact.json` / `metrics_semantic.json`
  - `cq_results*.json`
  - `run_report.json`
  - `validation_summary.json`
  - `reasoning_report.json`
  - `cq_summary.json`
  - `repair_log.json`
  - `patches.json`
- SHACL αναφορές (`validation_report.ttl`, `shacl_report.ttl`): πλήρες output validator για debugging παραβιάσεων.

## Τι περιέχει κάθε JSON (δομή και περιγραφή)

| Αρχείο | Δομή | Τι περιγράφει |
| --- | --- | --- |
| `metrics_exact.json` / `metrics_semantic.json` | Αντικείμενο με πεδία `precision`, `recall`, `f1`, `pred_triples`, `gold_triples`, `overlap_triples`. | Μετρικές κάλυψης του παραγόμενου tripleset έναντι του gold. Το `exact` ζητά απόλυτη ταύτιση URIs/literals, το `semantic` επιτρέπει ισοδυναμίες. 【F:runs/E1_llm_only/metrics_exact.json†L1-L7】【F:runs/E1_llm_only/metrics_semantic.json†L1-L7】 |
| `cq_results*.json` | Αντικείμενο με `pass_rate`, `passed`, `total` και πίνακα `results` από αντικείμενα `{query, success, message}`. Τα αρχεία με κατάληξη `_iterX` αντιστοιχούν σε συγκεκριμένο iteration. 【F:runs/E1_llm_only/cq_results.json†L1-L27】 | Αναλυτική εκτέλεση ASK competency questions ανά run/iteration. Δεν εμπεριέχει τα ίδια τα triples, μόνο το query και την επιτυχία του. |
| `run_report.json` | Συγκεντρωτικό αντικείμενο. Πεδία: `llm_notes` (σχόλια παραγωγής), `competency_questions` ή `cq_results` (ίδια δομή με `cq_results*.json`), `shacl` (αντικείμενο με `conforms`, `text_report`, `results`), `reasoner` (αντικείμενο με `enabled`, `consistent`, `unsatisfiable_classes`, `notes`), `iterations` (λίστα per-iteration με τα ίδια πεδία), προαιρετικό `patch_notes`. 【F:runs/E2_symbolic_only/run_report.json†L1-L21】【F:runs/E3_no_repair/run_report.json†L1-L41】【F:runs/E3_no_repair/run_report.json†L42-L104】 | Ενοποιεί την εικόνα του run: τι ζήτησε/παρήγαγε το LLM, τι έδωσε το SHACL validator, αν ο reasoner βρίσκει ασυνέπειες και πώς απάντησαν οι CQ. |
| `validation_summary.json` | Αντικείμενο `{total, violations: {hard, soft}}`. 【F:runs/E2_symbolic_only/validation_summary.json†L1-L6】 | Σύνοψη των SHACL παραβιάσεων (σκληρές/ήπιες) χωρίς λεπτομέρειες ανά constraint. |
| `reasoning_report.json` | Αντικείμενο με `notes`, `total_unsat`, `unsat_classes` (λίστα URIs). 【F:runs/E2_symbolic_only/reasoning_report.json†L1-L5】 | Αποτελέσματα συλλογιστικής: πόσες κλάσεις είναι ασυνεπείς και ποια είναι η λίστα τους. |
| `cq_summary.json` | Λίστα αντικειμένων `{iteration, conforms, cq_pass_rate}`. 【F:runs/E6_cq_oriented/cq_summary.json†L1-L17】 | Συνοπτική πρόοδος CQ ανά iteration, χωρίς τα ίδια τα queries. |
| `repair_log.json` | Αντικείμενο ανά iteration με μετρητές `hard`/`soft`. 【F:runs/E4_full/repair_log.json†L1-L10】 | Πόσες SHACL παραβιάσεις απομένουν μετά από κάθε βήμα repair. |
| `patches.json` | Λίστα από patches με πεδία `action`, `subject`, `predicate`, `object`, `message`, `source_shape`, `severity` (και τυχόν πρόσθετα metadata). 【F:runs/E4_full/iter0/patches.json†L1-L24】 | Τι διορθώσεις προτείνονται από το repair loop ανά iteration, χαρτογραφημένες στα SHACL findings. |

### Παραγωγή αρχείων (πώς φτάνουμε στα JSON)

1. **Παραγωγή/ενημέρωση ontology**: το LLM ή ο repair βρόχος γράφει `pred.ttl` (ή `iterX/pred.ttl`).
2. **SHACL validation**: ο validator τρέχει στο παραχθέν ontology και:
   - Καταγράφει λεπτομέρειες σε `run_report.json` (πεδίο `shacl.results` και `text_report`). 【F:runs/E3_no_repair/run_report.json†L42-L104】
   - Συνοψίζει σε `validation_summary.json` και (στα repair runs) σε `repair_log.json` ανά iteration. 【F:runs/E2_symbolic_only/validation_summary.json†L1-L6】【F:runs/E4_full/repair_log.json†L1-L10】
   - Παράγει SHACL reports σε TTL όπου χρειάζεται.
3. **Reasoning**: όπου ενεργοποιημένος, ο reasoner ενημερώνει το `run_report.json` (πεδίο `reasoner`) και, σε runs μόνο-symbolic, γράφει και `reasoning_report.json`. 【F:runs/E2_symbolic_only/reasoning_report.json†L1-L5】【F:runs/E3_no_repair/run_report.json†L1-L41】
4. **Competency Questions**: εκτελούνται ASK queries στο παραγόμενο ontology. Τα αποτελέσματα αποθηκεύονται είτε σαν πλήρης λίστα (`cq_results*.json`, `run_report.json > competency_questions/cq_results`) είτε σαν ποσοστό ανά iteration (`cq_summary.json`). 【F:runs/E1_llm_only/cq_results.json†L1-L27】【F:runs/E6_cq_oriented/cq_summary.json†L1-L17】
5. **Μετρικές κάλυψης**: ο συγκριτής με το gold ontology υπολογίζει precision/recall/F1 και γράφει τα `metrics_exact.json` / `metrics_semantic.json`. 【F:runs/E1_llm_only/metrics_exact.json†L1-L7】

## Αρχεία ανά πείραμα (E1–E6)

- **E1 — `runs/E1_llm_only/`**: `pred.ttl`, `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `run_report.json`. Ενιαίο iteration χωρίς SHACL/repair.
- **E2 — `runs/E2_symbolic_only/`**: Ό,τι στο E1, συν `validation_summary.json` και `reasoning_report.json` για άμεσο SHACL/consistency έλεγχο.
- **E3 — `runs/E3_no_repair/`**: Αρχεία ρίζας (με SHACL & reasoner μέσα στο `run_report.json`), `validation_summary.json`, `validation_report.ttl` και φάκελος `iter0/` με `pred.ttl`. CQ ανά iteration στο `cq_results_iter0.json`.
- **E4 — `runs/E4_full/`**: Iterative repair. Για κάθε iteration (`iter0/`, `iter1/`) υπάρχουν `pred.ttl`, `patches.json`, `shacl_report.ttl`. Το `repair_log.json` συνοψίζει τις παραβιάσεις ανά βήμα. Ο φάκελος `final/` κρατά τις τελικές μετρικές/προβλέψεις (`pred.ttl`, `metrics_*`, `cq_results.json`, `validation_summary.json`).
- **E6 — `runs/E6_cq_oriented/`**: Ενιαίο ontology και μετρικές στη ρίζα, `cq_summary.json` για πρόοδο CQ ανά iteration, `validation_summary.json` και συγκεντρωτικό `run_report.json` με reasoner/SHACL/CQ πληροφορίες.

## Ανάγνωση ανά πείραμα

### E1 — `runs/E1_llm_only/`
- Αρχεία: `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `run_report.json`, `pred.ttl`.
- Ερμηνεία: Ενιαίο iteration. Τα metrics δείχνουν την επικάλυψη με το gold· το CQ αρχείο έχει μία λίστα από ASK queries με πεδίο `success`.

### E2 — `runs/E2_symbolic_only/`
- Προσθήκες σε σχέση με E1: `validation_summary.json` και `reasoning_report.json` για γρήγορο SHACL/consistency έλεγχο.
- Ερμηνεία: Χρησιμοποιήστε `validation_summary.json` για να επιβεβαιώσετε ότι δεν υπάρχουν παραβιάσεις, και `reasoning_report.json` για να δείτε αν υπάρχουν unsatisfiable classes.

### E3 — `runs/E3_no_repair/`
- Δομή: αρχεία ρίζας + φάκελος `iter0/` (π.χ. `iter0/pred.ttl`). Το `cq_results_iter0.json` αντιστοιχεί στο ίδιο iteration.
- Επιπλέον: `validation_report.ttl` δίνει λεπτομέρειες SHACL, πέρα από το σύνοψη `validation_summary.json`.
- Ερμηνεία: Διαβάστε `metrics_*` για συνολική ακρίβεια και `validation_report.ttl` για να εντοπίσετε ποια shapes παραβιάστηκαν.

### E4 — `runs/E4_full/`
- Δομή πολλαπλών iterations: `iter0/` και `iter1/` με `pred.ttl`, `patches.json`, `shacl_report.ttl` ανά iteration.
- Repair log: `repair_log.json` συγκεντρώνει τον αριθμό `hard`/`soft` παραβιάσεων ανά iteration.
- Τελικό αποτέλεσμα: ο φάκελος `final/` περιέχει `pred.ttl`, `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `validation_summary.json` (δηλαδή τις μετρικές μετά το repair loop).
- Ερμηνεία: Χρησιμοποιήστε `patches.json` για να δείτε τι προτάθηκε ανά iteration, `shacl_report.ttl` για λεπτομέρειες παραβιάσεων, και τα αρχεία στο `final/` για την τελική αποτίμηση.

### E6 — `runs/E6_cq_oriented/`
- Δομή: ενιαία `pred.ttl` και μετρικές στην ρίζα, αλλά υπάρχει `cq_summary.json` με λίστα αντικειμένων `{iteration, conforms, cq_pass_rate}`.
- Ερμηνεία: Το `cq_summary.json` δείχνει την πορεία CQ ανά iteration (παρά το ότι δεν υπάρχουν ξεχωριστοί φάκελοι per iteration). Το `validation_summary.json` καταγράφει συνολικά SHACL αποτελέσματα.

## Γρήγορη ροή ανάγνωσης
1. **Κάλυψη:** `metrics_exact.json` και `metrics_semantic.json` → precision/recall/F1 και μέτρηση overlapping triples.
2. **CQ ικανοποίηση:** `cq_results*.json` ή `cq_summary.json` → ποσοστό επιτυχίας (`success` ή `cq_pass_rate`).
3. **Συμμόρφωση:** `validation_summary.json` → αριθμός `hard`/`soft` παραβιάσεων. Για λεπτομέρειες δείτε `validation_report.ttl` ή `shacl_report.ttl`.
4. **Συνεκτικότητα:** `reasoning_report.json` ή πεδίο `reasoner` μέσα στο `run_report.json` → unsatisfiable classes / consistency.
5. **Παραγόμενο ontology:** `pred.ttl` (και, όπου υπάρχει, `final/pred.ttl`) → τελικό μοντέλο προς επιθεώρηση ή φόρτωση σε reasoner/editor.

Με τα παραπάνω βήματα μπορεί κανείς να αναγνώσει και να παρουσιάσει γρήγορα τα αποτελέσματα κάθε πειράματος E1–E6, χωρίς να χρειάζεται να ανοίξει όλα τα logs κάθε φορά.
