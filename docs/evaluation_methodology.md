# Μεθοδολογία Αξιολόγησης Οντολογιών

## Βασική ιδέα (2 προτάσεις)
Η ποιότητα μιας οντολογίας δεν είναι μονοδιάστατη: μπορεί να είναι (α) συντακτικά σωστή, (β) σημασιολογικά σωστή, (γ) λογικά συνεπής και (δ) λειτουργικά επαρκής για το domain. Κάθε metric καλύπτει διαφορετική διάσταση, επομένως χρειάζεται συνδυασμός μετρικών για ολοκληρωμένη εικόνα.

## 4 επίπεδα αξιολόγησης (High-level map)
| Επίπεδο | Metric | Τι μετρά |
| --- | --- | --- |
| Συντακτικό | Exact Matching | Αν τα RDF triples είναι ίδια |
| Σημασιολογικό | Semantic (Entailment) Matching | Αν τα axioms συνεπάγονται το ίδιο νόημα |
| Δομικό / Λογικό | SHACL + Reasoner | Αν η οντολογία είναι έγκυρη |
| Λειτουργικό | Competency Questions | Αν “δουλεύει” για το domain |

**Στόχος E4:** να βελτιώνει και τα τέσσερα, όχι μόνο ένα. Για E1 (baseline) στοχεύουμε στο να ελαχιστοποιήσουμε το ονοματολογικό drift ώστε να αυξηθούν τα exact/semantic scores χωρίς να αλλάξουμε τη gold.

## Exact Matching — «είναι ίδια τα triples;»
**Τι είναι:** Μετράμε αν ακριβώς τα ίδια RDF triples εμφανίζονται και στο pred και στο gold.  
**Παράδειγμα:**  
Gold: `Withdrawal rdfs:subClassOf Transaction`  
Pred: `Withdrawal rdfs:subClassOf Transaction` → match  
Pred: `Withdrawal owl:equivalentClass ...` → no match  
**Τι μας λέει:** Πόσο πιστά αντέγραψε/αναπαρήγαγε το μοντέλο τη gold οντολογία· είναι πολύ αυστηρό metric.  
**Γιατί δεν αρκεί:** Τιμωρεί σωστά μοντελοποιημένες αλλά διαφορετικές αναπαραστάσεις. Στα repair loops το exact μπορεί να μείνει χαμηλό ενώ η ποιότητα βελτιώνεται. Είναι baseline, όχι τελική αλήθεια.

## Semantic Metrics — «λένε το ίδιο πράγμα;»
**Ιδέα:** Συγκρίνουμε τι συνεπάγεται λογικά κάθε οντολογία, όχι τα raw triples. Αν δύο οντολογίες λένε το ίδιο πράγμα με διαφορετικό τρόπο, πρέπει να μετρήσουν ως σωστές.  
**Entailment:** Ένα γράφημα entails ένα triple αν αυτό προκύπτει μετά από reasoning (RDFS/OWL-RL).  
**Παράδειγμα:**  
Pred: `Withdrawal owl:equivalentClass [ owl:intersectionOf (Transaction ...) ]`  
⇒ συνεπάγεται: `Withdrawal rdfs:subClassOf Transaction`  
Semantic match: ναι (even if exact όχι).  
**Πρακτικά:** Τρέχουμε reasoning → closure → συγκρίνουμε τα closures.  
**Τι μετρά:** Precision/Recall/F1 δείχνουν εννοιολογική κάλυψη (κατανόηση), όχι αντιγραφή.  
**Πώς υλοποιείται εδώ:**  
- Στον κώδικα (`og_nsd/metrics.py`) γίνεται OWL 2 RL materialization με `owlrl` (αν είναι εγκατεστημένο) πριν τον υπολογισμό precision/recall/F1, ώστε να συγκριθούν inferred closures.  
- Αν λείπει το `owlrl`, η σύγκριση γίνεται στα raw triples (exact/normalized). Για πλήρη semantic μέτρηση προτείνεται `pip install owlrl`.

## SHACL + Reasoner — «είναι έγκυρη οντολογία;»
**Δεν είναι similarity metric.**  
**Ελέγχει:** λείπουν υποχρεωτικές ιδιότητες; λάθος datatypes; domain/range παραβιάσεις; logical inconsistencies.  
**Παράδειγμα:** “Withdrawal χωρίς requestedAmount” → violation.  
**Τι μας λέει:** Αν η οντολογία είναι δομικά/λογικά έγκυρη και αν το repair loop μειώνει τα violations. Μπορεί να έχει καλό semantic F1 αλλά πολλά SHACL errors.

## Competency Questions (CQs) — «δουλεύει για το domain;»
**Τι είναι:** SPARQL ASK queries που εκφράζουν domain απαιτήσεις.  
**Μετράμε:** ποσοστό CQs που περνούν.  
**Γιατί κρίσιμο:** Μετρά λειτουργική ορθότητα. Μπορεί SHACL/semantic να είναι οκ αλλά CQ να αποτυγχάνει → το ontology δεν καλύπτει τις ανάγκες.

