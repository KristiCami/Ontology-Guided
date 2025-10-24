# Τεχνική Αναφορά Χρυσού Πυρήνα ATM

## 1. Επισκόπηση
Ο φάκελος `gold/` φιλοξενεί τον σταθερό πυρήνα αξιολόγησης για το domain ATM. Ο πυρήνας αυτός διαχωρίζεται από την επιχειρησιακή οντολογία (`ontologies/atm_operational.ttl`) ώστε οι μετρήσεις να επικεντρώνονται σε έναν καθαρό TBox χωρίς stateful κλάσεις ή UI μηνύματα. Το σχήμα αποτελείται από:

- **Χρυσό TBox (`gold/atm_gold.ttl`)** με συμπαγές λεξιλόγιο ~15 κλάσεων και ιδιοτήτων που περιγράφουν ATM, τράπεζες, πελάτες, λογαριασμούς, κάρτες και τύπους συναλλαγών.【F:gold/atm_gold.ttl†L1-L94】
- **SHACL Shapes (`gold/shapes_atm.ttl`)** που εφαρμόζουν δομικούς περιορισμούς (μη αρνητικά ποσά, υποχρεωτικές συνδέσεις πελάτη/λογαριασμού, αντίστροφη ιδιοκτησία καρτών, όρια αναλήψεων, απαίτηση εξουσιοδότησης και εγκατάστασης ATM).【F:gold/shapes_atm.ttl†L1-L78】
- **Competency Questions (`evaluation/atm_cqs.rq`)** οι οποίες εκφράζουν ερωτήματα επάρκειας για ποσά αναλήψεων, ύπαρξη πελάτη/λογαριασμού και διαδικασία έκδοσης καρτών.【F:evaluation/atm_cqs.rq†L1-L30】

Αντίθετα, η επιχειρησιακή οντολογία (`ontologies/atm_operational.ttl`) παραμένει πλήρης με states, UI και πρόσθετους περιορισμούς για σκοπούς demo και προτροπών LLM.【F:ontologies/atm_operational.ttl†L1-L20】

## 2. Υλοποίηση Χρυσού TBox
Το `atm_gold.ttl` υλοποιεί το βασικό λεξιλόγιο με τις ακόλουθες σχεδιαστικές αποφάσεις:

- **Κλάσεις**: ATM, Bank, BankBranch, BankNetwork, Customer, Account, CashCard, Transaction και εξειδικεύσεις όπως Withdrawal, Deposit, BalanceInquiry, Authorization, Message και ATMComponent.【F:gold/atm_gold.ttl†L6-L24】
- **Αντικειμενικές ιδιότητες**: σχέσεις λειτουργίας/εγκατάστασης ATM (`operatedBy`, `installedAt`, `connectsToNetwork`, `hasComponent`) και επιχειρησιακές σχέσεις πελάτη-τραπεζών (`hasAccount`, `ownsCard`, `issuesCard`, `performedBy`, `onAccount`, `authorizedBy`, `communicatesMessage`). Οι domains/ranges δηλώνονται ρητά για να διευκολύνουν reasoning και tooling.【F:gold/atm_gold.ttl†L25-L52】
- **Ιδιότητες δεδομένων**: ποσοτικά/μεταδεδομένα πεδίο (`requestedAmount`, `dispensedAmount`, `serialNumber`, `bankCode`, `transactionTimestamp`, `locationDescription`, `componentName`) με τύπους `xsd:decimal`, `xsd:string` ή `xsd:dateTime`. Η διάκριση Withdrawal/Transaction διασφαλίζει ότι τα ποσά και τα χρονικά stamps είναι διαθέσιμα για έλεγχο συνεπειών.【F:gold/atm_gold.ttl†L53-L80】

Το TBox μένει σκόπιμα μικρό και χωρίς περίπλοκες αξιωματικές αλληλεπιδράσεις για να αποτελεί διαχειρίσιμο σημείο αναφοράς σε αυτόματους ελέγχους και LLM prompts.

## 3. Δομικοί Έλεγχοι SHACL
Το `shapes_atm.ttl` κωδικοποιεί τους υποχρεωτικούς περιορισμούς για instances:

