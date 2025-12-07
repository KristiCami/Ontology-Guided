# Πείραμα E3 — Ontology-aware σύνταξη χωρίς repair

Το E3 είναι η πρώτη «έξυπνη» έκδοση του συστήματος όπου ενεργοποιούνται όλα τα προχωρημένα components (ontology-aware prompting, λογικός reasoner, SHACL validation), αλλά **χωρίς** repair loop. Στόχος είναι να δούμε πόσο βελτιώνεται το αρχικό draft όταν το LLM καθοδηγείται από το schema και πόσα violations εμφανίζονται χωρίς καμία επιδιόρθωση.

## 1. Τι είναι το E3 και γιατί το τρέχουμε
- Ενεργοποιεί όλα τα advanced components εκτός από το repair: ontology-aware prompting, DL reasoning και SHACL validation τρέχουν, αλλά δεν γίνονται patches.
- Μετράμε πόσο καλύτερο draft παράγει το LLM όταν έχει schema context και πόσο μειώνονται τα λάθη σε σχέση με το E1.
- Αν το E3 δεν είναι εμφανώς καλύτερο από το baseline E1, τότε το ontology-aware prompt είναι μάλλον λανθασμένο.

## 2. Διαφορές σε σχέση με το E1 (baseline)
| Component                  | E1 (baseline LLM only) | E3 (Ours, no-repair) |
| -------------------------- | ---------------------- | -------------------- |
| Ontology-aware prompting   | Όχι                    | Ναι                  |
| SHACL validation           | Όχι                    | Ναι                  |
| DL reasoner                | Όχι                    | Ναι                  |
| Patch calculus             | Όχι                    | Όχι                  |
| Repair loop                | Όχι                    | Όχι                  |
| Iterations                 | 1                      | 1                    |

## 3. Τι πρέπει να κάνει το E3 (βήμα-βήμα)
1. **Φόρτωση schema context πριν το drafting.** Εξάγουμε κλάσεις, object/datatype properties (με domain/range) και labels από το `gold/atm_gold.ttl` και τα περνάμε στο prompt ως δεσμευμένο λεξιλόγιο.
2. **Reasoner πριν το SHACL.** Ο SHACL validator πρέπει να δει το reasoning-expanded γράφημα (κληρονομημένοι περιορισμοί). Αν γίνει skip, προκύπτουν λάθος αρνητικά.
3. **SHACL μόνο για διάγνωση.** Δεν τρέχει repair loop· απλώς μετράμε total/hard/soft violations.
4. **Metrics στο draft.**
   - Exact axiom metrics: precision/recall/F1 με string-identical matching.
   - Semantic metrics: πιο ανεκτικό matching (πρέπει να είναι ≥ των exact scores).
   - CQ pass rate: SPARQL ASK πάνω στο reasoning-expanded γράφημα (`atm_cqs.rq`).
   - SHACL σύνοψη: total/hard/soft violations από το report.
5. **Δομή εξόδου (αυτοτελής).**
   ```
   runs/E3_no_repair/
       iter0/pred.ttl
       validation_report.ttl
       validation_summary.json
       metrics_exact.json
       metrics_semantic.json
       cq_results_iter0.json
   ```
   Το `pred.ttl` είναι το raw draft· όλα τα υπόλοιπα προκύπτουν από το reasoning-expanded γράφημα. Τα gold αρχεία μένουν ως έχουν στο `gold/`.

## 4. Πώς να το τρέξεις
Χρησιμοποιήστε τον preset runner (heuristic LLM by default):

```bash
python scripts/run_atm_examples.py --config configs/atm_ontology_aware.json
```

### Windows PowerShell
```powershell
python scripts/run_atm_examples.py --config configs/atm_ontology_aware.json
```

### macOS / Linux (bash, zsh)
```bash
python scripts/run_atm_examples.py --config configs/atm_ontology_aware.json
```

Βεβαιώσου ότι το `pellet` είναι διαθέσιμο για πλήρες reasoning. Αν λείπει, ο runner θα επιστρέψει μόνο το asserted γράφημα και το SHACL θα το χρησιμοποιήσει χωρίς τα inferred triples.
