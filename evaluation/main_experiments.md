# Main Experiments (ATM Domain)

Offline evaluation for the ATM requirements split now follows the camera-ready table format described in Table~\ref{tab:main-exps-offline} (see `evaluation/offline_tables.tex`). Key observations from the cached runs are:

- **E1 – LLM-only**: macro precision/recall/F1 of 0.985/1.000/0.992 with no SHACL validation and a 57.1% CQ pass rate.
- **E2 – Symbolic-only**: precision drops to 0.305 while recall remains at 1.000 (F1 = 0.468); CQ coverage stays flat because validation is disabled.
- **E3 – Ours (no-repair)**: identical precision/recall/F1 to E1 but with SHACL enabled (0 violations before/after) and reasoning coherence maintained.
- **E4 – Ours (full)**: matches E3 metrics because cached generations already conform, yielding zero repair iterations.
- **E5/E6** remain pending until healthcare/automotive caches and CQ-triggering snippets are populated.

The raw CSV exports that feed the LaTeX table remain available in `evaluation/table1.csv`–`evaluation/table4.csv` for reproducibility.
