# 🧠 Σύνταξη Οντολογιών από Απαιτήσεις Λογισμικού

Το αποθετήριο αυτό υλοποιεί μια μικτή **νευρο-συμβολική** διαδικασία που μετατρέπει φυσικές γλώσσες απαιτήσεων σε οντολογίες OWL.  
Ο συνδυασμός της υπολογιστικής ισχύος μεγάλων γλωσσικών μοντέλων (LLMs) με κανόνες SHACL επιτρέπει την αυτόματη δημιουργία, επικύρωση και διόρθωση τριπλετών.

Demo Url: https://kristitsami.pythonanywhere.com/

> Αναπτύχθηκε στο πλαίσιο μεταπτυχιακής διπλωματικής εργασίας στην Τεχνητή Νοημοσύνη.

---

## 📂 Δομή Αρχείων

```
Ontology-Guided/
├── ontology_guided/         # Python package με τον βασικό κώδικα
│   ├── __init__.py
│   ├── data_loader.py       # Φόρτωση και προεπεξεργασία κειμένων
│   ├── llm_interface.py     # Επικοινωνία με το LLM (π.χ. GPT-4)
│   ├── ontology_builder.py  # Ενοποίηση Turtle σε αρχείο OWL/TTL (υποστηρίζει `lexical_namespace` για συνώνυμα)
│   ├── repair_loop.py       # Επαναληπτική επιδιόρθωση με LLM
│   └── validator.py         # SHACL έλεγχος ορθότητας
├── scripts/                 # Εκτελέσιμα βοηθητικά scripts
│   ├── main.py              # Ενοποιημένο pipeline
│   ├── generate_examples.py # Δημιουργία παραδειγμάτων
│   └── web_app.py           # Απλή web διεπαφή
├── tests/                   # Μονάδες ελέγχου
├── demo.txt                 # Δείγμα απαιτήσεων
├── shapes.ttl               # Κανόνες SHACL
├── requirements.txt         # Εξαρτήσεις Python
└── README.md
```

---
## 📑 Πρωτόκολλο Διαχωρισμού & Προτρεπτικών

Το αποθετήριο εφαρμόζει αυστηρό διαχωρισμό **dev/test** ώστε να αποφεύγεται η
διαρροή πληροφορίας:

1. **Διαχωρισμός προτάσεων** – Τα αρχεία `splits/dev.txt` και `splits/test.txt`
   περιέχουν ασύνδετα `sentence_id`. Η συνάρτηση
   `load_dev_examples` φορτώνει αποκλειστικά τις προτάσεις του dev split και
   ελέγχει για ελλείποντα IDs, επιστρέφοντας έτοιμα ζεύγη πρόταση→OWL για
   few‑shot παραδείγματα【F:scripts/main.py†L33-L84】.
2. **Έλεγχος επικάλυψης** – Κατά την εκτέλεση του pipeline, γίνεται επαλήθευση
   ότι τα test IDs δεν συμπίπτουν με τα dev examples ούτε με τα επιτρεπόμενα
   `allowed_ids`. Οποιαδήποτε επικάλυψη προκαλεί άμεσο σφάλμα ώστε τα prompts να
   μην περιέχουν test δεδομένα【F:scripts/main.py†L149-L164】.
3. **Κατασκευή prompt** – Η `LLMInterface.build_prompt` προσθέτει σταθερές
   οδηγίες, διαφημίζει το επιτρεπόμενο λεξιλόγιο και εισάγει 3–6 dev
   παραδείγματα πριν από την πρόταση του τεστ, διασφαλίζοντας αναπαραγωγιμότητα
   και χρήση αποκλειστικά εγκεκριμένων όρων【F:ontology_guided/llm_interface.py†L30-L102】.
4. **Αξιολόγηση με provenance** – Οι συναρτήσεις αξιολόγησης
   `filter_by_ids` και `compare_metrics` φιλτράρουν το χρυσό TTL με βάση την
   προέλευση κάθε τριπλέτας, ώστε να συγκρίνονται μόνο οι δομές που σχετίζονται
   με τα test `sentence_id` χωρίς να διασπάται το ίδιο το χρυσό αρχείο
   οντολογίας【F:evaluation/compare_metrics.py†L24-L56】.