- **WithdrawalShape**: απαιτεί πελάτη (`performedBy`), λογαριασμό (`onAccount`), μη αρνητικά αιτούμενα και διανεμηθέντα ποσά (`requestedAmount`, `dispensedAmount`).【F:gold/shapes_atm.ttl†L6-L26】
- **CashCardShape**: επιβάλλει serialNumber/bankCode και τουλάχιστον έναν κάτοχο μέσω αντίστροφου `ownsCard` (κάλυψη cardinality χωρίς επιπλέον τριπλές στο dataset).【F:gold/shapes_atm.ttl†L28-L40】
- **PerTransactionLimitShape**: οριοθετεί τις αναλήψεις στα 1000€ ανά συναλλαγή με `maxInclusive`.【F:gold/shapes_atm.ttl†L42-L50】
- **AuthorizationShape**: διασφαλίζει ότι κάθε συναλλαγή φέρει `authorizedBy` και `transactionTimestamp`.【F:gold/shapes_atm.ttl†L52-L60】
- **ATMInstallationShape**: απαιτεί σύνδεση ATM με τράπεζα και υποκατάστημα για αποτύπωση φυσικής εγκατάστασης.【F:gold/shapes_atm.ttl†L62-L70】

Οι shapes καλύπτουν τόσο schema-level (διασύνδεση οντοτήτων) όσο και data-level περιορισμούς (όρια ποσών), αποτρέποντας σιωπηρές αποκλίσεις όταν δημιουργούνται δείγματα δεδομένων από LLM.

## 4. Competency Questions
Το αρχείο `atm_cqs.rq` περιέχει τρία βασικά ASK queries:

1. Επιβεβαιώνει ότι κάθε Withdrawal έχει μη αρνητικό αιτούμενο ποσό, μέσω φίλτρου σε `requestedAmount`.
2. Ελέγχει ταυτόχρονα για ύπαρξη πελάτη και λογαριασμού, με `FILTER NOT EXISTS` μπλοκ ανά constraint ώστε ένα αποτυχημένο υπογράφημα να σηματοδοτεί ελλιπή μοντελοποίηση.
3. Βεβαιώνει ότι οι τράπεζες εκδίδουν κάρτες που δηλώνονται ρητά ως `CashCard`.

Η χρήση ASK κρατά το reporting δυαδικό (pass/fail) και επιτρέπει εύκολη σύγκριση ανάμεσα στο χρυσό TBox και σε παραγόμενα αποσπάσματα.【F:evaluation/atm_cqs.rq†L1-L30】

## 5. Ροή Μετρήσεων με Εστίαση σε Τμήματα
Για να αποφύγετε υψηλό κόστος από κλήσεις LLM, δουλέψτε με αποσπάσματα της οντολογίας και επαναχρησιμοποιήστε τα σε πολλαπλές μετρήσεις.

### 5.1 Δημιουργία αποσπάσματος
Χρησιμοποιήστε το `scripts/extract_ontology_segment.py` για να εξάγετε μόνο τις κλάσεις/ιδιότητες που σας ενδιαφέρουν. Ο αλγόριθμος μετατρέπει CURIEs σε IRIs, ακολουθεί `rdfs:subClassOf/domain/range` μέχρι το βάθος που ορίσατε και κρατά μόνο τα σχετικά triples στο νέο γράφημα.【F:scripts/extract_ontology_segment.py†L1-L108】

Παράδειγμα (αποσπασματικό TBox για αναλήψεις):
```bash
python scripts/extract_ontology_segment.py \
    --input gold/atm_gold.ttl \
    --terms atm:Withdrawal atm:Transaction atm:Customer \
    --depth 1 \
    --output tmp/gold_withdrawal.ttl
```

Επαναλάβετε με `ontologies/atm_operational.ttl` για να δημιουργήσετε συγκρίσιμο απόσπασμα από την επιχειρησιακή οντολογία. Το ίδιο snippet μπορεί να τροφοδοτήσει SHACL, SPARQL και LLM χωρίς να φορτώνετε όλο το αρχείο.

### 5.2 SHACL validation
Τρέξτε τον επικυρωτή πάνω στα αποσπάσματα με το `ontology_guided.validator` για να καταγράψετε τυχόν παραβιάσεις και να δημιουργήσετε πίνακες σύγκρισης (χρυσό vs επιχειρησιακό).【F:ontology_guided/validator.py†L1-L78】

```bash
python -m ontology_guided.validator \
    --data tmp/gold_withdrawal.ttl \
    --shapes gold/shapes_atm.ttl \
    --inference none
```

