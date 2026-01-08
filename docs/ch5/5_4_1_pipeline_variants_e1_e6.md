# 5.4.1 Pipeline Variants (E1–E6)

Οι βασικές παραλλαγές του OG–NSD ορίζονται ως πειράματα E1–E6 και αντιστοιχούν σε διαφορετικές διαμορφώσεις του pipeline. Η υλοποίηση τους είναι explicit στο αποθετήριο μέσω ειδικών scripts (`scripts/run_e1_llm_only.py`, `scripts/run_e2_symbolic_only.py`, `scripts/run_atm_examples.py`, `scripts/run_e4_iterative.py`, `scripts/run_e5_cross_domain.py`, `scripts/run_e6_cq_oriented.py`) και αντίστοιχων JSON configs στον φάκελο `configs/`. Κάθε experiment αντιστοιχεί σε σαφή αλλαγή στη ροή εκτέλεσης, επιτρέποντας συγκρίσεις “apples-to-apples”.

**E1 – LLM-only.** Το pipeline εκτελεί μόνο το drafting step. Δεν χρησιμοποιούνται SHACL, reasoner ή repair loop. Το αποτέλεσμα είναι το raw ontology (π.χ. `pred.ttl`) που προκύπτει απευθείας από τις απαιτήσεις. Αυτό λειτουργεί ως neural baseline και δείχνει το επίπεδο lexical drift και structural ασυνέπειας χωρίς symbolic καθοδήγηση.

**E2 – Symbolic-only.** Το pipeline αποφεύγει LLM drafting και βασίζεται σε deterministic heuristic rules. Εδώ το `og_nsd/llm.py` λειτουργεί σε heuristic mode, παράγοντας axioms χωρίς νευρωνική υποστήριξη. Ο SHACL/Reasoner έλεγχος παραμένει ενεργός, άρα το αποτέλεσμα είναι υψηλής ακρίβειας αλλά χαμηλής κάλυψης. Αυτό είναι το symbolic baseline.

**E3 – Ours (no-repair).** Πρόκειται για ontology-aware drafting, αλλά χωρίς τον επαναληπτικό repair loop. Το αποτέλεσμα είναι ένα μόνο validated draft, χρήσιμο για να απομονωθεί η συμβολή του grounding χωρίς iterative feedback. Η εκτέλεση γίνεται μέσω `scripts/run_atm_examples.py` με config `configs/atm_ontology_aware.json`.

**E4 – Ours (full).** Εδώ ενεργοποιείται πλήρως ο repair loop, με SHACL + reasoning feedback και πολλαπλές iterations. Είναι το “κύριο” experiment όπου αναμένουμε μείωση violations και βελτίωση F1. Αυτό το setup αξιοποιεί το `configs/atm_e4_iterative.json`.

**E5 – Cross-domain.** Το pipeline τρέχει σε πολλαπλά domains (π.χ. ATM, health). Το config `configs/e5_cross_domain.json` περιλαμβάνει blocks με διαφορετικά requirements/base/shapes/CQs. Αυτό δείχνει τη δυνατότητα plug-and-play προσαρμογής του συστήματος.

**E6 – CQ-oriented.** Επικεντρώνεται στις Competency Questions, καταγράφοντας CQ pass rates ανά iteration. Έτσι, αξιολογείται η επίδραση του repair loop όχι μόνο σε SHACL compliance αλλά και στην επιχειρησιακή επάρκεια.

Η ύπαρξη αυτών των παραλλαγών είναι βασική για ακαδημαϊκή τεκμηρίωση, διότι επιτρέπει τον έλεγχο υποθέσεων: τι προσφέρει το LLM, τι προσφέρει η symbolic επικύρωση, τι προσφέρει ο repair loop, και κατά πόσο το σύστημα γενικεύει σε νέα domains. Τα artefacts των runs αποθηκεύονται στο `runs/` και χρησιμοποιούνται για στατιστική σύγκριση.
