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
| `metrics_exact.json` / `metrics_semantic.json` | Αντικείμενο με πεδία:<br>• `precision` (number)<br>• `recall` (number)<br>• `f1` (number)<br>• `pred_triples`, `gold_triples`, `overlap_triples` (integers) | Μετρικές κάλυψης του παραγόμενου tripleset έναντι του gold. Το `exact` ζητά απόλυτη ταύτιση URIs/literals, το `semantic` επιτρέπει ισοδυναμίες. |
| `cq_results*.json` | Αντικείμενο με:<br>• `pass_rate` (0–1), `passed` (int), `total` (int)<br>• `results` (λίστα) με αντικείμενα: `{query: string, success: bool, message: string}`. `_iterX` εκδόσεις αντιστοιχούν σε συγκεκριμένο iteration. | Αναλυτική εκτέλεση ASK competency questions ανά run/iteration. Δεν εμπεριέχει τα ίδια τα triples, μόνο το query και την επιτυχία του. |
| `run_report.json` | Συγκεντρωτικό αντικείμενο με βασικά πεδία:<br>• `llm_notes` (string)<br>• `competency_questions` ή `cq_results` (ίδια δομή με `cq_results*.json`)<br>• `shacl` (αντικείμενο με `conforms` (bool), `text_report` (string), `results` (λίστα αντικειμένων `{focus_node, path, message, severity, source_shape, constraint_component, value}`))<br>• `reasoner` (αντικείμενο `{enabled, consistent, unsatisfiable_classes: [], notes}`)<br>• `iterations` (λίστα από αντικείμενα με τα ίδια πεδία, επιπλέον `iteration`, `conforms` ανά βήμα)<br>• προαιρετικό `patch_notes` (string). | Ενοποιεί την εικόνα του run: τι ζήτησε/παρήγαγε το LLM, τι έδωσε το SHACL validator, αν ο reasoner βρίσκει ασυνέπειες και πώς απάντησαν οι CQ. |
| `validation_summary.json` | Αντικείμενο `{total: int, violations: {hard: int, soft: int}}`. | Σύνοψη των SHACL παραβιάσεων (σκληρές/ήπιες) χωρίς λεπτομέρειες ανά constraint. |
| `reasoning_report.json` | Αντικείμενο με πεδία:<br>• `notes` (string)<br>• `total_unsat` (int)<br>• `unsat_classes` (λίστα URIs). | Αποτελέσματα συλλογιστικής: πόσες κλάσεις είναι ασυνεπείς και ποια είναι η λίστα τους. |
| `cq_summary.json` | Λίστα αντικειμένων `{iteration: int, conforms: bool, cq_pass_rate: number}`. | Συνοπτική πρόοδος CQ ανά iteration, χωρίς τα ίδια τα queries. |
| `repair_log.json` | Αντικείμενο με κλειδιά ανά iteration και τιμές `{hard: int, soft: int}`. | Πόσες SHACL παραβιάσεις απομένουν μετά από κάθε βήμα repair. |
| `patches.json` | Λίστα από αντικείμενα patches με πεδία:<br>• `action` (π.χ. `addProperty`, `deleteTriple`)<br>• `subject`, `predicate`, `object` (URIs ή datatypes)<br>• `message` (αιτιολόγηση)<br>• `source_shape` (SHACL shape id)<br>• `severity` (Violation/Warning/Info)<br>+ προαιρετικά: `datatype`, `cardinality`, ή άλλα metadata που σχετίζονται με τον SHACL κανόνα. | Τι διορθώσεις προτείνονται από το repair loop ανά iteration, χαρτογραφημένες στα SHACL findings. |

### Τεχνική σημασία πεδίων και ροή παραγωγής

- **Μετρικές (`metrics_exact.json`, `metrics_semantic.json`)**: παράγονται από σύγκριση του `pred.ttl` με το gold ontology. Τα πεδία precision/recall/f1 είναι τα κλασικά ποσοστά TP/FP/FN, ενώ τα `pred_triples`, `gold_triples`, `overlap_triples` είναι οι απόλυτοι μετρητές που τροφοδοτούν τους λόγους. Η semantic εκδοχή επιτρέπει ισοδυναμίες/υποκατηγοριοποιήσεις πριν τον υπολογισμό TP/FP/FN.
- **CQ αποτελέσματα (`cq_results*.json`)**: δημιουργούνται από εκτέλεση ASK SPARQL queries πάνω στο `pred.ttl`. Το `pass_rate` υπολογίζεται ως `passed/total`. Κάθε αντικείμενο στη λίστα `results` περιλαμβάνει το κείμενο του query (`query`), το boolean αποτέλεσμα (`success`) και τυχόν πρόσθετο σχόλιο/λάθος (`message`, συχνά κενό).
- **Συγκεντρωτικό report (`run_report.json`)**: συντίθεται στο τέλος κάθε run. Το `llm_notes` κρατά το prompt/απόκριση ή τις μετασχηματίσεις του LLM. Το τμήμα `shacl` προέρχεται από τον SHACL validator: `conforms` είναι boolean, το `text_report` είναι η ανθρώπινη αναφορά, και το `results` είναι λίστα violation entries (με focus node, path, constraint component κ.λπ.). Το τμήμα `reasoner` γεμίζει από τον reasoner (π.χ. OWL) και δηλώνει αν η TBox/ABox είναι συνεπής και ποιες κλάσεις είναι unsatisfiable. Το `iterations` επαναλαμβάνει τα ίδια πεδία ανά βήμα (repair loop ή CQ iterations). Το `patch_notes` καταγράφει περιγραφικά ό,τι παρήχθη στο στάδιο προτάσεων patch.
- **Σύνοψη SHACL (`validation_summary.json`)**: παράγεται απευθείας από το αποτέλεσμα του validator, με `total` πλήθος παραβιάσεων και διάκριση `hard`/`soft` με βάση τη σοβαρότητα (π.χ. Violation vs Warning).
- **Reasoning (`reasoning_report.json`)**: γεμίζει μετά την εκτέλεση reasoner· `total_unsat` είναι μετρητής unsatisfiable classes, `unsat_classes` η λίστα URIs, `notes` κρατά τεχνικά σχόλια (π.χ. ποιος reasoner χρησιμοποιήθηκε).
- **CQ σύνοψη (`cq_summary.json`)**: προκύπτει από aggregation των αποτελεσμάτων CQ ανά iteration. Το `conforms` τυπικά αντικατοπτρίζει το SHACL αποτέλεσμα του ίδιου βήματος, ενώ το `cq_pass_rate` είναι ο μέσος όρος επιτυχίας queries στο iteration.
- **Repair log (`repair_log.json`)**: παράγεται μετά από κάθε SHACL validation στο repair loop. Για κάθε iteration κλειδί, οι μετρητές `hard`/`soft` είναι το πλήθος παραβιάσεων που παραμένουν μετά την εφαρμογή του patch set εκείνου του βήματος.
- **Patches (`patches.json`)**: κατασκευάζονται από τον repair agent βάσει των SHACL violations. Κάθε αντικείμενο είναι μια προτεινόμενη τριπλέτα ή αλλαγή. Το `action` δηλώνει το είδος μεταβολής, τα `subject`/`predicate`/`object` δίνουν τους πόρους ή datatypes, το `message` αιτιολογεί, το `source_shape` δείχνει ποιο SHACL shape προκάλεσε το patch, και το `severity` ταιριάζει με τη σοβαρότητα του violation. Προαιρετικά πεδία εξειδικεύουν περιορισμούς (π.χ. `datatype`, `cardinality`) για να διευκολυνθεί η εφαρμογή.

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