## Πώς δένουν όλα μαζί
* Exact: πόσο κοντά είμαστε στο reference.
* Semantic: αν λέμε το ίδιο πράγμα.
* SHACL: αν η οντολογία είναι έγκυρη.
* CQs: αν καλύπτει τις απαιτήσεις.
Το E4 είναι επιτυχημένο μόνο αν βελτιώνει και τα τέσσερα.

## Αναμενόμενα patterns στα experiments
| Experiment | Exact | Semantic | SHACL | CQs |
| --- | --- | --- | --- | --- |
| E1 (LLM-only) | χαμηλό | χαμηλό | πολλά violations | ❌ |
| E3 (no-repair) | μέτριο | μέτριο | ⚠️ | ⚠️ |
| E4 (full) | ⬆ ή ↔ | ⬆⬆ | PASS | ⬆⬆ |

Αν στο E4: semantic ↑, SHACL ↓, CQ ↑ αλλά exact ↓ → είναι αναμενόμενο και αποδεκτό.

## Σε 2 προτάσεις (σύνοψη)
* Το exact μετράει αντιγραφή, το semantic κατανόηση, το SHACL εγκυρότητα και τα CQs χρησιμότητα.
* Ο στόχος είναι η ταυτόχρονη βελτίωση και των τεσσάρων διαστάσεων, όχι η μεγιστοποίηση μόνο του exact.

## Πρακτικές οδηγίες για καλύτερα αποτελέσματα (ιδίως στο E1)
- **Χρήση gold λεξιλογίου χωρίς αλλαγές:** Μην πειράζετε τη gold οντολογία για να “φτιάξετε” τα metrics· ο στόχος είναι να ευθυγραμμιστεί η πρόβλεψη.  
- **Namespace πειθαρχία:** Ορίστε/κρατήστε `base_namespace` στο config (`configs/atm_e1_llm_only.json`) και ελέγξτε ότι οι IRIs που παράγει το LLM ξεκινούν με αυτό (π.χ. `http://lod.csd.auth.gr/atm/atm.ttl#`). Δείγματα drift εμφανίζονται στο `run_report.json` (`drift_axioms_sample`).  
- **Ontology context on:** Βεβαιωθείτε ότι `use_ontology_context` είναι `true` στο E1 config ώστε το prompt να “κλειδώνει” στο λεξιλόγιο του `gold/atm_gold.ttl`.  
- **Χαμηλότερο στοχαστικό noise:** Μειώστε temperature/χρησιμοποιήστε `llm_mode: heuristic` για πιο ντετερμινιστική έξοδο, περιορίζοντας off-schema ονόματα.  
- **Ενισχυμένη semantic μέτρηση:** Εγκαταστήστε `owlrl` (περιλαμβάνεται στο `requirements.txt`) ώστε το script να υλοποιεί closure πριν τα semantic metrics.
- **Έλεγχος λειτουργικότητας:** Τρέξτε CQs (`atm_cqs.rq`) μετά την παραγωγή για να δείτε functional επάρκεια ακόμα κι αν το exact παραμένει χαμηλό.

## Τεχνική υλοποίηση (πού να κοιτάξετε/τι να τρέξετε)
- **Υπολογισμός metrics:** `og_nsd/metrics.py` υλοποιεί exact/semantic. Η OWL RL επέκταση ενεργοποιείται αυτόματα όταν υπάρχει `owlrl`. Χρησιμοποιεί αυτόματο format guessing, οπότε τόσο `.ttl` (Turtle) όσο και `.owl/.rdf` (RDF/XML) φορτώνονται χωρίς extra flags.  
- **E1 run (με τις αλλαγές):** `python scripts/run_e1_llm_only.py --config configs/atm_e1_llm_only.json` παράγει `pred.ttl`, `metrics_exact.json`, `metrics_semantic.json`, `cq_results.json`, και `run_report.json` με δείγματα drift/redundancy. Το output είναι Turtle (`pred.ttl`) και αξιολογείται κανονικά.  
- **Ενεργοποίηση ontology context:** Στο config `use_ontology_context: true` και `ontology_path: gold/atm_gold.ttl` (ή `--ontology-context` στο CLI).  
- **Έλεγχος namespaces:** Στο `run_report.json` δείτε `drift_axioms_sample` για IRIs εκτός namespace. Διορθώστε prompts/LLM params ώστε να αποφεύγονται.  
- **Περαιτέρω βελτίωση (E4):** Τρέξτε `scripts/run_e4_iterative.py` με shapes/reasoner ενεργά για repair loop που μειώνει SHACL violations και ανεβάζει semantic/CQ scores.
