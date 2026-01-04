# Διαχωρισμός απαιτήσεων και σύνθεση prompt

Το M2 πρωτόκολλο απαιτεί να χωρίζονται οι προτάσεις απαιτήσεων σε dev/test και να χρησιμοποιούνται **μόνο** οι dev προτάσεις ως few-shot παραδείγματα. Παρακάτω περιγράφεται πώς υλοποιούνται οι κανόνες στο codebase.

## Πώς χωρίζονται οι απαιτήσεις
- Τα IDs dev/test δίνονται στα αρχεία `splits/dev.txt` και `splits/test.txt`. Στο παράδειγμα περιλαμβάνονται τα `FR-1, FR-2` (dev) και `FR-3, FR-4` (test).  
- Ο loader (`RequirementLoader`) κανονικοποιεί τίτλους όπως «Functional requirement 3» σε IDs τύπου `FR-3`, ώστε να ταιριάζουν με τα split αρχεία. Αν κάποιο ID δεν βρεθεί, καταγράφεται στο `run_report.json` ως `unmatched_split_ids` για να εντοπιστεί η απόκλιση.  
- Η προαιρετική αντιστοίχιση dev/test δεν αγγίζει την gold οντολογία (`gold/atm_gold.ttl`): δεν γίνεται «split» ή τροποποίηση της gold TTL, σύμφωνα με τις οδηγίες. Το split αφορά μόνο τις προτάσεις που τροφοδοτούν το LLM.

## Τι χρησιμοποιείται στο prompt (και τι όχι)
Για κάθε παρτίδα requirements:
- **Schema context (fixed):** εξάγεται λεξιλόγιο/επιτρεπτό vocabulary από το grounding TTL (π.χ. `gold/atm_context_tbox.ttl`) και μπαίνει στην ενότητα `SECTION A — Allowed Vocabulary`.  
- **Task spec (fixed):** ενότητα με κανόνες εξόδου (Turtle, χρήση `atm:` namespace, αποφυγή νέων όρων κ.λπ.).  
- **Few-shot (dev only):** έως 6 παραδείγματα από το dev split. Στο prompt εμφανίζονται μόνο τα dev IDs και τα axioms που συνοδεύουν κάθε dev απαίτηση (αν υπάρχουν στο JSON). Test προτάσεις και το gold OWL τους **δεν** μπαίνουν ποτέ στα examples.  
- **Target sentences:** το batch των υπό επεξεργασία προτάσεων (dev+test) έρχεται στο τέλος (`SECTION C`). Η gold TTL δεν περνάει αυτούσια στο prompt — μόνο το vocabulary.  
- **Repair (όταν χρειαστεί):** ο validator/λόγος παράγει violations και στέλνονται στο LLM, χωρίς να περιλαμβάνεται gold OWL test πρότασης.

## Τι «logάρουμε»
- Το `run_report.json` περιλαμβάνει `few_shot_exemplars` με τα IDs των dev προτάσεων που χρησιμοποιήθηκαν σε όλα τα batches, ώστε να αποδεικνύεται ποιο exemplar pool ήταν παγωμένο πριν το testing.  
- Η λίστα `unmatched_split_ids` εμφανίζει IDs που υπήρχαν στα split αρχεία αλλά δεν βρέθηκαν στο requirements corpus (για να διορθωθούν πριν την αξιολόγηση).

## Ροή εκτέλεσης
- Το preset `scripts/run_atm_examples.py --config configs/atm_ontology_aware.json` ενεργοποιεί το ontology-aware draft, SHACL/Reasoner, και αναφορές metrics/CQ.  
- Στο config ορίζονται `dev_split`/`test_split`, η διαδρομή του grounding TTL (`ontology_context_path`), και το `gold_path` για τις μετρικές.  
- Ο pipeline περιορίζει τα few-shot σε dev-only, διατηρεί σταθερό exemplar pool, και δεν αγγίζει τη gold TTL, καλύπτοντας όλα τα bullets της προδιαγραφής (split handling, prompt construction, no leakage).
