# 6.5 Πίνακες ανά πείραμα (E1–E6)

Οι παρακάτω πίνακες συγκεντρώνουν δομημένα τα βασικά στοιχεία ανά πείραμα. Στόχος είναι να προσφέρεται γρήγορη οπτική σύγκριση των μετρικών, των CQs και της συμπεριφοράς του repair loop.

## E1 – LLM-only (seed1, seed2)

| Παράμετρος | Seed1 | Seed2 |
| --- | --- | --- |
| Semantic F1 (Exact) | 0.4769 (0.4769) | 0.1079 (0.1079) |
| Precision / Recall | 0.4295 / 0.536 | 0.0895 / 0.136 |
| CQ Pass | 11/21 (0.524) | 2/21 (0.095) |
| Pred triples | 156 | 190 |
| Mode | draft_only | draft_only |

## E2 – Symbolic-only

| Παράμετρος | Τιμή |
| --- | --- |
| Semantic F1 (Exact) | 0.3333 (0.3670) |
| Precision / Recall (semantic) | 0.2388 / 0.552 |
| CQ Pass | 12/21 (0.571) |
| Pred triples | 289 (semantic), 251 (exact) |
| Reasoner | consistent: true, 36 missing classes |
| SHACL | 0/0 |

## E3 – Few-shot χωρίς repair

| Παράμετρος | Τιμή |
| --- | --- |
| Semantic F1 (Exact) | 0.2451 (0.2451) |
| Precision / Recall | 0.1575 / 0.552 |
| CQ Pass | 12/21 (0.571) |
| Pred triples | 438 |
| Reasoner | 25 missing classes, 40 invalid restrictions removed |
| SHACL | 0/0 |

## E4 – Full repair (συγκριτικός πίνακας παραλλαγών)

| Παραλλαγή | Semantic F1 (Exact) | CQ Pass | Pred triples | Stop reason | Σχόλια |
| --- | --- | --- | --- | --- | --- |
| default | 0.3052 (0.3052) | 11/21 (0.524) | 314 | no_hard_violations | 15 patches/iter |
| hard_and_cq | 0.0442 (0.0442) | 4/21 (0.190) | 871 | patches_unchanged | Pellet NPEs |
| max_only | 0.3427 (0.3427) | 11/21 (0.524) | 266 | max_iterations_reached | σταθερό Pellet |
| ignore_no_hard | 0.0343 (0.0343) | 16/21 (0.762) | 2 380 | patches_unchanged | Pellet NPEs |

## E5 – Cross-domain (ATM/Health)

| Παράμετρος | ATM | Health |
| --- | --- | --- |
| Semantic F1 (Exact) | 0.2191 (0.2296) | 0.0909 (0.0484) |
| CQ Pass | 6/21 (0.286) | 1/8 (0.125) |
| Pred triples | 231 | 212 |
| Reasoner | Pellet NPE | Pellet NPE |
| Notes | prompt swap | 140 invalid restrictions dropped |

## E6 – CQ sweep (thresholds)

| Threshold | CQ Pass (iter) | Iterations | Stop reason | Notes |
| --- | --- | --- | --- | --- |
| 0.5 | 3/21 (iter1–2) | 3 | patches_unchanged | Pass rate 0.048→0.143→0.143 |
| 0.8 | 11/21 (iter0–1) | 2 | patches_unchanged | Pass rate stable 0.524 |
