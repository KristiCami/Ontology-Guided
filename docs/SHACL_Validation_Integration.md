# SHACL Validation Integration

## Σκοπός
Τεχνική αναφορά για το πώς ενσωματώνεται το SHACL validation στο OG‑NSD pipeline, ποιους ελέγχους παρέχει και ποια artefacts παράγονται σε κάθε run.

## Ρόλος SHACL στο σύστημα
- Το SHACL είναι ο πρώτος «τοίχος προστασίας» που διασφαλίζει ότι το draft ontology είναι δομικά σωστό και συμβατό με τους κανόνες του domain.  
- Ελέγχει σχήμα/κανόνες (υποχρεωτικές ιδιότητες, datatypes, domains/ranges, cardinalities), όχι λογική συνέπεια· ο reasoner καλύπτει την τελευταία.
- Τα αποτελέσματα του SHACL μετατρέπονται σε feedback προς το LLM (violation→prompt) στο E4 loop.

## Τι ελέγχει
- Missing/mandatory properties (π.χ. Withdrawal με performedBy, onAccount, requestedAmount).
- Σωστά datatypes και εύρη τιμών (π.χ. xsd:decimal, min/maxInclusive).
- Σωστές domains/ranges και κλάσεις στόχου.
- Cardinality κανόνες και προαιρετικά uniqueness (SPARQL constraints).
- Soft κανόνες πολιτικής (π.χ. PerTransactionLimit) που δηλώνονται ως warnings.

## Πηγή SHACL κανόνων
- Το shapes αρχείο είναι χειροποίητο domain specification, **όχι** αντίγραφο του gold ontology.
- Στο ATM domain χρησιμοποιείται το `gold/shapes_atm.ttl` με shapes όπως WithdrawalShape, CashCardShape, AuthorizationShape, PerTransactionLimitShape κ.ά.
- Αν αλλάξει το gold schema, τα shapes αλλάζουν μόνο αν αλλάξουν οι domain κανόνες.

## Ποιο γράφημα ελέγχεται
- Πάντα ελέγχεται το νέο draft (`pred.ttl`) που παράγει το LLM σε κάθε run/iteration.
- Δεν γίνεται validation στο gold ούτε στο baseline output προηγούμενων πειραμάτων.
- Ροές:
  - E3: LLM drafting → `iter0/pred.ttl` → SHACL validation → metrics/CQ.
  - E4: `iterN/pred.ttl` → SHACL validation → repair prompts/patches → νέο `pred.ttl` → επανάληψη.

## Τεχνικές ρυθμίσεις validator
- `pyshacl.validate` με `inference="rdfs"` και `advanced=True` ώστε οι constraints να κληρονομούνται μέσω ταξινομίας (π.χ. Withdrawal ⊑ Transaction).
- Προληπτικός έλεγχος για άκυρα `xsd:decimal` literals ώστε να αποφεύγονται runtime errors.

## Κατηγοριοποίηση hard vs soft
- Hard violations: severities με `sh:Violation` (domain/range λάθη, λάθος datatype, λείπει mandatory property, λάθος class).
- Soft violations: warnings/infos (π.χ. προαιρετικά πεδία, πολιτικές ορίων).
- Το summary JSON διαχωρίζει τα δύο και το E4 repair loop συνθέτει patches μόνο από τα hard.

## Ενοποίηση στο pipeline
1. Φόρτωμα draft γράφου (`pred.ttl`) στο `data_graph`.
2. Φόρτωμα SHACL shapes σε `shacl_graph`.
3. Εκτέλεση validation με RDFS inference.
4. Αποθήκευση αναφοράς (TTL) και σύνοψης (JSON).
5. Στο E4: μετατροπή hard violations σε patches και συνέχιση του loop μέχρι stop policy.

## Outputs ανά run
- Αναλυτικό SHACL report (TTL):
  - E3: `runs/E3_no_repair/validation_report.ttl`.
  - E4: `runs/E4_full/iterN/shacl_report.ttl` ανά iteration.
- Σύνοψη παραβιάσεων (JSON):
  - E3: `runs/E3_no_repair/validation_summary.json`.
  - E4: `runs/E4_full/final/validation_summary.json` και μετρήσεις ανά iteration στο `repair_log.json`.
- Patch plans (μόνο E4): `runs/E4_full/iterN/patches.json` από hard violations.

## Κρίσιμες οδηγίες/παρατηρήσεις
- Τα SHACL constraints πρέπει να είναι «minimal but meaningful» για το domain: αρκετά για να πιάσουν σημαντικά λάθη χωρίς να μπλοκάρουν το LLM.
- Τα outputs διαβάζονται μηχανικά: το JSON summary τροφοδοτεί το repair calculus και dashboards, όχι manual inspection.
- Το vocabulary μεταξύ shapes και gold πρέπει να είναι συνεπές· αν shapes αναφέρονται σε ανύπαρκτα URIs, ενημερώνεται το gold ή το shapes file.