### 5.3 Εκτέλεση competency questions
Χρησιμοποιήστε τη `evaluate_cqs` για να εκτελέσετε τα ASK queries στο ίδιο απόσπασμα και να λάβετε τους δείκτες επιτυχίας (passed, total, pass_rate). Το module φορτώνει τα queries, εφαρμόζει προαιρετικά OWL RL reasoning και εκτελεί κάθε ASK διαδοχικά.【F:evaluation/competency_questions.py†L1-L74】

```python
from evaluation.competency_questions import evaluate_cqs

metrics_gold = evaluate_cqs("tmp/gold_withdrawal.ttl", "evaluation/atm_cqs.rq")
metrics_oper = evaluate_cqs("tmp/oper_withdrawal.ttl", "evaluation/atm_cqs.rq")
```

Καταγράψτε τα αποτελέσματα σε αναφορά σύγκρισης. Στις περιπτώσεις ασυμφωνίας, περιορίστε την προτροπή στο LLM στο συγκεκριμένο snippet (`tmp/oper_withdrawal.ttl`) ώστε να ζητήσετε διορθώσεις χωρίς επιπλέον token κόστος.

### 5.4 Αυτοματοποιημένα παραδείγματα και αποθήκευση αποτελεσμάτων
Για να εκτελέσετε το πλήρες παράδειγμα (εξαγωγή αποσπάσματος, SHACL, CQs) και να αποθηκεύσετε όλες τις απαντήσεις, χρησιμοποιήστε το βοηθητικό script `scripts/run_atm_examples.py` που ενοποιεί τα παραπάνω βήματα και δημιουργεί έτοιμα αναλυτικά αρχεία JSON/Markdown.【F:scripts/run_atm_examples.py†L1-L174】

```bash
python scripts/run_atm_examples.py \
    --terms atm:Withdrawal atm:Transaction atm:Customer \
    --depth 1 \
    --output-dir results/examples/withdrawal_demo \
    --tag gold_vs_oper
```

Η εντολή:

1. Δημιουργεί δύο αποσπάσματα (`gold_segment_<tag>.ttl`, `operational_segment_<tag>.ttl`) στους οποίους τρέχει SHACL και CQs.【F:scripts/run_atm_examples.py†L76-L120】
2. Αποθηκεύει αναλυτικό report σε JSON (με πλήρη λίστα παραβιάσεων) και συνοπτική Markdown αναφορά στον φάκελο `results/examples/withdrawal_demo`.【F:scripts/run_atm_examples.py†L122-L150】
3. Εκτυπώνει στη γραμμή εντολών τη σύνοψη ώστε να δείτε άμεσα πόσα queries πέρασαν και αν υπάρχουν παραβιάσεις.【F:scripts/run_atm_examples.py†L157-L174】

Μπορείτε να αλλάξετε τους όρους (`--terms`) και το βάθος (`--depth`) για να περιορίσετε το snippet σε συγκεκριμένα τμήματα της οντολογίας, όπως ζητήθηκε, εξασφαλίζοντας μικρό αριθμό API κλήσεων στο LLM.

## 6. Οδηγίες για Παρουσίαση & Επαναληψιμότητα
- Τεκμηριώστε ανά κύκλο αξιολόγησης το ζεύγος αποσπασμάτων (χρυσό vs επιχειρησιακό) και τις καταγραφές SHACL/CQ σε έναν κοινό φάκελο (π.χ. `results/2024-05/`).
- Χρησιμοποιήστε πίνακες δύο στηλών για να παρουσιάσετε τα metrics (π.χ. `Conforms`, `Violations`, `CQ pass rate`).
- Επισημάνετε τις διαφορές με στιγμιότυπα από τα Turtle αποσπάσματα και περιγράψτε πώς τα LLM prompts αξιοποίησαν τα snippets για διορθώσεις.
- Επαναχρησιμοποιήστε τα ίδια αποσπάσματα σε επόμενες επαναλήψεις για να διατηρήσετε συγκρισιμότητα και να αποφύγετε περιττά API calls.

Με αυτή τη ροή έχετε μια πλήρη τεχνική τεκμηρίωση του χρυσού πυρήνα ATM και μια πρακτική διαδικασία μετρήσεων που ελαχιστοποιεί την κατανάλωση LLM.
