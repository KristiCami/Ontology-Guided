# Αξιολόγηση του run **E4_full** και προτάσεις βελτίωσης

## Τι παρατηρήσαμε
- Η παραμετροποίηση δηλώνει **20 iterations**, αλλά το loop σταμάτησε μετά το `iter0` επειδή η συνάρτηση τερματισμού είδε «no_hard_violations».【F:runs/E4_full/repair_log.json†L4-L29】【F:og_nsd/repair.py†L58-L95】
- Η SHACL αναφορά στο `iter0` είναι πλήρως σύμφωνη (`sh:conforms true`), άρα δεν παρήχθη κανένα patch για το επόμενο iteration.【F:runs/E4_full/iter0/shacl_report.ttl†L1-L4】
- Το παραγόμενο γράφημα περιέχει κυρίως δηλώσεις τάξεων/ιδιοτήτων και όχι στιγμιότυπα που να ενεργοποιούν τα SHACL shapes (π.χ. δεν υπάρχουν άτομα τύπου `atm:Withdrawal` με υποχρεωτικά πεδία), οπότε οι node shapes με `sh:targetClass` δεν βρίσκουν focus nodes για να δώσουν παραβιάσεις.【F:runs/E4_full/iter0/pred.ttl†L1-L120】【F:gold/shapes_atm.ttl†L1-L80】
- Παρά τον πρόωρο τερματισμό, το τελικό γράφημα πέτυχε exact/semantic F1 ≈ 0.36 με 69 κοινά τρίπλετς, αλλά η κάλυψη CQ έμεινε στο ~57% (12/21).【F:runs/E4_full/final/metrics_exact.json†L1-L7】【F:runs/E4_full/final/cq_results.json†L1-L199】

## Γιατί έγινε μόνο ένα iteration
1. **Κριτήριο τερματισμού:** Το `should_stop` τερματίζει αμέσως όταν τα hard violations είναι 0, χωρίς να εξετάζει την CQ pass rate ή άλλο σήμα ποιότητας. Στο `iter0` το σύνολο παραβιάσεων ήταν 0, άρα το loop σταμάτησε παρότι οι CQ αποτυγχάνουν σε 9/21 περιπτώσεις.【F:og_nsd/repair.py†L58-L95】【F:runs/E4_full/repair_log.json†L14-L46】
2. **Μηδενικές SHACL παραβιάσεις:** Οι node shapes απαιτούν ιδιότητες σε συγκεκριμένα instances (π.χ. `atm:Withdrawal` με `atm:performedBy`), όμως το draft γράφημα δεν περιέχει τέτοια instances — μόνο ορισμούς κλάσεων/ιδιοτήτων. Έτσι, οι shapes δεν έχουν focus nodes και ο validator επιστρέφει `conforms=true`, άρα δεν δημιουργούνται patches.【F:runs/E4_full/iter0/pred.ttl†L1-L120】【F:gold/shapes_atm.ttl†L1-L80】【F:runs/E4_full/iter0/shacl_report.ttl†L1-L4】

## Προτεινόμενες βελτιώσεις για να «τρέχει» το loop
1. **Σύνδεση τερματισμού με CQ:** Τροποποίησε το `should_stop` ώστε να απαιτεί είτε (α) 0 hard violations *και* CQ pass rate ≥ threshold, είτε (β) σκληρό όριο iterations. Έτσι αποφεύγεται ο πρόωρος τερματισμός όταν η ποιότητα παραμένει χαμηλή.【F:og_nsd/repair.py†L58-L95】
2. **Ενεργοποίηση SHACL μέσω instances:** Κατά το drafting (`iter0`), δημιούργησε τουλάχιστον ένα ελάχιστο instance ανά targetClass των shapes (π.χ. ένα `atm:Withdrawal` με dummy πόρους/λίτρα) ώστε τα `sh:minCount`/`sh:datatype` να ελεγχθούν και να παραχθούν patches. Εναλλακτικά, πρόσθεσε helper που μετατρέπει απαιτήσεις σε mock instances πριν το πρώτο validation.【F:runs/E4_full/iter0/pred.ttl†L1-L120】【F:gold/shapes_atm.ttl†L1-L80】
3. **Patches από αποτυχίες CQ:** Αν δεν υπάρχουν SHACL violations αλλά αποτυγχάνουν CQ, παράγαγε patches από τα CQ αποτελέσματα (π.χ. για τα queries που ελέγχουν `atm:displays`, `atm:hasBackUpPowerSupply`, κ.λπ.) ώστε να συνεχίζεται το loop με στοχευμένες προσθήκες σε ιδιότητες/κλάσεις.【F:runs/E4_full/final/cq_results.json†L1-L199】
4. **Soft/Warning escalation:** Επίτρεψε στα soft (warning) SHACL αποτελέσματα να μετατρέπονται σε patches όταν τα hard violations είναι 0, ώστε να υπάρχει υλικό για επόμενο iteration ακόμη κι αν λείπουν μόνο προειδοποιήσεις.

Με αυτά τα βήματα, το loop θα έχει σήματα (SHACL ή CQ) για να παράγει patches σε επόμενα iterations, αντί να σταματά στο `iter0` χωρίς καμία προσπάθεια βελτίωσης.
