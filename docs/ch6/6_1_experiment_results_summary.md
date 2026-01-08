# 6.1 Σύνοψη αποτελεσμάτων πειραμάτων (E1–E6)

Η ενότητα συνοψίζει τα κύρια αποτελέσματα αξιολόγησης για τα πειράματα E1–E6, όπως αποτυπώνονται στα JSON των `runs/` και αναλύονται εκτενώς στο `runs/e1_to_e6_runs_analysis.md`. Τα μεγέθη παρατίθενται για να δώσουν συνοπτική εικόνα πριν από την αναλυτική συζήτηση.

## Πίνακας συνοπτικών αποτελεσμάτων

| ID / Παραλλαγή | Domain / Setup | Semantic F1 (Exact) | CQ Pass | SHACL | Reasoner | Iters / Stop | Σχόλια |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E1 (seed1, draft) | ATM, LLM-only | 0.4769 (0.4769) | 11/21 (0.524) | N/A | N/A | Draft-only | 156 pred triples, 1 559 tokens (`runs/E1_llm_only_seed1`) |
| E1 (seed2, draft) | ATM, LLM-only | 0.1079 (0.1079) | 2/21 (0.095) | N/A | N/A | Draft-only | 190 pred triples, 1 416 tokens (`runs/E1_llm_only_seed2`) |
| E2 symbolic | ATM, rules+reasoner | 0.3333 (0.3670) | 12/21 (0.571) | 0/0 | true | Single pass | 289 pred, 36 missing classes (`runs/E2_symbolic_only`) |
| E3 no-repair | ATM, few-shot | 0.2451 (0.2451) | 12/21 (0.571) | 0/0 | true | Iter0 only | 438 pred, 40 invalid restrictions removed (`runs/E3_no_repair`) |
| E4 full – default | ATM, closed loop | 0.3052 (0.3052) | 11/21 (0.524) | 0/0 | true | 2 iters, stop: no_hard_violations | 15 patches/iter, pred 314 (`runs/E4_full_default/final`) |
| E4 full – hard_and_cq | ATM, aggressive stop | 0.0442 (0.0442) | 4/21 (0.190) | 0/0 | null | 3 iters, stop: patches_unchanged | Pred 871, Pellet NPEs (`runs/E4_full_hard_and_cq/final`) |
| E4 full – max_only | ATM, capped iters | 0.3427 (0.3427) | 11/21 (0.524) | 0/0 | true | 4 iters, stop: max_iterations_reached | Pred 266, stable Pellet (`runs/E4_full_max_only/final`) |
| E4 full – ignore_no_hard | ATM, ignore hard | 0.0343 (0.0343) | 16/21 (0.762) | 0/0 | null | 3 iters, stop: patches_unchanged | Pred 2 380, Pellet NPEs (`runs/E4_full_ignore_no_hard/final`) |
| E5 cross-domain (ATM) | ATM, prompt swap | 0.2191 (0.2296) | 6/21 (0.286) | 0/0 | null | Draft-only | 231 pred, Pellet NPE (`runs/E5_cross_domain/atm`) |
| E5 cross-domain (Health) | Health, prompt swap | 0.0909 (0.0484) | 1/8 (0.125) | 0/0 | null | Draft-only | 212 pred, 140 invalid restrictions dropped (`runs/E5_cross_domain/health`) |
| E6 CQ sweep (thr 0.5) | ATM, repair with p≥0.5 | N/A | 3/21 (iter1–2) | 0/0 | null | 3 iters, stop: patches_unchanged | Pass rate 0.048→0.143→0.143, triples after reasoning 382→1079 (`runs/E6_cq_sweep/threshold_0_5`) |
| E6 CQ sweep (thr 0.8) | ATM, repair with p≥0.8 | N/A | 11/21 (iter0–1) | 0/0 | true | 2 iters, stop: patches_unchanged | Pass rate stable 0.524, triples after reasoning 280 (`runs/E6_cq_sweep/threshold_0_8`) |

## Σημειώσεις ανάγνωσης
- Τα σκόρ παρατίθενται ως **semantic F1**, με την exact τιμή σε παρένθεση όπου υπάρχει.
- Το πεδίο **CQ Pass** αφορά το ποσοστό επιτυχημένων competency questions.
- Τα **SHACL** και **Reasoner** προέρχονται από τα `validation_summary.json` και `repair_log.json` αντίστοιχα.
- Για αναλυτική τεκμηρίωση (αναφορά JSON, ερμηνεία αποκλίσεων, λεπτομερή σχόλια) δείτε το `runs/e1_to_e6_runs_analysis.md`.
