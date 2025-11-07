# Οδηγός Παρουσίασης Πειραμάτων

Ο παρών οδηγός περιγράφει βήμα προς βήμα πώς να εκτελέσετε τα κύρια πειράματα (E1–E6), τις βασικές αφαιρέσεις (A1–A4) και πώς να μετασχηματίσετε τα αποτελέσματα σε πίνακες και διαγράμματα για παρουσίαση.

## 1. Προετοιμασία περιβάλλοντος
1. Δημιουργήστε και ενεργοποιήστε virtualenv (προαιρετικά).
2. Εγκαταστήστε τις εξαρτήσεις:
   ```bash
   pip install -r requirements.txt
   ```
   
3. Βεβαιωθείτε ότι ο φάκελος `results/` υπάρχει (δημιουργείται αυτόματα από τα scripts).

## 2. Εκτέλεση κύριων πειραμάτων (Πίνακας Α)
Ο αυτοματοποιημένος δρομέας `evaluation/run_benchmark.py` υποστηρίζει παρτίδες πειραμάτων και εξάγει CSV/Markdown πίνακες. Η παρακάτω εντολή εκτελεί τις διαμορφώσεις E1–E4 πάνω στο split ATM χρησιμοποιώντας τις αποθηκευμένες αποκρίσεις (backend `cache`).

```bash
python -m evaluation.run_benchmark \
  --pairs "evaluation/atm_requirements.jsonl:gold/atm_gold.ttl" \
  --settings-file evaluation/presentation_main.json \
  --cqs evaluation/atm_cqs.rq \
  --base-iri http://lod.csd.auth.gr/atm/atm.ttl# \
  --repeats 1
```

> **PowerShell σημείωση:** Χρησιμοποιήστε το backtick `` ` `` ως χαρακτήρα συνέχειας γραμμής ή εκτελέστε την εντολή σε μία γραμμή. Το αντίστοιχο PowerShell snippet είναι:

```powershell
python -m evaluation.run_benchmark `
  --pairs "evaluation/atm_requirements.jsonl:gold/atm_gold.ttl" `
  --settings-file evaluation/presentation_main.json `
  --cqs evaluation/atm_cqs.rq `
  --base-iri "http://lod.csd.auth.gr/atm/atm.ttl#" `
  --repeats 1
```

Αν επικολλήσετε τις επιλογές χωρίς χαρακτήρα συνέχειας, το PowerShell θα προσπαθήσει να εκτελέσει κάθε γραμμή ξεχωριστά (π.χ. `--pairs ...`) με αποτέλεσμα τα σφάλματα `Missing expression after unary operator '--'` που φαίνονται παραπάνω.

- Το αρχείο `evaluation/presentation_main.json` αντιστοιχίζει τα πειράματα E1–E4 με τις σημαίες `use_terms`, `validate`, `repair`, `reason` και το backend `cache`, ώστε να παραχθούν οι ίδιες διαμορφώσεις που περιγράφονται στην περίληψη των πειραμάτων.【F:evaluation/presentation_main.json†L1-L27】【F:evaluation/run_benchmark.py†L119-L146】【F:evaluation/run_benchmark.py†L246-L347】
- Τα αποτελέσματα γράφονται ως `evaluation/E*_*.csv` και `evaluation/E*_*.md`, τα οποία μπορούν να μετατραπούν σε LaTeX με τον κώδικα της ενότητας 4.
- Για E5 (Cross-domain) επαναλάβετε την ίδια εντολή με πρόσθετα ζεύγη στο `--pairs`, π.χ. `evaluation/healthcare_requirements.txt:gold/healthcare_gold.ttl:evaluation/healthcare_shapes.ttl` και `requirements_auto.jsonl:gold/auto_gold.ttl:shapes_auto.ttl`, εφόσον είναι διαθέσιμα.
- Για E6 (CQ-oriented) κρατήστε τη ρύθμιση E4 και εξαναγκάστε επισκευές με `--repeats` > 1 ή με ένα σύνολο απαιτήσεων που περιέχει γνωστές παραβιάσεις ώστε να παραχθούν πολλαπλές επαναλήψεις για την γραφική παράσταση CQ.