5. **Επιδιόρθωση χωρίς διαρροή** – Όταν ο SHACL validator εντοπίσει παραβιάσεις,
   η `synthesize_repair_prompts` δημιουργεί προτροπές με τοπικό
   αποσπασματικό γράφημα και κανονικοποιημένη περιγραφή του σφάλματος· το LLM
   προτείνει μόνο τριπλέτες διόρθωσης χρησιμοποιώντας το διαθέσιμο λεξιλόγιο,
   χωρίς ποτέ να βλέπει τις χρυσές απαντήσεις των test προτάσεων【F:ontology_guided/repair_loop.py†L136-L205】.

Με αυτά τα βήματα, οι προτροπές που στέλνονται στο LLM χρησιμοποιούν μόνο
παραδείγματα από το dev split και το επιτρεπόμενο λεξιλόγιο, ενώ η αξιολόγηση
γίνεται αποκλειστικά σε δεδομένα test.

---
## 🔄 OG‑NSD Pipeline

![OG‑NSD Pipeline](docs/pipeline.svg)

## ♻️ Repair Loop

The diagram below zooms into the repair cycle from detecting a real violation to producing the corrected axioms diff.

![Repair Loop](docs/repair_loop_zoom.svg)

### Termination & Guarantees

Ο βρόχος διακόπτεται είτε όταν επιτευχθούν `kmax` επαναλήψεις είτε μόλις η SHACL επικύρωση ολοκληρωθεί χωρίς παραβιάσεις.
Η τιμή `conforms=True` σηματοδοτεί πλήρη συμμόρφωση με τους κανόνες SHACL· εφόσον η επιλογή `reason` είναι ενεργή, διασφαλίζεται επιπλέον συνεκτικότητα μέσω λογικού συμπερασμού.
Η προτροπή ζητά ελάχιστες διορθώσεις και το σύστημα υπολογίζει το diff μεταξύ των αρχικών και των διορθωμένων τριπλετών για να μετρήσει την επίδραση κάθε επανάληψης.

## 🚀 Γρήγορη Εκκίνηση

1. **Εγκατάσταση βιβλιοθηκών**
   ```bash
   python3 -m pip install -r requirements.txt
   python3 -m spacy download en_core_web_sm
   ```

2. **Ρύθμιση κλειδιού API**
   Δημιουργήστε αρχείο `.env` με την μεταβλητή `OPENAI_API_KEY` για να μπορεί το LLM να κληθεί.

3. **Εκτέλεση ενοποιημένου pipeline**
   ```bash
   python3 scripts/main.py --inputs demo.txt --shapes shapes.ttl --reason --repair
   ```
   Το script διαβάζει τις απαιτήσεις, παράγει τα OWL triples, τρέχει τον
   reasoner και τον έλεγχο SHACL, και αν χρειαστεί εκτελεί αυτόματο βρόχο διόρθωσης.
   Ο φάκελος `results/` δημιουργείται αυτόματα αν δεν υπάρχει.

   Προαιρετικές επιλογές:
   - `--base-iri`: αλλάζει το βασικό IRI της παραγόμενης οντολογίας.
   - `--ontologies`: λίστα από επιπλέον αρχεία TTL που θα φορτωθούν.
   - `--ontology-dir`: φόρτωση όλων των οντολογιών από φάκελο.
   - `--rbo`, `--lexical`: συμπερίληψη των προ-ενσωματωμένων οντολογιών.
   - `--spacy-model`: ορίζει ποιο spaCy μοντέλο θα χρησιμοποιηθεί για τμηματοποίηση προτάσεων.
   - `--inference`: επιλέγει τρόπο συμπερασμού κατά την επικύρωση SHACL (`none`, `rdfs`, `owlrl`).
   - `--model`: επιλέγει ποιο LLM θα κληθεί (προεπιλογή: `gpt-4`).
   - `--kmax`: μέγιστος αριθμός επαναλήψεων στον βρόχο διόρθωσης (προεπιλογή: `5`).
   - `--no-terms`: δεν παρέχονται διαθέσιμοι όροι της οντολογίας στο LLM (προεπιλογή: παρέχονται).
   - `--no-shacl`: απενεργοποίηση του ελέγχου SHACL και του βρόχου διόρθωσης (προεπιλογή: ενεργοποιημένα).

   Η προτροπή προς το LLM πλέον περιλαμβάνει οδηγίες για το base IRI και το prefix, ώστε τα παραγόμενα IRIs να είναι συνεπή. Παράδειγμα:

   ```python
   from scripts.main import PROMPT_TEMPLATE

   print(
       PROMPT_TEMPLATE.format(
           sentence="The ATM authenticates cards.",
           base="http://example.com/atm#",
           prefix="atm",
       )
   )
   ```

   Παράγει απόσπασμα τύπου:

   ```turtle
   @prefix atm: <http://example.com/atm#> .
   atm:Authentication a owl:Class .
   ```

   Παράδειγμα με προσαρμοσμένες επιλογές:
   ```bash
   python3 scripts/main.py --inputs demo.txt --shapes shapes.ttl --ontology-dir ontologies --rbo --lexical --base-iri http://example.com/atm#
   ```

   Η προαιρετική σημαία `--reason` τρέχει τον ενσωματωμένο reasoner της OWLready2 πριν τον έλεγχο SHACL.
   Για να λειτουργήσει, απαιτείται εγκατεστημένο Java (π.χ. OpenJDK).

