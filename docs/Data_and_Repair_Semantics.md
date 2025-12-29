# Διαχωρισμός Δεδομένων/Gold και Σημασιολογία Repair E4

Το παρόν έγγραφο περιγράφει τις κρίσιμες διορθώσεις πρωτοκόλλου που αφαιρούν διαρροή οντολογίας, ευθυγραμμίζουν τα ρυθμιστικά πεδία με την πραγματική εκτέλεση και επιβάλλουν σαφή σημασιολογία repair στον βρόχο E4.

## A. Ρόλοι Δεδομένων και Αποφυγή Διαρροής

- **Διαχωρισμός context και gold**
  - Νέο **ontology context**: `gold/atm_schema_context.ttl` (μόνο TBox, με κλάσεις, object/datatype properties, domain/range και prefixes).
  - **Gold οντολογία για metrics** παραμένει το `gold/atm_gold.ttl`.
- **Αλλαγές στη διαμόρφωση**
  - Τα `configs/atm_e4_iterative.json` και `configs/atm_ontology_aware.json` διακρίνουν πλέον:
    - `ontology_context_path`: πηγή για prompt grounding.
    - `gold_path`: πηγή μόνο για αξιολόγηση.
  - Το script E4 επιβάλλει ότι το `iterations` στο config είναι η μοναδική πηγή για τον αριθμό επαναλήψεων· το `--kmax` είναι παρωχημένο και πρέπει να ταυτίζεται με το config αν δοθεί.
- **Επιβολή prompt grounding**
  - Με `use_ontology_context=false` απενεργοποιείται πλήρως το φόρτωμα context.
  - Το φόρτωμα context απαιτεί `ontology_context_path` (ή ρητό `ontology_path`), αποτρέποντας την τυχαία χρήση του gold αρχείου.

## B. Σημασιολογία και Απαραβίαστα του Repair Loop

- **Διατήρηση κατάστασης**
  - Η εφαρμογή patch δεν επανεκκινεί το γράφημα τα patches εφαρμόζονται στο υπάρχον state ώστε να αποφεύγονται rewrite loops και απώλειες.
- **Πειθαρχία patch**
  - Η μετατροπή SHACL→patch κάνει dedup και ταξινόμηση για ντετερμινιστικά πλάνα.
  - Το prompt εφαρμογής patch απαγορεύει νέους namespaces/URIs, διαγραφές ή αλλαγές εκτός scope και απαιτεί πλήρη διατήρηση του ontology.
- **Ευθυγράμμιση metrics**
  - Τα τελικά metrics υπολογίζονται στο reasoned (expanded) γράφημα ώστε να ταιριάζουν με το validation surface του SHACL/CQ.

## C. Logging και Διαγνωστικά Πειραμάτων

- **Τεχνουργήματα ανά επανάληψη**
  - Κάθε φάκελος `iterX/` αποθηκεύει `cq_results.json` μαζί με SHACL reports και πλάνα patches.
- **Εμπλουτισμένο `repair_log.json`**
  - Καταγράφει σύνοψη SHACL, CQ pass rate και αποτυχίες, πλήθος patches ανά action, διαγνωστικά reasoning (enabled, consistency, unsat πλήθος, πλήθος triples) και το stop reason.

## D. Ρυθμιστικά για Αναπαραγωγιμότητα

- **Παράμετρος τεμαχισμού απαιτήσεων** ρυθμίζεται μέσω `requirements_chunk_size` ώστε να εκτίθεται η υπερπαράμετρος chunking.
- **Τήρηση του flag validation**: με `validation=false` ο SHACL βρόχος παρακάμπτεται αντί να τρέχει σιωπηρά.


