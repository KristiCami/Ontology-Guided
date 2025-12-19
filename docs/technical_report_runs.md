# Τεχνική Αναφορά Αποτελεσμάτων (Runs)

## Σκοπός και Πεδίο
Η παρούσα αναφορά αξιολογεί **τα αποτελέσματα των πειραμάτων E1–E6** όπως περιγράφονται στο `README.md` (Table A) και όπως έχουν αποθηκευτεί στον φάκελο `runs/`. Η αξιολόγηση βασίζεται στα διαθέσιμα JSON logs (metrics, CQ, SHACL, reasoning) και στο `repair_log` όπου υπάρχει.

**Πηγή δεδομένων**
- `runs/E1_llm_only/*`
- `runs/E2_symbolic_only/*`
- `runs/E3_no_repair/*`
- `runs/E4_full/*`
- `runs/E6_cq_oriented/*`

> **Σημείωση για E5:** Δεν υπάρχει φάκελος `runs/E5_cross_domain` στα διαθέσιμα artefacts, συνεπώς δεν είναι δυνατή ποσοτική αξιολόγηση για το E5.

---

## Σύνοψη Μετρικών (ATM πείραμα)
Οι μετρικές προέρχονται από τα `metrics_exact.json`, `metrics_semantic.json`, `validation_summary.json`, `reasoning_report.json`, και `cq_results*.json`/`cq_summary.json`.

| Πείραμα | Precision (exact) | Recall (exact) | F1 (exact) | Precision (semantic) | Recall (semantic) | F1 (semantic) | CQ pass rate | SHACL violations (hard/soft/total) | Unsat classes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **E1 LLM-only** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0476 (1/21) | – | – |
| **E2 Symbolic-only** | 0.0833 | 0.0320 | 0.0462 | 0.0678 | 0.0320 | 0.0435 | 0.0476 (1/21) | 0 / 0 / 0 | 0 |
| **E3 Ours (no-repair)** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0476 (1/21) | 10 / 2 / 12 | 0 |
| **E4 Ours (full)** | – | – | – | – | – | – | – | iter0: 8/0, iter1: 8/0 | – |
| **E6 CQ-oriented** | 0.0096 | 0.0080 | 0.0087 | 0.0270 | 0.0080 | 0.0123 | 0.0952 (2/21)* | 11 / 0 / 11 | – |

\* Στο E6, το CQ pass rate προέρχεται από `cq_summary.json` ανά iteration. Η τιμή 0.0952 αντιστοιχεί σε 2/21. Η σταθερότητα του ίδιου ποσοστού σε όλα τα iterations δείχνει ότι η CQ επίδοση **δεν βελτιώθηκε** κατά τις επαναλήψεις.

---

## Αναλυτική Αξιολόγηση Ανά Πείραμα

### E1 — LLM-only baseline
**Ευρήματα:**
- Μηδενική επικάλυψη με το gold σύνολο τόσο σε exact όσο και σε semantic matching.
- CQ pass rate 1/21 (≈4.76%), δηλαδή μόνο 1 competency question ικανοποιείται.

**Ερμηνεία:**
Το αποτέλεσμα υποδηλώνει ισχυρό semantic drift ή ασυμβατότητα του παραγόμενου λεξιλογίου με το gold schema. Παρά το ότι παράχθηκαν 113 triples, κανένα δεν ταυτίζεται με το gold σύνολο.

### E2 — Symbolic-only baseline
**Ευρήματα:**
- Καλύτερη ακρίβεια από E1 (precision 0.0833 exact), αλλά πολύ χαμηλή ανάκληση (0.032).
- CQ pass rate παραμένει 1/21.
- SHACL violations: 0 (hard/soft).
- 0 unsatisfiable classes.

**Ερμηνεία:**
Η symbolic διαδικασία παράγει λίγα αλλά σχετικά πιο σωστά triples (χαμηλή recall, μέτρια precision). Η μηδενική παραβίαση SHACL δείχνει ότι το output είναι «ασφαλές» δομικά, αλλά φτωχό σε κάλυψη, κάτι που φαίνεται και στις CQ αποτυχίες.

### E3 — Ours (no-repair)
**Ευρήματα:**
- Μηδενικά exact/semantic matches με το gold.
- SHACL violations: 10 hard + 2 soft (σύνολο 12).
- CQ pass rate 1/21.
- Reasoning: 0 unsat, με σημείωση για coercion 4 invalid literals σε `xsd:string`.