4. **Αυτόματη δημιουργία παραδειγμάτων**
   ```bash
   python3 scripts/generate_examples.py
   ```
   Παράγει τα αρχεία `results/combined.ttl` και `results/combined.owl` από το `demo.txt`.
5. **Χειροκίνητη εκτέλεση επιμέρους βημάτων** (προαιρετικά)
   ```bash
   python3 ontology_guided/ontology_builder.py    # συγχώνευση σε combined.ttl/owl
   python3 ontology_guided/validator.py --data results/combined.ttl --shapes shapes.ttl
   python3 ontology_guided/repair_loop.py         # εφόσον υπάρχουν παραβιάσεις
   ```
6. **Εκτέλεση tests**
   ```bash
   pytest
   ```
   Τα tests βρίσκονται στον φάκελο `tests/` και τρέχουν χωρίς πραγματική κλήση στο OpenAI API.

7. **Εκκίνηση Web διεπαφής**
   ```bash
   python3 scripts/web_app.py
   ```
   Ανοίξτε τον browser στη διεύθυνση `http://localhost:8000` για να ανεβάσετε κείμενο, αρχεία απαιτήσεων, πολλαπλά αρχεία οντολογιών, προσαρμοσμένο base IRI και (προαιρετικά) αρχείο κανόνων SHACL.

   Στη φόρμα υπάρχουν επίσης τα checkboxes:
   - **Repair**: ενεργοποιεί τον αυτόματο βρόχο διόρθωσης παραβιάσεων SHACL.
   - **Reason**: τρέχει τον reasoner της OWLready2 πριν τον έλεγχο SHACL.

   Μετά την εκτέλεση εμφανίζονται οι προ-επεξεργασμένες προτάσεις, τα αποσπάσματα OWL που παράγονται από το LLM, η έξοδος του reasoner και η αναφορά SHACL (συμμόρφωση και λεπτομέρειες), μαζί με την τελική οντολογία.

   Τα αρχεία που ανεβάζονται διαγράφονται αυτόματα μετά την ολοκλήρωση κάθε αιτήματος.

---

## 📦 Προ-ενσωματωμένες Οντολογίες

- **ontologies/rbo.ttl**: ορίζει βασικές κλάσεις για Requirements, Actions και Actors, μαζί με τις ιδιότητες `requiresAction` και `performedBy`.
- **ontologies/lexical.ttl**: περιέχει λεξική δομή με κλάσεις `Word`, `Noun` και σχέσεις `synonym`, `antonym` μεταξύ λέξεων.
  Ο `OntologyBuilder` δέχεται προαιρετικό `lexical_namespace` ώστε να καθοριστεί το namespace της ιδιότητας `synonym`.

## 🏥 Εναλλαγή Τομέων

Η ίδια διαδικασία μπορεί να στραφεί σε διαφορετικό domain αλλάζοντας απλώς
τις απαιτήσεις, τα SHACL shapes και τις (προαιρετικές) οντολογίες. Για
παράδειγμα, το παρακάτω command εκτελεί το pipeline σε σενάριο υγείας χωρίς
καμία επανεκπαίδευση του μοντέλου:

```bash
python3 scripts/main.py \
    --inputs evaluation/healthcare_requirements.txt \
    --shapes evaluation/healthcare_shapes.ttl \
    --ontology-dir ontologies/healthcare \
    --base-iri http://example.com/healthcare#
```

