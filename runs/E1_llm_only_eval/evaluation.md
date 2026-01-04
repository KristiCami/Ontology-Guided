# E1 LLM-only baseline – two-temperature sweep (seed1=0.1, seed2=0.7)

## Summary metrics
| Run | Temperature | Precision | Recall | F1 | Pred triples | Gold triples | Overlap triples |
| --- | ----------- | --------- | ------ | -- | ------------- | ------------ | ---------------- |
| seed1 | 0.1 | 0.4295 | 0.5360 | 0.4769 | 156 | 125 | 67 |
| seed2 | 0.7 | 0.0895 | 0.1360 | 0.1079 | 190 | 125 | 17 |

## CQ outcomes
| Run | Pass rate | Passed / Total |
| --- | --------- | -------------- |
| seed1 | 0.524 | 11 / 21 |
| seed2 | 0.095 | 2 / 21 |

## Observations
- Higher temperature (seed2=0.7) sharply reduced precision/recall/F1 and CQ pass rate, despite producing more triples, indicating substantial semantic drift.
- Both runs avoided redundant or off-namespace axioms (no drift samples reported). Token usage was comparable (seed1 total 1559 vs seed2 total 1416 tokens).
- Variation across just two runs is large; conclusions are sensitive to sampling temperature.

## Suitability for academic reporting
- With only two seeds and high variance, the results are **not yet statistically stable** for publication-quality claims. The swing in F1 (0.48 → 0.11) and CQ pass rate (52% → 9.5%) suggests randomness dominates performance.
- Recommended for rigor: run additional seeds (≥5), fix or log a pseudo-random seed if the backend allows, and report mean ± std for both F1 and CQ pass rate. Keep temperature low (≤0.2) for reproducibility, or justify higher temperatures with multiple runs.
- Document exact config, model version, and API parameters alongside metrics; include the full `pred.ttl` snapshots per run for auditability.
