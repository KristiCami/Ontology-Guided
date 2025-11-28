# Συστατικό 1 — Ontology-Aware Prompting (Τεχνική Περιγραφή)

Το Ontology-Aware Prompting (E3) καθοδηγεί το LLM με λεξιλόγιο που εξάγεται από την gold οντολογία, χωρίς να αντιγράφει το πλήρες TTL. Οι παρακάτω αρχές συνοψίζουν τη ροή και τα μέτρα ασφαλείας του συστήματος.

## 1. Αφετηρία
- Η διαδικασία ξεκινά από το requirements text, όχι από το `pred.ttl` baseline.
- Το baseline (E1) παραμένει ανέπαφο· το E3 εκτελεί νέο drafting με καθοδηγούμενο prompt.

## 2. Χρήση του gold
- Το gold **δεν** περνάει αυτούσιο στο prompt.
- Αντί για πλήρες TTL, εξάγεται δομημένο λεξιλόγιο (ontology grounding context):
  - Λίστα κλάσεων.
  - Object properties με domain/range.
  - Datatype properties με datatypes.
  - Labels/comments (όπου υπάρχουν).
  - Prefixes & namespace rules.
- Το λεξιλόγιο λειτουργεί ως «κανόνας» και όχι ως «λύση»· το LLM συνθέτει νέα axioms.

## 3. Τεχνική Εξαγωγής Λεξιλογίου
1. Συλλογή `owl:Class` ως έγκυρες κλάσεις.
2. Εξαγωγή object properties με domain/range.
3. Εξαγωγή datatype properties με datatypes.
4. Labels/synonyms όπου υπάρχουν (`rdfs:label`).
5. Prefixes με πλήρη IRI.

Παράδειγμα εξόδου:
```json
{
  "classes": ["ATM", "Bank", "Transaction"],
  "object_properties": {
    "operatedBy": {"domain": "ATM", "range": "Bank"}
  },
  "datatype_properties": {
    "requestedAmount": {"domain": "Transaction", "range": "xsd:decimal"}
  }
}
```

## 4. Δόμηση Prompt
- **SECTION A — Allowed Vocabulary:** classes, object properties (domain→range), datatype properties (domain→datatype), labels, prefixes.
- **SECTION B — Drafting Specification:** χρήση αποκλειστικά του παραπάνω λεξιλογίου, αποφυγή νέων ονομάτων εκτός αν το απαιτεί απαίτηση, τήρηση domain/range και namespace, έξοδος σε έγκυρο Turtle.
- **SECTION C — Requirements Input:** ίδιο κείμενο απαιτήσεων με το baseline.

## 5. Σειρά Εκτέλεσης E3
1. Requirements Text
2. Ontology-Aware Prompting Module (με `use_ontology_context=true`)
3. Νέο LLM drafting → `pred.ttl (iter0)`
4. Reasoner → SHACL → Metrics → CQs

Το LLM δεν λαμβάνει το παλιό `pred.ttl` ούτε γράφει πάνω του· συντάσσει νέο γράφημα εντός των «rails» του schema.

## 6. «Χρησιμοποιείς το gold αλλά δεν το αντιγράφεις»
- Το gold παρέχει μόνο vocabulary.
- Το LLM δημιουργεί νέα axioms από τις απαιτήσεις.
- Οι domain/range περιορισμοί μειώνουν τα λάθη και τη lexical drift.

## 7. Διαφορά E1 → E3 (τεχνικά)
| Feature | E1 (LLM-only) | E3 (ontology-aware, no-repair) |
| --- | --- | --- |
| Vocabulary | Ελεύθερο, εφευρίσκει ονόματα | Κλειδωμένο στο schema του gold |
| Domain/Range Awareness | Άγνοια περιορισμών | Πλήρης γνώση περιορισμών |
| Lexical Drift | Υψηλή | Χαμηλή |
| Structure | Χαοτική | Ημι-δομημένη |
| Validity | Πολλά invalid axioms | Σαφώς πιο valid |
| Cost / Iterations | 1 call / 1 iter | 1 call / 1 iter |

Το E3 είναι «guided-form»: καλύτερο από το baseline χωρίς να εξαρτάται από τα λάθη του.