Εναλλακτικά, περάστε συγκεκριμένα αρχεία με `--ontologies`.
Το αποτέλεσμα είναι μια οντολογία με κανόνες για γιατρούς, ασθενείς και
ιατρικές παρατηρήσεις.

## 📊 Αξιολόγηση

### Δομή Δεδομένων

Η διαδικασία αξιολόγησης βασίζεται στην ακόλουθη διάταξη φακέλων:

```
data/requirements.jsonl   # όλες οι απαιτήσεις με πεδία sentence_id
gold/atm_gold.ttl         # χρυσή οντολογία (ή άλλα αρχεία στο gold/)
splits/dev.txt            # sentence_id για παραδείγματα few-shot
splits/test.txt           # sentence_id που αξιολογούνται
```

Τα `sentence_id` στο `requirements.jsonl` αντιστοιχούν στα ίδια IDs που
χρησιμοποιούνται στο χρυσό αρχείο και στα αρχεία split.  Οι προτάσεις του
`dev.txt` αξιοποιούνται ως παραδείγματα στο prompt και δεν πρέπει να
εμφανίζονται στο `test.txt`.

### Dev παραδείγματα και Retrieval

Το `scripts/main.py` φορτώνει αυτόματα τις προτάσεις του dev split για
few-shot prompts.  Με την επιλογή `--use-retrieval` ο επιλογέας
παραδειγμάτων αναζητά τα πιο όμοια dev παραδείγματα από ένα JSON αρχείο
(`--dev-pool`) και καταγράφει τα IDs στο `--prompt-log` ώστε η επιλογή να
παγώνει και να αναπαράγεται σε μελλοντικά runs.

### Αξιολόγηση μόνο στο test split

Κατά την αξιολόγηση χρησιμοποιούνται αποκλειστικά οι προτάσεις από το
`splits/test.txt`.  Οι επιλογές CLI `--split` (φιλτράρισμα εισόδων) και
`--dev` (φόρτωση dev παραδειγμάτων) ελέγχουν ότι δεν υπάρχει επικάλυψη
μεταξύ dev και test IDs.

#### Παραδείγματα εντολών

```bash
# Εκτέλεση pipeline μόνο σε test IDs με παγωμένο retrieval
python3 scripts/main.py --inputs data/requirements.jsonl --shapes shapes.ttl \
    --split splits/test.txt --use-retrieval --dev-pool data/dev_examples.json \
    --retrieve-k 4 --prompt-log results/prompts.log
```

```bash
# Υπολογισμός μετρικών με dev παραδείγματα και test split
python3 evaluation/compare_metrics.py data/requirements.jsonl gold/atm_gold.ttl \
    --shapes shapes.ttl --split splits/test.txt --dev splits/dev.txt
```

```bash
# Benchmark με retrieval και test split
python3 evaluation/run_benchmark.py --pairs "data/requirements.jsonl:gold/atm_gold.ttl" \
    --splits splits/test.txt --use-retrieval --dev-pool data/dev_examples.json \
    --prompt-log results/prompts.log
```

Μπορείτε να επιλέξετε στρατηγική αντιστοίχισης αξιωμάτων με την επιλογή
`--match-mode` (`syntactic` ή `semantic`), με προεπιλογή το `syntactic`.

Το script υπολογίζει **precision** και **recall** και αποθηκεύει τις
μετρικές στο `results/metrics.txt`.

### Μαζική αξιολόγηση

Για την αναπαραγωγή πινάκων αξιολόγησης σε διαφορετικές ρυθμίσεις, υπάρχει το script:

```bash
python3 evaluation/run_benchmark.py --pairs "data/requirements.jsonl:gold/atm_gold.ttl" \
    --splits splits/test.txt --repeats 1
```

Το script εκτελεί το pipeline με όλους τους συνδυασμούς των σημαιών `use_terms` και `validate`,
αποθηκεύοντας τα αποτελέσματα σε πίνακες `table_<N>.csv` και `table_<N>.md` στον φάκελο `evaluation`.

Το script φορτώνει αυτόματα παραδείγματα από το dev split (`splits/dev.txt`).

Η προαιρετική σημαία `--normalize-base` κανονικοποιεί τα base IRIs πριν τη σύγκριση,
μειώνοντας ψευδείς αποκλίσεις όταν οι ίδιες τριπλέτες χρησιμοποιούν διαφορετικά base.

