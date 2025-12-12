# Πείραμα E4 — Iterative Repair Loop

Το E4 επεκτείνει το E3 ενεργοποιώντας πλήρως το repair loop. Η λογική είναι να κρατήσουμε ένα σταθερό draft από το iteration 0 και να εφαρμόζουμε αυστηρά SHACL-driven patches μέχρι να σταματήσει η πρόοδος ή να εξαφανιστούν τα hard violations.

## Μεθοδολογία (βήμα-βήμα)
1. **Πριν το loop**
   - Φορτώνουμε **μόνο** το `gold/atm_gold.ttl` για schema extraction (ontology-aware prompting). Δεν συνδυάζεται με κανένα pred.
   - Οι απαιτήσεις διαβάζονται από `baseline_requirements.jsonl` και chunkάρονται σε παρτίδες των 5.

2. **Iteration 0 — Drafting χωρίς patches**
   - Το LLM συνθέτει την αρχική οντολογία από requirements + schema context. Το `pred.ttl` γράφεται στο `runs/E4_full/iter0/pred.ttl`.
   - Δεν φορτώνεται προηγούμενη οντολογία ή `pred.ttl` από άλλα runs το draft είναι **from scratch**.

3. **Reasoning ανά iteration**
   - Ο Pellet (ή fallback reasoner) τρέχει **πάντα** πάνω στο `pred.ttl` του τρέχοντος iteration και παράγει expanded graph στη μνήμη.
   - Το gold δεν συμμετέχει στο reasoning μετά το iteration 0.

4. **SHACL validation**
   - Είσοδος: `gold/shapes_atm.ttl` + expanded graph.
   - Έξοδος: `shacl_report.ttl` και `validation_summary.json` με hard/soft counts.

5. **Patch calculus**
   - Μεταφράζει **μόνο** τα hard violations σε `patches.json` (δομή τύπου `{action, subject, predicate, object, message}`) χωρίς καμία αναφορά στο gold ontology.

6. **Εφαρμογή patches με LLM**
   - Input: τρέχον `pred.ttl` + `patches.json`.
   - Prompt: «μην δημιουργήσεις νέους πόρους, εφάρμοσε μόνο τα patches, κράτα prefixes και όλα τα υπόλοιπα triples as-is».
   - Output: νέο `pred.ttl` για το επόμενο iteration.

7. **Loop logic / stopping criteria**
   - Τερματισμός αν: (α) hard violations == 0, (β) `patches.json` κενό, (γ) ίδιο patch plan με το προηγούμενο, (δ) CQ pass rate ≥ threshold (π.χ. 0.8), (ε) `iteration >= kmax`.

8. **Τελική αξιολόγηση**
   - Στο `runs/E4_full/final/` γράφονται `pred.ttl`, `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, `validation_summary.json`.
   - `repair_log.json` στο root με `{iterX: {hard, soft}}` για debugging/βελτίωση.

## Πώς τρέχει
```bash
python scripts/run_e4_iterative.py --config configs/atm_e4_iterative.json --kmax 3 --cq-threshold 0.8
```

Η έξοδος ακολουθεί την επιβεβαιωμένη δομή:

```
runs/E4_full/
  iter0/ pred.ttl, shacl_report.ttl, patches.json
  iter1/ ...
  iter2/ ...
  final/ pred.ttl, metrics_exact.json, metrics_semantic.json, cq_results.json, validation_summary.json
  repair_log.json
```

Κρίσιμες απαντήσεις:
- Κάθε iteration φορτώνει **μόνο** το πιο πρόσφατο `pred.ttl`.
- Το gold χρησιμοποιείται μόνο για ontology-aware prompting στο iteration 0 και για metrics στο τέλος.
- Το LLM γράφει ολόκληρο `pred.ttl` σε κάθε iteration, επηρεασμένο μόνο από τα patches.
- Reasoning + SHACL τρέχουν πριν από κάθε patch calculus.

## Αποτελέσματα του run `E4_full`
- Το loop σταμάτησε στο iteration 0 επειδή η SHACL αναφορά επέστρεψε `conforms = true`, άρα δεν υπήρξαν hard violations για να παραχθούν patches ή επόμενα iterations (βλ. `repair_log.json`).
- Η τελική οντολογία απέτυχε να καλύψει τις περισσότερες απαιτήσεις η CQ pass rate ήταν ~4.8% (1/21) σύμφωνα με το `cq_results.json`, αποτυπώνοντας ότι το στάδιο drafting χρειάζεται βελτιώσεις παρά την απουσία SHACL σφαλμάτων.
- Τα exact/semantic metrics ήταν χαμηλά (P=0.0833, R=0.032, F1=0.0462 με 4/125 overlaps), δείχνοντας μεγάλο κενό από το gold, οπότε απαιτούνται ισχυρότερα constraints ή διαφορετικό prompting στο drafting.