**Ερμηνεία:**
Η ontology-aware φάση χωρίς repair δεν οδηγεί σε σύγκλιση με το gold (F1=0). Επιπλέον, οι SHACL παραβιάσεις δείχνουν ασυμβατότητα με σχήματα. Η αναγκαστική μετατροπή literals υποδηλώνει επίσης ασυμφωνίες τύπων.

### E4 — Ours (full, iterative repair)
**Διαθέσιμα δεδομένα:**
- `repair_log.json` με hard/soft violations ανά iteration.

**Ευρήματα:**
- Hard violations: 8 στο iter0 και 8 στο iter1 (καμία μείωση).
- Soft violations: 0 σε όλες τις καταγραφές.

**Ερμηνεία:**
Με τα υπάρχοντα logs, **δεν τεκμηριώνεται βελτίωση** των hard violations στο δεύτερο iteration. Δεν υπάρχουν διαθέσιμες μετρικές F1 ή CQ για να αξιολογηθεί συνολικά η επίδραση του repair. Χρειάζονται επιπλέον outputs (metrics, CQ, validation summary) για πλήρη συγκριτική αξιολόγηση.

### E6 — CQ-oriented
**Ευρήματα:**
- Μικρό αλλά μη μηδενικό overlap (1 triple) με το gold.
- CQ pass rate 0.0952 (2/21), σταθερό σε 4 iterations.
- SHACL violations: 11 hard.

**Ερμηνεία:**
Η CQ-κατευθυνόμενη ρύθμιση βελτιώνει ελαφρώς την CQ επίδοση σε σχέση με E1–E3, αλλά χωρίς πρόοδο κατά τις επαναλήψεις. Η σταθερή παραβίαση 11 hard constraints υποδηλώνει ότι το CQ optimization δεν συνοδεύτηκε από δομική συμμόρφωση.

---

## Συγκριτική Αποτίμηση & Σημεία για Ακαδημαϊκή Παρουσίαση

1. **Coverage vs. Conformance trade-off**
   - E2 δείχνει το αναμενόμενο συμβολικό μοτίβο: μικρό output, χαμηλή recall αλλά καμία παραβίαση SHACL.
   - E1/E3 παράγουν περισσότερα triples χωρίς αντιστοίχιση στο gold και με χαμηλή CQ επίδοση.

2. **CQ performance**
   - Η CQ επιτυχία είναι συνολικά πολύ χαμηλή (1–2 στα 21).
   - Το E6 παρουσιάζει **οριακή βελτίωση** (2/21), αλλά χωρίς δυναμική ανά iteration.

3. **SHACL συμμόρφωση**
   - Μόνο το E2 έχει πλήρη συμμόρφωση.
   - Το E3 και E6 εμφανίζουν πολλαπλές hard παραβιάσεις, γεγονός που περιορίζει την καταλληλότητα του παραγόμενου ontology για downstream χρήση.

4. **Απουσία δεδομένων για E4/E5**
   - Για E4 υπάρχει μόνο repair log χωρίς πλήρη metrics/CQ.
   - Για E5 δεν υπάρχουν καθόλου logs. Για ολοκληρωμένη δημοσίευση απαιτείται επαναληπτική εκτέλεση ή συμπλήρωση artefacts.

---

## Προτάσεις για Περαιτέρω Εμπλουτισμό των Logs
Για πληρέστερη και αναπαραγώγιμη ακαδημαϊκή παρουσίαση:
- Καταγραφή `metrics_exact/semantic.json` και `cq_results.json` για κάθε iteration του E4.
- Ενιαία `validation_summary.json` ανά iteration (iter0/iter1/...) για E4/E6.
- Παρουσίαση αποτελεσμάτων του E5 (cross-domain) με αντίστοιχα logs.

---

## Συμπέρασμα
Με βάση τα διαθέσιμα logs, **η συμβολική baseline (E2) εμφανίζει την καλύτερη SHACL συμμόρφωση**, αλλά χαμηλή κάλυψη. Οι LLM-βασισμένες ρυθμίσεις (E1/E3/E6) δεν ευθυγραμμίζονται με το gold schema και εμφανίζουν χαμηλές CQ επιδόσεις. Το E6 βελτιώνει οριακά τις CQ, χωρίς όμως μείωση των hard violations. Η πλήρης αξιολόγηση του κλειστού βρόχου (E4) και του cross-domain (E5) παραμένει ανοικτή λόγω ελλείψεων στα artefacts.