Οι οντολογίες ανά domain καθορίζονται εύκολα μέσω `--ontologies` για
μεμονωμένα αρχεία ή `--ontology-dir` για φόρτωση όλων των `.ttl` από έναν
φάκελο. Το χρυσό TBox `evaluation/atm_gold.ttl` περιλαμβάνεται εξ ορισμού, αλλά
όταν χρησιμοποιείται `--ontology-dir` πρέπει να προστίθεται ρητά. Παράδειγμα:

```bash
python3 evaluation/run_benchmark.py \
    --pairs "data/requirements.jsonl:gold/atm_gold.ttl" \
    --ontologies gold/atm_gold.ttl \
    --ontology-dir ontologies \
    --splits splits/test.txt \
    --repeats 1
```

Παράδειγμα με προσαρμοσμένη ρύθμιση που φορτώνει επιπλέον οντολογίες:

```bash
python -m evaluation.run_benchmark \
    --pairs "data/requirements.jsonl:gold/atm_gold.ttl" \
    --settings '[{"name":"table1","use_terms":true,"validate":true,"ontologies":["gold/atm_gold.ttl","ontologies/rbo.ttl","ontologies/lexical.ttl"]}]'
```

### Mini Evaluation Example

Για ένα μίνι παράδειγμα, χρησιμοποιήστε τα αρχεία στον φάκελο `evaluation` που ξεκινούν με `mini_`.
Τρέξτε:
```bash
python3 evaluation/compare_metrics.py evaluation/mini_requirements.jsonl evaluation/mini_gold.ttl --shapes evaluation/mini_shapes.ttl --base-iri http://example.com/mini#
```
Αναμένονται μετρικές F1 περίπου 0.14 → 0.27 → 0.53 για τα αρχεία `mini_pred_iter0.ttl`, `mini_pred_iter1.ttl` και `mini_pred_iter2.ttl`.

### Competency Questions

Οι ερωτήσεις ικανότητας (Competency Questions) μετρούν κατά πόσο η παραγόμενη
οντολογία μπορεί να απαντήσει σε βασικά ερωτήματα του domain.  Κάθε ερώτηση
γράφεται ως SPARQL `ASK` query και αξιολογείται ως επιτυχία όταν το ερώτημα
επιστρέφει `True`.

* **Προετοιμασία**: αποθηκεύστε τα queries σε αρχείο `.rq`, χωρισμένα με κενές
  γραμμές.  Παράδειγμα τεσσάρων ερωτήσεων για δύο domains:

```sparql
PREFIX atm: <http://lod.csd.auth.gr/atm/atm.ttl#>

# Every Withdrawal has a non-negative amount
ASK {
  FILTER NOT EXISTS {
    ?w a atm:Withdrawal ;
       atm:amount ?amt .
    FILTER (?amt < 0)
  }
}

# ATMs accept cash cards
ASK {
  atm:ATM atm:accepts ?card .
}

PREFIX hc: <http://example.com/healthcare#>

# Every Observation is performed by a Doctor
ASK {
  FILTER NOT EXISTS {
    ?o a hc:Observation ;
       hc:performedBy ?x .
    FILTER NOT EXISTS { ?x a hc:Doctor }
  }
}

# Observations concern Patients
ASK {
  ?o a hc:Observation ;
     hc:onPatient ?p .
  ?p a hc:Patient .
}
```

* **Εκτέλεση**: τρέξτε το script `evaluation/competency_questions.py` δίνοντας
  το αρχείο οντολογίας και το αρχείο ερωτήσεων:

```bash
python3 - <<'PY'
from evaluation.competency_questions import evaluate_cqs
stats = evaluate_cqs("results/combined.ttl", "evaluation/atm_cqs.rq")
print(stats)
PY
```

Παράδειγμα ποσοστών επιτυχίας σε τέσσερις ερωτήσεις:

| Baseline          | Pass rate |
|-------------------|-----------|
| LLM-only          | 25%       |
| Symbolic-only     | 50%       |
| Ours (no-repair)  | 75%       |
| Ours (full)       | 100%      |

## 🔧 Εργαλεία
- **spaCy** για τμηματοποίηση προτάσεων
- **OpenAI API** για παραγωγή αρχικών τριπλετών
- **rdflib** και **OWLready2** για χειρισμό οντολογιών
- **pySHACL** για επικύρωση με κανόνες SHACL

---

## 📝 Άδεια Χρήσης
Διανέμεται υπό την άδεια MIT.