### Αναμενόμενες εξαγωγές
Με χρήση των cache αποτελεσμάτων της ATM καταγράφονται τα metrics που συνοψίζονται στην έτοιμη LaTeX εκδοχή (`evaluation/offline_tables.tex`). Χρησιμοποιήστε τα αρχεία CSV για να επιβεβαιώσετε ότι οι μακρο-μετρικές (P/R/F1), ο αριθμός παραβιάσεων SHACL και το ποσοστό επιτυχίας των CQs συμφωνούν με τις περιγραφές του Πίνακα Α.【F:evaluation/offline_tables.tex†L1-L33】

## 3. Εκτέλεση αφαιρέσεων & ευαισθησίας (Πίνακας Β)
Οι αφαιρέσεις A1–A4 γίνονται τροποποιώντας σταδιακά τη βασική ρύθμιση E4:

| ID | Αλλαγή | Παράμετροι CLI |
|----|--------|----------------|
| A1 | Χωρίς weighted SHACL | Προσθέστε `--settings '[{"name":"A1_no_wshacl","use_terms":true,"validate":true,"repair":true,"reason":true,"backend":"cache","kmax":5,"weighted":false}]'` και επεκτείνετε το σχήμα ώστε να μην διαχωρίζει σοβαρότητες (αφαίρεση προσαρμοσμένων βαρών από τα SHACL αρχεία). |
| A2 | Χωρίς Patch Calculus | Θέστε `--settings '[{"name":"A2_no_patch","use_terms":true,"validate":true,"repair":true,"reason":true,"backend":"cache","kmax":5,"typed_patches":false}]'` και επεξεργαστείτε το loop ώστε να δέχεται ελεύθερο Turtle (βλ. `ontology_guided/repair_loop.py`). |
| A3 | Χωρίς admissibility | Στο JSON ρύθμισης θέστε `"admissibility": false` για να παρακαμφθεί ο προέλεγχος ασφαλείας πριν την οριστική ενημέρωση του γραφήματος. |
| A4 | Χωρίς ontology-aware prompting | Θέστε `"use_terms": false` στην πλήρη ρύθμιση. |

Ο δρομέας CLI δέχεται οποιαδήποτε λίστα λεξικών ως `--settings` ή `--settings-file`, και μεταβιβάζει τα πεδία απευθείας στη `run_pipeline`, επιτρέποντας να ανακτήσετε τις τιμές των μετρικών που αντιστοιχούν στις γραμμές του Πίνακα Β.【F:evaluation/run_benchmark.py†L263-L347】【F:scripts/main.py†L73-L170】【F:ontology_guided/repair_loop.py†L1-L120】

> **Σημείωση:** Τα πεδία `weighted`, `typed_patches` και `admissibility` αντιστοιχούν σε λογική που βρίσκεται στο `RepairLoop`/`validator`. Ρυθμίστε τα ανάλογα με τις τροποποιήσεις που έχετε εφαρμόσει ώστε να ενεργοποιούνται/απενεργοποιούνται τα σχετικά μπλοκ κώδικα.

## 4. Μετατροπή CSV σε LaTeX & Σχεδιασμός πινάκων
Χρησιμοποιήστε το ακόλουθο script Python για να μετατρέψετε τα παραχθέντα CSV σε LaTeX πίνακες (όπως ο Πίνακας Α) και να ενημερώσετε την παρουσίαση:

```python
import pandas as pd
from pathlib import Path

# Παράδειγμα για E1–E4
rows = []
for name in ["E1_llm_only", "E2_symbolic_only", "E3_no_repair", "E4_full_loop"]:
    df = pd.read_csv(Path("evaluation") / f"{name}.csv")
    row = df.iloc[0].to_dict()
    rows.append({
        "ID": name.split("_")[0].upper(),
        "Precision": f"{row['precision']:.3f}",
        "Recall": f"{row['recall']:.3f}",
        "F1": f"{row['f1']:.3f}",
        "Violations": f"{int(row['initial_violations'])}→{int(row['final_violations'])}",
        "CQ%": f"{row['cq_pass_rate']*100:.1f}%",
        "Iterations": f"{row['iterations']:.1f}"
    })

table = pd.DataFrame(rows)
print(table.to_latex(index=False, escape=False))
```

