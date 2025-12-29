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

- **Μετρικές (`metrics_exact.json`, `metrics_semantic.json`)**: παράγονται από σύγκριση του `pred.ttl` με το gold ontology. Χρησιμοποιούνται για να ποσοτικοποιήσουν την κάλυψη του συστήματος (precision/recall/f1). Τα `pred_triples`, `gold_triples`, `overlap_triples` παρέχουν τους βασικούς μετρητές ώστε να μπορεί να αναπαραχθεί ο υπολογισμός TP/FP/FN. Επιλέχθηκε ζεύγος exact/semantic για να ξεχωρίζει η αυστηρή ταύτιση από την εννοιολογική ισοδυναμία (π.χ. υποκλάσεις, ισοδύναμες κλάσεις).
- **CQ αποτελέσματα (`cq_results*.json`)**: δημιουργούνται από εκτέλεση ASK SPARQL queries πάνω στο `pred.ttl`. Το `pass_rate` (= `passed/total`) δίνει την κάλυψη απαιτήσεων σε επίπεδο competency questions. Κάθε αντικείμενο `results` περιέχει το query (`query`), την επιτυχία (`success`) και σχόλιο/λάθος (`message`) για να διευκολύνει debugging. Η δομή είναι επίπεδη ώστε να μπορεί να οπτικοποιηθεί ή να εξαχθεί εύκολα σε dashboards.
- **Συγκεντρωτικό report (`run_report.json`)**: συντίθεται στο τέλος κάθε run και συγκεντρώνει LLM context, SHACL, reasoner και CQ. Το `llm_notes` καταγράφει prompts/μετασχηματισμούς, επιτρέποντας αναπαραγωγή. Το τμήμα `shacl` φέρει λεπτομέρειες παραβιάσεων (focus node, path, constraint component) που χρησιμοποιούνται downstream από το repair module. Το τμήμα `reasoner` δηλώνει συνέπεια/unsat classes, απαραίτητο για semantic αξιολόγηση. Το `iterations` επαναλαμβάνει τα ίδια πεδία ανά βήμα ώστε να παρακολουθείται η εξέλιξη σε repair ή CQ-oriented runs. Το `patch_notes` δίνει κείμενο-σύνοψη για τα patches που προτάθηκαν, ώστε να συνδέεται η SHACL ανάλυση με τις τροποποιήσεις.
- **Σύνοψη SHACL (`validation_summary.json`)**: παράγεται απευθείας από τον validator για γρήγορη επισκόπηση. Τα `hard`/`soft` ξεχωρίζουν κρίσιμες από ήπιες παραβιάσεις. Το `total` διευκολύνει thresholds/alarms σε αυτοματοποιημένους ελέγχους.
- **Reasoning (`reasoning_report.json`)**: προκύπτει από OWL reasoner (π.χ. HermiT/ELK). Το `total_unsat` και `unsat_classes` επιτρέπουν να εντοπιστούν σφάλματα μοντελοποίησης που δεν ανιχνεύονται από SHACL (π.χ. αντιφάσεις). Το `notes` χρησιμοποιείται για metadata του reasoner ή παρατηρήσεις εκτέλεσης.
- **CQ σύνοψη (`cq_summary.json`)**: aggregation των CQ ανά iteration, ώστε να φαίνεται η τάση βελτίωσης χωρίς να μεταφέρονται όλα τα queries. Το `conforms` συνήθως αντιστοιχεί στη SHACL κατάσταση του ίδιου iteration, επιτρέποντας συσχέτιση CQ και validation προόδου.
- **Repair log (`repair_log.json`)**: καταγράφει μετρητές παραβιάσεων μετά την εφαρμογή των patches κάθε iteration. Επιλέχθηκε απλή δομή key-value για να είναι εύκολα αναλώσιμη από scripts/plots και να παρακολουθείται η σύγκλιση του repair loop.
- **Patches (`patches.json`)**: κατασκευάζονται από τον repair agent βάσει SHACL violations. Η δομή περιλαμβάνει `action` και τα RDF στοιχεία (`subject`/`predicate`/`object`) ώστε να μεταφράζονται απευθείας σε τροποποιήσεις triples. Το `source_shape` και `severity` δένουν το patch με το αντίστοιχο violation, ενώ το `message` αιτιολογεί την αλλαγή. Προαιρετικά metadata (`datatype`, `cardinality` κ.ά.) υποστηρίζουν αυτόματη εφαρμογή ή χειροκίνητο review.

### Παραγωγή αρχείων (πώς φτάνουμε στα JSON)

1. **Παραγωγή/ενημέρωση ontology**: το LLM ή ο repair βρόχος γράφει `pred.ttl` (ή `iterX/pred.ttl`).
2. **SHACL validation**: ο validator τρέχει στο παραχθέν ontology και:
   - Καταγράφει λεπτομέρειες σε `run_report.json` (πεδίο `shacl.results` και `text_report`).
   - Συνοψίζει σε `validation_summary.json` και (στα repair runs) σε `repair_log.json` ανά iteration.
   - Παράγει SHACL reports σε TTL όπου χρειάζεται.
3. **Reasoning**: όπου ενεργοποιημένος, ο reasoner ενημερώνει το `run_report.json` (πεδίο `reasoner`) και, σε runs μόνο-symbolic, γράφει και `reasoning_report.json`.
4. **Competency Questions**: εκτελούνται ASK queries στο παραγόμενο ontology. Τα αποτελέσματα αποθηκεύονται είτε σαν πλήρης λίστα (`cq_results*.json`, `run_report.json > competency_questions/cq_results`) είτε σαν ποσοστό ανά iteration (`cq_summary.json`).
5. **Μετρικές κάλυψης**: ο συγκριτής με το gold ontology υπολογίζει precision/recall/F1 και γράφει τα `metrics_exact.json` / `metrics_semantic.json`.

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
