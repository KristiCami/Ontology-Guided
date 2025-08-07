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
│   ├── ontology_builder.py  # Ενοποίηση Turtle σε αρχείο OWL/TTL
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
   - `--spacy-model`: ορίζει ποιο spaCy μοντέλο θα χρησιμοποιηθεί για τμηματοποίηση προτάσεων.
   - `--inference`: επιλέγει τρόπο συμπερασμού κατά την επικύρωση SHACL (`none`, `rdfs`, `owlrl`).

   Παράδειγμα με προσαρμοσμένες επιλογές:
   ```bash
   python3 scripts/main.py --inputs demo.txt --shapes shapes.ttl --spacy-model en --inference none
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
   Ανοίξτε τον browser στη διεύθυνση `http://localhost:8000` για να ανεβάσετε αρχεία ή κείμενο και να τρέξετε το pipeline μέσω web.

---

## 🔧 Εργαλεία
- **spaCy** για τμηματοποίηση προτάσεων
- **OpenAI API** για παραγωγή αρχικών τριπλετών
- **rdflib** και **OWLready2** για χειρισμό οντολογιών
- **pySHACL** για επικύρωση με κανόνες SHACL

---

## 📝 Άδεια Χρήσης
Διανέμεται υπό την άδεια MIT.