Ο κώδικας χρησιμοποιεί την ίδια δομή που εφαρμόζεται στον exporter του benchmark (`write_csv`, `write_markdown`) και σας επιτρέπει να δημιουργήσετε προσαρμοσμένα πεδία (π.χ. `Violations` ως συμβολισμό `pre→post`).【F:evaluation/run_benchmark.py†L214-L233】

## 5. Οπτικοποίηση δυναμικής επισκευής
Για να παρακολουθήσετε την εξέλιξη των παραβιάσεων και των CQ ποσοστών ανά επανάληψη, αναλύστε το JSON πεδίο `per_iteration` από το αντικείμενο `aggregate_repair_efficiency`:

```python
import json
from evaluation.repair_efficiency import aggregate_repair_efficiency

with open("evaluation/E4_full_loop.csv") as f:
    # Κάθε γραμμή περιέχει ήδη συνοπτικές μετρικές, αλλά τα λεπτομερή logs βρίσκονται στο directory `results/`
    pass
```

Για λεπτομερείς πληροφορίες εκτελέστε τον pipeline με `--prompt-log` ώστε να αποθηκεύσετε τα ids των παραδειγμάτων που χρησιμοποιήθηκαν, και δημιουργήστε stacked bar/line plots χρησιμοποιώντας `matplotlib` ή `seaborn` με βάση το output του `aggregate_repair_efficiency` που παρέχει μετρήσεις ανά iteration.【F:evaluation/repair_efficiency.py†L1-L200】

## 6. Αφήγηση παρουσίασης
Κατά την παρουσίαση, χρησιμοποιήστε το ακόλουθο αφήγημα:

1. **E1 – LLM-only:** Εκτέλεση χωρίς SHACL/Reasoner για να καταδειχθεί η απουσία συμβολικών ελέγχων και η εμφάνιση λανθασμένων αξιωμάτων. Παρουσιάστε Precision/Recall/F1 και επισημάνετε ότι δεν γίνεται παρακολούθηση παραβιάσεων.【F:evaluation/offline_tables.tex†L8-L14】
2. **E2 – Symbolic-only:** Ενεργοποιήστε μόνο κανόνες/ευθυγραμμίσεις (μέσω cache) και δείξτε το trade-off υψηλής ακρίβειας αλλά χαμηλής κάλυψης.【F:evaluation/offline_tables.tex†L15-L18】
3. **E3 – Ours (no-repair):** Τονίστε ότι ακόμη και με μία διέλευση, ο συνδυασμός LLM + SHACL + Reasoner παρέχει συνέπεια και μηδενικές παραβιάσεις, αλλά στερείται του βρόχου διορθώσεων.【F:evaluation/offline_tables.tex†L18-L21】
4. **E4 – Ours (full):** Περιγράψτε τον πλήρη CEGIR βρόχο με Patch Calculus και admissibility, ο οποίος εξαλείφει παραβιάσεις και συγκλίνει γρήγορα.【F:evaluation/offline_tables.tex†L21-L24】
5. **Επεκτάσεις (E5/E6):** Επισημάνετε ότι οι μελλοντικές εκτελέσεις σε Health/Auto domains και οι CQ τροχιές θα αναδείξουν τη γενίκευση και τη βελτίωση CQs.
6. **Αφαιρέσεις (A1–A4):** Συζητήστε τις επιπτώσεις από την απενεργοποίηση κάθε συνιστώσας, χρησιμοποιώντας το ραντάρ/heatmap που θα παραχθεί από τα δεδομένα της ενότητας 3.【F:evaluation/offline_tables.tex†L26-L43】

Με αυτά τα βήματα θα έχετε τόσο τα αριθμητικά αποτελέσματα όσο και το αφηγηματικό πλαίσιο για μία ολοκληρωμένη παρουσίαση.
