# Component 2 — SHACL Validation Integration (Τεχνική Περιγραφή)

## 1. Ρόλος του SHACL Validation στο OG–NSD
- Το SHACL είναι το υποσύστημα που ελέγχει αν η οντολογία που παρήγαγε το LLM είναι δομικά σωστή, πλήρης και σύμφωνη με τους κανόνες του domain.
- Δεν ελέγχει λογική συνέπεια (αυτό το κάνει ο reasoner), αλλά ελέγχει σχήμα και domain rules. Πιάνονται περιπτώσεις όπως:
  - Υποχρεωτικά πεδία που λείπουν (π.χ. performedBy/onAccount/requestedAmount σε Withdrawal).
  - Λάθος datatype, domain ή range.
  - Λάθος κλάση για property ή παραβίαση cardinality.
  - Προαιρετικά business rules (π.χ. policy limits, warnings).
- Αποτελεί τον πρώτο «τοίχο προστασίας» πριν από reasoner και repair loop.

## 2. Ποια οντολογία ελέγχεται
- Το SHACL validation τρέχει **πάντα** πάνω στη νέα οντολογία που παρήγαγε το LLM σε αυτό το run (`pred.ttl` και διαδοχικά patches).
- Δεν τρέχει ποτέ πάνω στο gold ούτε στο baseline output του E1. Σε E3/E4 η ακολουθία είναι:
  - E3: LLM drafting → `pred.ttl` → SHACL validation.
  - E4: `pred.ttl` → repair prompt → `new_pred.ttl` → SHACL validation → repeat.

## 3. Πηγή των SHACL rules
- Το `gold/shapes_atm.ttl` είναι χειροποίητο αρχείο shapes που αποτυπώνει domain constraints, **όχι** αντίγραφο του gold ontology.
- Αν αλλάξει το gold schema, το shapes ενημερώνεται μόνο όταν αλλάξουν οι domain rules. Το vocabulary πρέπει να παραμένει συνεπές μεταξύ `gold/atm_gold.ttl` και `gold/shapes_atm.ttl`.

## 4. Τεχνικά βήματα υλοποίησης
1. **Δημιουργία shapes:** Το `gold/shapes_atm.ttl` περιλαμβάνει minimal αλλά ουσιώδη NodeShapes (WithdrawalShape, CashCardShape, Authorization/TransactionShape, PerTransactionLimitShape κ.λπ.) με `sh:path`, `sh:minCount`, `sh:datatype`, `sh:class`, αριθμητικά όρια κ.λπ.
2. **Ενοποίηση στο pipeline:** Μετά το drafting, το pipeline φορτώνει `pred.ttl` ως data graph, το `shapes_atm.ttl` ως SHACL graph και εκτελεί validation αυτόματα σε κάθε iteration (E1, E3, E4). Το validation τρέχει χωρίς χειροκίνητα βήματα.
3. **Inference ρυθμίσεις:** Το pySHACL καλείται με `inference="rdfs"` και `advanced=True` για να κληρονομούνται οι περιορισμοί σε ιεραρχίες (π.χ. Withdrawal ⊑ Transaction).
4. **Κατηγοριοποίηση σφαλμάτων:** Τα validation results διαβάζονται προγραμματικά και ταξινομούνται σε:
   - **Hard violations:** λάθος domain/range, λάθος datatype, έλλειψη mandatory property (`sh:minCount`), λάθος class για property.
   - **Soft violations:** extra optional fields, cardinality που δεν σπάει inference, business rules (`sh:maxInclusive`/`sh:minInclusive`), warnings.
   Τα hard violations τροφοδοτούν το repair loop του E4, τα soft απλώς αναφέρονται.
5. **Έξοδοι αρχείων:** Για κάθε iteration αποθηκεύεται αναλυτικό SHACL report σε TTL και σύνοψη σε JSON. Τα default μονοπάτια είναι `build/iter_XX/validation_report.ttl` και `build/iter_XX/validation_summary.json`, με το τελευταίο στιγμιότυπο να αντιγράφεται και σε `build/validation_report.ttl` και `build/validation_summary.json`.

## 5. Κρίσιμα σημεία
- Τα SHACL constraints είναι "minimal but meaningful" ώστε να επιτρέπουν στο LLM να παράγει valid ontology χωρίς υπερ-δέσμευση.
- Το SHACL report πρέπει να αναλυθεί από parser (όχι manual inspection) για να μετρώνται οι παραβιάσεις και να παράγεται input για το Patch Calculus στο E4.
- Συμφωνία vocabulary: τα properties που αναφέρονται στα shapes πρέπει να υπάρχουν στο gold ontology και αντίστροφα.
