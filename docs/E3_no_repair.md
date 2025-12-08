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

## 3. (E3 / no-repair)
- **Grounding TTL:** `gold/atm_gold.ttl` (η μοναδική gold οντολογία στο repo).
- **SHACL shapes:** `gold/shapes_atm.ttl` (χρησιμοποιείται αυτούσιο, δεν αναπαράγεται).
- **Baseline draft path:** `build/pred.ttl` (όλα τα αρχεία draft/metrics που παράγονται από το νέο preset γράφονται στο `runs/E3_no_repair/`).

Ο ευκολότερος τρόπος για να τρέξετε το E3 preset χωρίς repair loop είναι το προρυθμισμένο script:

```bash
python scripts/run_atm_examples.py --config configs/atm_ontology_aware.json
```

Τι κάνει το preset:
- Φορτώνει λεξιλόγιο από `gold/atm_gold.ttl` ως ontology-aware context, χωρίς να συγχωνεύει τις gold τριπλέτες στο draft.
- Τρέχει reasoner και περνά το reasoning-expanded γράφημα στον SHACL validator, ώστε τα κληρονομημένα constraints να ελεγχθούν σωστά.
- Εκτελεί CQs (`atm_cqs.rq`) πάνω στο ίδιο expanded γράφημα.
- Υπολογίζει exact/semantic metrics (η semantic βαθμολογία δεν πέφτει κάτω από την exact) και σύνοψη hard/soft violations.

Η έξοδος γράφεται σε:

```
runs/E3_no_repair/
  iter0/pred.ttl          ← draft της 1ης (και μοναδικής) iter
  validation_report.ttl   ← SHACL report από το gold/shapes_atm.ttl
  validation_summary.json ← μετρητής hard/soft παραβιάσεων
  metrics_exact.json      ← precision/recall/F1 vs gold/atm_gold.ttl
  metrics_semantic.json   ← semantic scorer με tolerance/normalisation
  reasoning_report.json   ← unsat classes από reasoner (αν owlready2/ Pellet διαθέσιμο)
  cq_results_iter0.json   ← αποτελέσματα από `atm_cqs.rq` (αν το path είναι στο config)
```

Τα αρχεία αυτά **δεν είναι προϋπάρχοντα**. Παράγονται μόνο όταν εκτελεστεί η παραπάνω εντολή και δεν αγγίζουν/αναγράφουν τα δεδομένα στον φάκελο `gold/`. Δείτε και το `docs/E3_no_repair.md` για πλήρη περιγραφή του πειράματος.
