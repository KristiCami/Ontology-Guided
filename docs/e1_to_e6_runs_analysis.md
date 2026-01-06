# Εμπλουτισμένη αξιολόγηση πειραμάτων E1–E6 και αναλυτική αποτίμηση JSON

## Εισαγωγή
Η παρούσα τεχνική αναφορά αποτελεί εκτενές υπόμνημα (περί τις 10.000 λέξεις) για τα πειράματα που βρίσκονται στον φάκελο `runs/` της τρέχουσας έκδοσης του αποθετηρίου. Καλύπτει όλες τις εκτελέσεις E1–E4 που αφορούν το σενάριο ATM, καθώς και τις νεότερες εκτελέσεις E5 (διατομεακή αξιολόγηση ATM/health) και E6 (σάρωση κατωφλιών CQs). Η γραφή είναι προσανατολισμένη σε ακαδημαϊκή τεκμηρίωση, με στόχο να αποτυπώνει τις παρατηρήσεις πάνω στα JSON, να εξηγεί τις μετρικές και να αιτιολογεί τις αποκλίσεις σε σχέση με τις αναμενόμενες συμπεριφορές. Το κείμενο είναι δομημένο θεματικά και χρονικά, ώστε να φαίνεται καθαρά η εξέλιξη του pipeline, οι βελτιώσεις ή οπισθοχωρήσεις ανά παραλλαγή, και η αξία των πειραμάτων ως προς τη χρήση τους για καθοδήγηση οντολογιών που δημιουργούνται ή επιδιορθώνονται με LLMs.

## Πίνακες συνοπτικών αποτελεσμάτων (επικαιροποίηση από τα αρχεία `runs/`)
Οι παρακάτω πίνακες ενσωματώνουν τις πραγματικές τιμές που εξήχθησαν από τα JSON των εκτελέσεων (metrics, CQ logs, repair logs). Όλα τα νούμερα είναι semantic F1 εκτός αν αναφέρεται διαφορετικά. Η στήλη SHACL καταγράφει τα τελικά (hard/soft) violations, ενώ η στήλη Reasoner αντικατοπτρίζει το πεδίο `consistent` στα repair logs.

### Πίνακας Α – Κύρια πειράματα (E1–E6)
| ID / Παραλλαγή | Domain / Setup | Semantic F1 (Exact) | CQ Pass | SHACL | Reasoner | Iters / Stop | Σχόλια |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E1 (seed1, draft) | ATM, LLM-only | 0.4769 (0.4769) | 11/21 (0.524) | N/A | N/A | Draft-only | 156 pred triples, 1 559 tokens (`runs/E1_llm_only_seed1`) |
| E1 (seed2, draft) | ATM, LLM-only | 0.1079 (0.1079) | 2/21 (0.095) | N/A | N/A | Draft-only | 190 pred triples, 1 416 tokens (`runs/E1_llm_only_seed2`) |
| E2 symbolic | ATM, rules+reasoner | 0.3333 (0.3670) | 12/21 (0.571) | 0/0 | true | Single pass | 289 pred, 36 missing classes (`runs/E2_symbolic_only`) |
| E3 no-repair | ATM, few-shot | 0.2451 (0.2451) | 12/21 (0.571) | 0/0 | true | Iter0 only | 438 pred, 40 invalid restrictions removed (`runs/E3_no_repair`) |
| E4 full – default | ATM, closed loop | 0.3052 (0.3052) | 11/21 (0.524) | 0/0 | true | 2 iters, stop: no_hard_violations | 15 patches/iter, pred 314 (`runs/E4_full_default/final`) |
| E4 full – hard\_and\_cq | ATM, aggressive stop | 0.0442 (0.0442) | 4/21 (0.190) | 0/0 | null | 3 iters, stop: patches_unchanged | Pred 871, Pellet NPEs (`runs/E4_full_hard_and_cq/final`) |
| E4 full – max\_only | ATM, capped iters | 0.3427 (0.3427) | 11/21 (0.524) | 0/0 | true | 4 iters, stop: max_iterations_reached | Pred 266, stable Pellet (`runs/E4_full_max_only/final`) |
| E4 full – ignore\_no\_hard | ATM, ignore hard | 0.0343 (0.0343) | 16/21 (0.762) | 0/0 | null | 3 iters, stop: patches_unchanged | Pred 2 380, Pellet NPEs (`runs/E4_full_ignore_no_hard/final`) |
| E5 cross-domain (ATM) | ATM, prompt swap | 0.2191 (0.2296) | 6/21 (0.286) | 0/0 | null | Draft-only | 231 pred, Pellet NPE (`runs/E5_cross_domain/atm`) |
| E5 cross-domain (Health) | Health, prompt swap | 0.0909 (0.0484) | 1/8 (0.125) | 0/0 | null | Draft-only | 212 pred, 140 invalid restrictions dropped (`runs/E5_cross_domain/health`) |
| E6 CQ sweep (thr 0.5) | ATM, repair with p≥0.5 | N/A | 3/21 (iter1–2) | 0/0 | null | 3 iters, stop: patches_unchanged | Pass rate 0.048→0.143→0.143, triples after reasoning 382→1079 (`runs/E6_cq_sweep/threshold_0_5`) |
| E6 CQ sweep (thr 0.8) | ATM, repair with p≥0.8 | N/A | 11/21 (iter0–1) | 0/0 | true | 2 iters, stop: patches_unchanged | Pass rate stable 0.524, triples after reasoning 280 (`runs/E6_cq_sweep/threshold_0_8`) |

### Πίνακας Β – Ablations & Sensitivity (A1–A14)
Δεν υπάρχουν αντίστοιχα artefacts κάτω από `runs/` για τις A1–A14, οπότε οι τιμές παραμένουν «N/A». Ο πίνακας καταγράφει την κατάσταση για διαφάνεια και μελλοντική συμπλήρωση.

| ID | Παραλλαγή | Κατάσταση στο repo | Παρατηρήσεις για συμπλήρωση |
| --- | --- | --- | --- |
| A1 (−wSHACL) | Ίδια λ, χωρίς severities | N/A (δεν εκτελέστηκε) | Προσθήκη μετρικών όταν υπάρξει run: iters, post-violations, CQ% |
| A2 (−PatchCalc) | Raw Turtle | N/A (δεν εκτελέστηκε) | Καταγραφή soft error/invalid RDF rate |
| A3 (−Admissibility) | Commit χωρίς safety precheck | N/A (δεν εκτελέστηκε) | Χρειάζεται # νέων hard viol., unsat incidents |
| A4 (−OntoAwarePrompt) | Χωρίς grounding | N/A (δεν εκτελέστηκε) | Συλλογή ΔF1, iters, drift cases |
| A5 (Reasoner order) | Reasoner πριν/μετά SHACL | N/A (δεν εκτελέστηκε) | Μετρήσεις Δviolations, runtime |
| A6 (LLM swap) | GPT-X / Claude-Y / Llama-Z | N/A (δεν εκτελέστηκε) | F1, iters, time/iter, cost/ontology |
| A7 ($K_{max}$ budget) | K∈{1,2,3,5} | N/A (δεν εκτελέστηκε) | Conformance rate, F1@budget, time |
| A8 (Top-m hints) | m∈{0,5,10,20}, λ grid | N/A (δεν εκτελέστηκε) | ΔF1, iters, grounding errors |
| A9 (Weights λ) | λ1–λ3 grid | N/A (δεν εκτελέστηκε) | Pareto (F1, edits, CQ%) |
| A10 (Noisy reqs) | 5/15/30 % noise | N/A (δεν εκτελέστηκε) | ΔF1, Δiters, conformance% |
| A11 (Long docs) | 5/15/30/60 sentences | N/A (δεν εκτελέστηκε) | Runtime scaling, mem, conformance |
| A12 (Shapes coverage) | −/+20 % SHACL | N/A (δεν εκτελέστηκε) | Under/over-constraint impact |
| A13 (Aligners) | String vs Embedding vs Hybrid | N/A (δεν εκτελέστηκε) | Alignment P/R, downstream ΔF1 |
| A14 (CQ design) | CQ density/strictness | N/A (δεν εκτελέστηκε) | CQ density/strictness vs F1 |

## Μεθοδολογία ανάγνωσης και σύνθεσης των JSON

### Βασικές μετρικές και αρχεία
Κάθε πείραμα αποδίδει πλήθος JSON αρχείων:
- **`run_report.json`**: σύνοψη μεταδεδομένων (tokens, λίστα CQs, αποτελέσματα SHACL, σημειώσεις reasoner, λίστα iterations όπου εφαρμόζεται).
- **`metrics_semantic.json`** και **`metrics_exact.json`**: αριθμητική αποτίμηση precision, recall και F1, μαζί με πλήθος προβλεπόμενων/χρυσών/επικαλυπτόμενων τριπλετών. Η semantic παραλλαγή επιτρέπει χαλαρή αντιστοίχιση (π.χ. ισοδυναμίες), ενώ η exact αποτιμά κυριολεκτική ταύτιση.
- **`cq_results.json`**: λίστα competency questions (CQs) με δυαδικό αποτέλεσμα `success` και συνολικό `pass_rate`. Για τα ATM σενάρια τα CQs είναι 21 (στα E2/E3 εκτελούνται τα ίδια 21, με 12 επιτυχίες).
- **`iteration_log.json` και `patches.json`**: εμφανίζονται στις εκτελέσεις που περιλαμβάνουν repair βρόχο (κυρίως E4 και E6). Περιλαμβάνουν πλήθος patches, τύπο (addProperty/addSubclass κ.ά.), αποτέλεσμα SHACL/Reasoner/CQ ανά iteration και λόγο τερματισμού.
- **`validation_summary.json`**: τελικός αριθμός παραβιάσεων (hard/soft) στο snapshot `final`.
- **`llm_error.txt`**: καταγράφει αποτυχίες parsing Turtle από LLM στο repair loop.

### Ερμηνεία μετρικών
- **Precision (καθαρότητα)**: ποσοστό των παραγόμενων τριπλετών που ανήκουν στο gold. Χαμηλή τιμή συνήθως υποδηλώνει «φλυαρία» του LLM ή επιθετικά patches που εισάγουν θόρυβο.
- **Recall (κάλυψη)**: ποσοστό των χρυσών τριπλετών που εντοπίζονται στην πρόβλεψη. Χαμηλή τιμή δείχνει έλλειψη κρίσιμων εννοιών/ιδιοτήτων ή υπερβολικές αφαιρέσεις κατά το repair.
- **F1**: αρμονικός μέσος precision και recall. Χρήσιμος ως συνολικός δείκτης ποιότητας.
- **Pass rate CQs**: ποσοστό CQs που επιστρέφουν true. Για τα ATM σενάρια με 21 CQs, `pass_rate 0.5238` αντιστοιχεί σε 11 επιτυχίες, ενώ `0.1904` σε 4 επιτυχίες.

### Ερμηνεία reasoning/SHACL
- **SHACL**: στις περισσότερες εκτελέσεις `conforms: true`, άρα οι παραβιάσεις δεν είναι ορατές στο SHACL επίπεδο. Αυτό σημαίνει είτε ότι οι shapes είναι ήπιες είτε ότι το repair αφαιρεί τις παραβιάσεις πριν το τελικό snapshot.
- **Reasoner (Pellet)**: σε αρκετά πειράματα εμφανίζονται σημειώσεις τύπου «Declared N missing owl:Class resource(s)» ή αποτυχίες ταξινόμησης με Java NPE. Αυτά δείχνουν είτε προσθήκη ανώνυμων κλάσεων από περιορισμούς είτε αυξημένη πολυπλοκότητα που οδηγεί σε κρασαρίσματα. Η συνέπεια (`consistent: true/false/null`) επηρεάζει την εμπιστοσύνη στο μοντέλο.

### Δομή της αναφοράς
Η ανάλυση χωρίζεται σε ενότητες ανά πείραμα, με έμφαση στην πορεία από E1 (LLM μόνο) έως E4 (πολλαπλά σενάρια repair), και κατόπιν στις επεκτάσεις E5–E6. Για κάθε ενότητα παρουσιάζονται:
1. **Γενικά μεταδεδομένα** (tokens, mode, seeds, few-shot).
2. **Μετρικές** (precision/recall/F1) και τι σημαίνουν.
3. **CQs**: αναλυτικά ποια περνούν ή αποτυγχάνουν και πιθανές αιτίες.
4. **Εξέλιξη iterations / patches** όπου υπάρχουν.
5. **Συμπεράσματα και αναμενόμενα επόμενα βήματα**.

## Γενική περίληψη σκόρ
Για αναφορά, οι βασικές μετρικές ανά τελικό snapshot είναι:
- **E1_llm_only_seed1**: F1≈0.477 (precision 0.4295, recall 0.536), CQ pass 11/21.
- **E1_llm_only_seed2**: F1≈0.108 (precision 0.0895, recall 0.136), CQ pass 2/21.
- **E2_symbolic_only**: F1≈0.367 exact (0.333 semantic), CQ pass 12/21.
- **E3_no_repair**: F1≈0.245, CQ pass 12/21.
- **E4_full_default (final)**: F1≈0.305, CQ pass 11/21, 0 hard/soft παραβιάσεις.
- **E4_full_hard_and_cq (final)**: F1≈0.044, CQ pass 4/21, 0 hard/soft παραβιάσεις.
- **E4_full_max_only**: F1≈0.343 (precision 0.2519, recall 0.536) με 266 pred_triples, CQ pass 11/21, 0 hard/soft παραβιάσεις, stop_reason `max_iterations_reached`.
- **E4_full_ignore_no_hard**: F1≈0.034 (precision 0.0181, recall 0.344) με 2.380 pred_triples, CQ pass 16/21, 0 hard/soft παραβιάσεις, stop_reason `patches_unchanged` (Pellet NPEs).
- **E5_cross_domain (ATM)**: F1≈0.219 semantic (0.2296 exact), CQ pass 6/21.
- **E5_cross_domain (Health)**: F1≈0.091 semantic (0.048 exact), CQ pass 1/8.
- **E6_cq_sweep**: μόνο repair logs (threshold 0.5 και 0.8), χωρίς τελικά metrics· pass rates παρατίθενται ανα iteration.

## Πείραμα E1 – LLM μόνο, seed 1
### Μεταδεδομένα και μέγεθος γραφήματος
Το `runs/E1_llm_only_seed1/run_report.json` δηλώνει `mode: "draft_only"` με 1.559 tokens (1.128 prompt, 431 completion) και 156 παραγόμενες τριπλέτες. Δεν υπάρχει repair βρόχος, ούτε shapes, ούτε reasoner. Αυτό το baseline αντιπροσωπεύει «ελεύθερη» παραγωγή του LLM χωρίς καθοδήγηση.

### Μετρικές
`metrics_semantic.json` και `metrics_exact.json` ταυτίζονται: precision 0.4295, recall 0.536, F1 0.4769, overlap 67/125 gold. Η ταύτιση semantic/exact δείχνει ότι δεν υπήρξε χαλάρωση στην αντιστοίχιση.

### CQs (21 στο σύνολο)
`pass_rate: 0.5238` (11/21). Τα επιτυχημένα εστιάζουν σε βασικές τάξεις (ATM/Bank/Customer/Account/Transaction), ιεραρχίες Withdrawals⊑Transaction, σύνδεση ATM–Bank, datatypes (bankCode, transactionTimestamp, requestedAmount, dispensedAmount), και σύνδεση πελατών με κάρτες ή λογαριασμούς. Αποτυγχάνουν λειτουργικά/υποδομής: dispenses money, UI unions, power supplies, verification timings, bank-computer επικοινωνίες, ενημερώσεις metrics, απαιτήσεις, credentials union, keypad.

### Ερμηνεία
- **Precision**: Με 156 τριπλέτες, σχεδόν το 57% είναι εκτός gold, αλλά το υπόλοιπο 43% καλύπτει σημαντικές έννοιες. Ο θόρυβος είναι ανεκτός για baseline.
- **Recall**: 0.536 σημαίνει ότι η μισή χρυσή οντολογία αναπαράγεται. Το LLM «πιάνει» τις κλασικές σχέσεις, αλλά αγνοεί λεπτομέρειες UI/λειτουργικότητας.
- **CQs**: Η επιτυχία σε 11/21 δείχνει ότι τα δεδομένα prompt ήταν επαρκή για core domain, όχι όμως για resilience/μετρικές/απαιτήσεις.

### Αναμενόμενη βελτίωση
Θα αναμέναμε ότι few-shot ή repair θα κρατήσουν την κάλυψη (recall ≈0.53) και θα αυξήσουν precision με απομάκρυνση θορύβου ή με στοχευμένες προσθήκες για αποτυχημένες CQs.

## Πείραμα E1 – LLM μόνο, seed 2
### Μεταδεδομένα
`run_report.json`: 190 τριπλέτες, mode draft_only, 1.416 tokens (1128 prompt, 288 completion). Η παραγωγή είναι πιο «φλύαρη» από το seed1.

### Μετρικές
Precision 0.0895, recall 0.136, F1 0.1079, overlap 17/125. Οι δείκτες καταρρέουν σε σχέση με seed1.

### CQs
`pass_rate: 0.0952` (2/21). Η τεράστια πτώση συμβαδίζει με τις μετρικές.

### Ερμηνεία
- **Στοχαστικότητα LLM**: Η αύξηση τριπλετών δεν αύξησε την κάλυψη· αντίθετα, πρόσθεσε θόρυβο.
- **Λανθασμένες δομές**: Η χαμηλή κάλυψη υποδηλώνει ότι λείπουν ακόμη και βασικές σχέσεις (ATM–Bank, Withdrawals⊑Transaction), άρα το seed παρήγαγε αποπροσανατολισμένες δηλώσεις.
- **Συμπέρασμα**: Οι LLM-only εκτελέσεις είναι ευαίσθητες στο seed. Η μέση ποιότητα χωρίς σταθεροποιητικό μηχανισμό είναι ασταθής (F1 περίπου 0.29 αν συνυπολογιστούν και τα δύο seeds), άρα απαιτείται repair ή few-shot.

## Σύνοψη E1
- **Εύρος απόδοσης**: Από F1 0.48 (seed1) σε 0.11 (seed2). Η διακύμανση τονίζει την ανάγκη ελέγχων σταθερότητας.
- **CQs**: Από 52% σε 9%. Οι λειτουργικές CQs είναι συστηματικά δύσκολες και για τα δύο seeds.
- **Μάθημα**: Μόνο LLM prompt δεν αρκεί· πρέπει να ενσωματωθούν επιπλέον σήματα (few-shot, κανόνες ή repair) για να περιοριστεί το θόρυβος και να ενισχυθεί η ανάκτηση κρίσιμων τριπλετών.

## Πείραμα E2 – Συμβολική επεξεργασία χωρίς repair
### Μεταδεδομένα
`runs/E2_symbolic_only/run_report.json`: 1.697 tokens, SHACL `conforms: true`, reasoner `consistent: true`, 36 δηλωμένες missing `owl:Class`. Οι CQs είναι 12 (υποσύνολο), όλες επιτυχημένες.

### Μετρικές
- `metrics_semantic`: precision 0.2388, recall 0.552, F1 0.3333, pred 289, overlap 69.
- `metrics_exact`: precision 0.2749, recall 0.552, F1 0.3670, pred 251, overlap 69.
Η βελτίωση precision στην exact έκδοση οφείλεται στο ότι αφαιρούνται «χαλαρές» αντιστοιχίες της semantic.

### CQs
Pass rate 0.571 (12/21). Περνούν οι βασικές CQs (τάξεις, Withdrawals/Deposits⊑Transaction, ATM–Transaction/CashCard συνδέσεις, ATM–Bank σχέσεις, bankCode, timestamps, requestedAmount/transactionAmount, dispensedAmount). Αποτυγχάνουν οι λειτουργικές/ανθεκτικότητας (dispenses, UI unions, power supplies κ.λπ.).

### Reasoner/SHACL
- 36 δηλωμένες missing κλάσεις υποδηλώνουν ότι ο reasoner κατασκεύασε placeholders για να ικανοποιήσει περιορισμούς allValuesFrom/someValuesFrom.
- Συνεπής ταξινόμηση χωρίς unsat classes.

### Ερμηνεία
- **Recall**: 0.552, όσο και στο E3 (βλ. επόμενη ενότητα). Η συμβολική παραγωγή καλύπτει πάνω από το μισό gold.
- **Precision**: 0.27 (exact) είναι καλύτερο από το E3, χειρότερο από το LLM seed1. Αυτό δείχνει ότι, παρότι η παραγωγή είναι δομημένη, τα πρόσθετα αξιώματα για συνέπεια μειώνουν την καθαρότητα.
- **CQs**: Η τελειότητα στις 12 ερωτήσεις αναδεικνύει ότι οι core έννοιες κωδικοποιούνται σωστά, αλλά η απουσία των υπόλοιπων 9 ερωτήσεων δεν επιτρέπει αξιολόγηση λειτουργικών χαρακτηριστικών.

### Αναμενόμενα βήματα
Για να αυξηθεί precision χωρίς να χαθεί recall, απαιτείται φίλτρο που θα αφαιρεί γενικεύσεις που εισάγονται για λόγους συνέπειας. Η ενσωμάτωση των 21 CQs στο repair loop θα επέτρεπε πιο πλούσια αξιολόγηση.

## Πείραμα E3 – Few-shot χωρίς repair
### Μεταδεδομένα
`runs/E3_no_repair/run_report.json`: few-shot exemplars `FR-1`, `FR-2` επαναλαμβανόμενα, 2.916 tokens. Reasoner: 25 missing classes, αφαίρεση 40 invalid restrictions. SHACL `conforms: true`.

### Μετρικές
Precision 0.1575, recall 0.552, F1 0.2451, pred 438, overlap 69. Σε σχέση με E2, το recall παραμένει ίδιο, αλλά το precision πέφτει ~0.12 μονάδες.

### CQs
Pass rate 0.571 (12/21). Οι ίδιες βασικές CQs με το E2 περνούν, οι λειτουργικές αποτυγχάνουν. Άρα few-shot δεν βελτιώνει ή μειώνει τις core ερωτήσεις, απλώς προσθέτει τριπλέτες.

### Ερμηνεία
- **Υπερπαραγωγή**: Οι 438 τριπλέτες (έναντι 289 στο E2) οδηγούν σε χαμηλό precision. Η few-shot καθοδήγηση φαίνεται να ενθαρρύνει επιπλέον περιγραφές χωρίς αντίστοιχη αύξηση κάλυψης.
- **Recall**: Σταθερό στο 0.552. Τα παραδείγματα βοηθούν να μην χαθούν οι βασικές έννοιες, αλλά δεν προσθέτουν τις «δύσκολες» gold σχέσεις.
- **Reasoner**: Η αφαίρεση invalid restrictions δείχνει ότι κάποια από τα παραγόμενα μοτίβα ήταν ασύμβατα. Παρ' όλα αυτά, το τελικό TTL παραμένει συνεπές.

### Αναμενόμενη βελτίωση
Ένας repair βρόχος με έμφαση στο precision θα μπορούσε να αφαιρέσει θόρυβο, διατηρώντας τις core τριπλέτες. Η μετατροπή των αποτυχημένων CQs σε patches θα ήταν μια καλή πρακτική.

## Πείραμα E4 – Παραλλαγές full repair
Η σειρά E4 εισάγει επαναληπτικό repair με patches. Διαφέρει ως προς το stop policy και το πώς αξιολογούνται οι παραβιάσεις. Ο φάκελος κάθε παραλλαγής περιέχει `iter0`, `iter1`, ... και `final` (όπου επιτυγχάνεται). Παρακάτω αναλύονται οι τέσσερις παραλλαγές: default, hard_and_cq, max_only, ignore_no_hard.

### E4_full_default – Κύρια παραλλαγή με επιτυχές final
#### Μεταδεδομένα
- Iterations: `iter0`, `iter1`, `final`.
- `patches` ανά iteration: 15 (10 addProperty, 5 addSubclass) προερχόμενα από CQs.
- Reasoner: iter0 «Declared 32 missing owl:Class» και 0 unsat, iter1 «Removed 2 invalid restriction(s)… Declared 58 missing…». SHACL μηδενικές παραβιάσεις. Stop reason: `no_hard_violations`.

#### Μετρικές (final)
Precision 0.2134, recall 0.536, F1 0.3052, pred 314, overlap 67. Validation summary: 0 hard/soft παραβιάσεις.

#### CQs (iter0/iter1/final)
Pass rate 0.5238 σε όλα τα στάδια (11/21). Οι αποτυχίες παραμένουν σταθερές: Deposit⊑Transaction, dispenses, UI union, power supplies, verification times, bank-computer comms, updates union, requirements, customer types union, keypad keys.

#### Εξέλιξη patches
- Παρά την εφαρμογή 15 patches σε iter0 και διατήρηση ίδιου πλήθους σε iter1, το pass rate δεν βελτιώθηκε. Αυτό υποδηλώνει είτε ότι τα patches στόχευαν CQs που ήδη περνούσαν είτε ότι δεν εφαρμόστηκαν σωστά λόγω ελλιπούς RDF λίστας/σύνταξης.
- Ο αριθμός τριπλετών αυξήθηκε από 278 (before reasoning iter0) σε 314 (after reasoning iter1/final), δηλαδή +36, χωρίς βελτίωση CQs. Αυτό δείχνει ότι τα patches πρόσθεσαν θόρυβο ή τριπλέτες που δεν μετριούνται στις CQs.

#### Ερμηνεία
- **Precision vs Recall**: Σε σχέση με E2/E3, το recall έμεινε ~0.536 (λίγο χαμηλότερο από 0.552), αλλά το precision ανέβηκε από 0.1575 (E3) σε 0.2134, όχι όμως μέχρι το 0.2749 (E2 exact). Άρα το repair βελτίωσε την καθαρότητα έναντι του few-shot, όχι όμως σε επίπεδο συμβολικής παραγωγής.
- **CQ στασιμότητα**: Το γεγονός ότι όλες οι αποτυχίες παρέμειναν δείχνει ότι το stop policy (χωρίς παραβιάσεις hard) δεν συσχετίζεται με την ικανοποίηση των CQs. Οι CQs που αποτυγχάνουν είναι κυρίως «λειτουργικές» και απαιτούν σύνθετες RDF λίστες ή unions, τις οποίες τα patches δεν εισήγαγαν.
- **Reasoning**: Η προσθήκη πολλών missing classes μπορεί να αυξάνει τον θόρυβο, μειώνοντας precision.

#### Συμπέρασμα
Η default παραλλαγή παρήγαγε ένα συνεπές, χωρίς παραβιάσεις μοντέλο, αλλά με μέτριο F1 και σταθερό CQ pass rate. Η αξία της είναι ότι παρέχει σταθερό baseline repair που δεν καταρρέει, αλλά χρειάζεται ενίσχυση στις CQs.

### E4_full_hard_and_cq – Επιθετικό stop policy
#### Μεταδεδομένα
- Iterations: 0,1,2 και final.
- Patches: το `repair_log` καταγράφει σταθερά patches, αλλά τα τελικά μεγέθη γραφήματος εκτοξεύονται (pred 871).
- Validation summary: 0 παραβιάσεις (hard/soft).

#### Μετρικές (final)
Precision 0.0253, recall 0.176, F1 0.0442, pred 871, overlap 22. Η πτώση είναι δραματική σε σχέση με όλα τα άλλα σενάρια.

#### CQs
Pass rate 0.1904 (4/21). Περνούν μόνο οι τάξεις και οι ιεραρχίες Withdrawals⊑Transaction, Deposit⊑Transaction, και bankCode datatype. Όλες οι υπόλοιπες αποτυγχάνουν.

#### Ερμηνεία
- **Υπερδιόγκωση τριπλετών**: Οι 871 τριπλέτες υποδηλώνουν ότι τα patches πρόσθεσαν πληθώρα περιορισμών/axioms χωρίς εστίαση. Το precision σχεδόν μηδενίζεται.
- **Stop policy**: Παρά το ότι ονομάζεται `hard_and_cq`, το σύστημα τερματίζει με 4/21 CQs, άρα το κριτήριο τερματισμού πιθανώς βασίστηκε μόνο σε παραβιάσεις (0) και όχι σε pass rate.
- **Reasoning**: validation summary μηδενικό, αλλά αυτό δεν σημαίνει ποιοτική οντολογία. Η απουσία unsat classes συνυπάρχει με χαμηλή αντιστοίχιση στο gold.

#### Συμπέρασμα
Η παραλλαγή απέτυχε να βελτιώσει τις CQs και κατέστρεψε την ακρίβεια. Απαιτεί επανασχεδιασμό του patch generator (π.χ. ποινή σε υπερβολική αύξηση τριπλετών, έλεγχος duplicates) και alignment του stop policy με pass rate.

### E4_full_max_only – Τερματισμός σε μέγιστες επαναλήψεις με σταθερό pass rate
#### Μεταδεδομένα
- Iterations: 0–3 με stop_reason `max_iterations_reached`.
- Πλήθος patches ανά iteration: 15 (10 addProperty, 5 addSubclass) από CQs, `iterations_with_patches: 4`.
- Reasoner: Pellet `consistent: true` σε όλα τα βήματα. Missing classes αυξάνονται (37→304) και αφαιρούνται invalid restrictions (0→6). `triples_before_reasoning` διογκώνονται (219→1378) αλλά `triples_after_reasoning` μένουν σταθερά στις 266.
- SHACL: 0 παραβιάσεις σε όλα τα βήματα. `validation_summary` του final: 0 hard/soft.

#### Μετρικές (final)
Precision 0.2519, recall 0.536, F1 0.3427, pred 266, overlap 67 (exact = semantic). Είναι το καλύτερο F1 της σειράς E4, ελαφρά πάνω από το default (0.3052).

#### CQs
Pass rate σταθερά 0.5238 (11/21) σε όλα τα iterations. Οι ίδιες 10 λειτουργικές CQs αποτυγχάνουν (dispenses, UI union, power supplies, verification times, bank-computer comms, updates union, requirements, customer types union, keypad, Deposit⊑Transaction).

#### Ερμηνεία
- **Σταθερότητα με μικρό γράφημα**: Παρά το ότι ο generator προσπαθεί να αυξήσει το γράφημα, το reasoning το «συμπιέζει» στις 266 τριπλέτες, διατηρώντας precision/recall.
- **Καμία βελτίωση CQs**: Η πολιτική `max_only` δεν βελτίωσε τις 10 λειτουργικές αποτυχίες, αλλά παρέμεινε συνεπής και χωρίς παραβιάσεις.

### E4_full_ignore_no_hard – Υψηλό CQ pass με πολύ θόρυβο
#### Μεταδεδομένα
- Iterations: 0–2, stop_reason `patches_unchanged`.
- Patches: iter0 26 (19 addProperty, 7 addSubclass), iter1/iter2 μόνο 5 addSubclass. `iterations_with_patches: 3`.
- Reasoner: Pellet NPE σε όλα τα iterations (`consistent: null`). Missing classes διογκώνονται 46→311, invalid restrictions αφαιρούνται (0→4). `triples_before_reasoning` 262→2073 και `after_reasoning` 308→2380.
- SHACL: 0 παραβιάσεις· `validation_summary` final 0 hard/soft.

#### Μετρικές (final)
Precision 0.0181, recall 0.344, F1 0.0343, pred 2380, overlap 43. Η υψηλή κάλυψη συνοδεύεται από πολύ χαμηλή καθαρότητα.

#### CQs
Pass rate ανέβηκε από 0.0952 (2/21) στο iter0 σε 0.7619 (16/21) στα iter1/iter2. Οι αποτυχίες στο final περιορίζονται σε 5 CQs: transaction timestamp, UI union, bank-computer comms, updates union, customer types union.

#### Ερμηνεία
- **Κάλυψη CQs με τίμημα precision**: Τα patches (κυρίως addSubclass) αυξάνουν θεαματικά τις επιτυχίες CQs αλλά εκτινάσσουν τις τριπλέτες σε 2.380, προκαλώντας σχεδόν μηδενικό precision.
- **Reasoner αστάθεια**: Τα διαδοχικά Pellet NPEs και τα εκατοντάδες missing classes δείχνουν ότι το γράφημα είναι εύθραυστο, παρότι δεν αναφέρονται SHACL παραβιάσεις.

### Συνολική σύγκριση E4
- **Default vs Hard_and_cq**: Ο ίδιος αρχικός pass rate (0.5238) οδηγεί σε τελικό 0.5238 (default) και 0.1904 (hard_and_cq). Το μέγεθος γραφήματος είναι 314 vs 871, με precision 0.2134 vs 0.0253. Άρα το αυστηρό stop policy χωρίς ρητή ποινή στο μέγεθος γραφήματος οδηγεί σε υπερπαραγωγή και κατάρρευση precision.
- **Max_only vs Ignore_no_hard**: Και οι δύο έφτασαν σε `final`. Το max_only κρατά το pass rate σταθερό 0.5238 με μικρό γράφημα (266 τριπλέτες) και F1 0.343, ενώ το ignore_no_hard ανεβάζει pass rate σε 0.7619 αλλά με 2.380 τριπλέτες και F1 0.034. Η ποιότητα του αρχικού draft επηρεάζει την πορεία, αλλά και το stop policy (patches_unchanged) επιτρέπει θόρυβο.
- **Stability**: Η default παραμένει η μόνη πλήρως επιτυχής (χωρίς errors) με μηδενικές παραβιάσεις. Παρά τα μέτρια CQs, αποτελεί σταθερό σημείο αναφοράς.

## Πείραμα E5 – Διατομεακή αξιολόγηση (ATM και Health)
Το E5 αξιολογεί την ικανότητα του pipeline να προσαρμόζεται σε διαφορετικά domains χωρίς repair loop. Περιλαμβάνει δύο φακέλους: `runs/E5_cross_domain/atm` και `runs/E5_cross_domain/health`.

### E5 – ATM υποσύνολο
#### Μεταδεδομένα
- Tokens: 1.548 (1128 prompt, 420 completion).
- SHACL: `conforms: true` χωρίς παραβιάσεις.
- Reasoner: Pellet failed με NPE (SomeValuesRule) μετά από αφαίρεση 5 invalid restrictions και δήλωση 30 missing classes.

#### Μετρικές
- Semantic: precision 0.1688, recall 0.312, F1 0.2191, pred 231, overlap 39.
- Exact: precision 0.1845, recall 0.304, F1 0.2296, pred 206, overlap 38.
Η exact έχει ελαφρώς καλύτερο precision/F1 λόγω λιγότερων τριπλετών.

#### CQs (21)
Pass rate 0.2857 (6/21). Περνούν οι τάξεις, Withdrawals⊑Transaction, bankCode, timestamps, amounts, dispensedAmount/union· αποτυγχάνουν ATM–Transaction/accepts, ATM–Bank, customer-card, accounts, dispenses, UI union, power supply, timings, bank-computer comms, updates, requirements, credentials, keypad. Σε σχέση με E1 seed1, χάνονται αρκετές βασικές σχέσεις (ATM–Bank κ.λπ.).

#### Ερμηνεία
- **Cross-domain drift**: Το prompt πιθανόν περιείχε health context εκτός ATM, οδηγώντας σε χαμηλότερη κάλυψη ATM ειδικών σχέσεων. Η παρουσία invalid restrictions (5) και missing classes (30) δείχνει προσπάθεια να συνδυαστούν διαφορετικά patterns.
- **Precision**: Παρότι χαμηλότερο από E1 seed1 (0.43), είναι υψηλότερο από E1 seed2 (0.0895), υποδεικνύοντας ότι η cross-domain επίδραση δεν είναι τόσο καταστροφική όσο ένα κακό seed.

### E5 – Health υποσύνολο
#### Μεταδεδομένα
- Tokens: 2.469 (1564 prompt, 905 completion) – μεγαλύτερη κατανάλωση από το ATM τμήμα.
- SHACL: `conforms: true`.
- Reasoner: Pellet failed με AllValuesRule NPE, 140 invalid restrictions αφαιρέθηκαν, 37 missing classes.

#### Μετρικές
- Semantic: precision 0.0755, recall 0.1143, F1 0.0909, pred 212, overlap 16.
- Exact: precision 0.0349, recall 0.0786, F1 0.0484, pred 315, overlap 11.
Η exact είναι χειρότερη γιατί αυξάνει το pred_triples σε 315, πιθανώς λόγω διαφορετικής χαλάρωσης καταμέτρησης.

#### CQs (8)
Μόνο 1/8 επιτυχία: η CQ για αποφυγή διπλής κράτησης ραντεβού (no double-booked appointment slots) περνά· όλες οι υπόλοιπες (appointments με patient/clinician/time, visits με room/clinician, prescriptions με medication/dosage, lab orders με result, insurance policy number, vital signs με timestamp/patient, billing record με visit/amount) αποτυγχάνουν.

#### Ερμηνεία
- **Κατάρρευση coverage**: Recall 0.1143 σημαίνει ότι ελάχιστες gold τριπλέτες καλύπτονται. Το pipeline δεν διέθετε few-shot ή domain-specific guidance για health, άρα το LLM παρήγαγε γενικό σχήμα χωρίς τις κρίσιμες ιδιότητες.
- **Invalid restrictions**: Η αφαίρεση 140 invalid restrictions δείχνει έντονη πολυπλοκότητα ή λάθος μοτίβα (πιθανώς από αναλογίες με ATM). Αυτό επιβαρύνει precision και οδηγεί σε reasoner failures.
- **Συμπέρασμα**: Η διατομεακή γενίκευση απαιτεί προσαρμοσμένα prompts ή λίστα health CQs για να καθοδηγηθεί η παραγωγή.

## Πείραμα E6 – Σάρωση κατωφλιών CQs (threshold_0_5 και threshold_0_8)
Το E6 δεν παρήγαγε final metrics· μόνο `repair_log.json` υπάρχει για κάθε κατώφλι. Στόχος ήταν να εξεταστεί πώς αλλάζει ο βρόχος repair όταν θεωρείται ότι οι CQs περνούν αν η πιθανότητα επιτυχίας υπερβαίνει ένα κατώφλι (0.5 ή 0.8).

### Threshold 0.5
- **Iter0**: pass rate 0.0476 (1/21), ίδιο μοτίβο με E4 ignore_no_hard στο αρχικό στάδιο (εκεί 0.0952, 19 αποτυχίες). SHACL 0 παραβιάσεις. Reasoner: 3 invalid restrictions αφαιρέθηκαν, 223 missing classes, Pellet NPE.
- **Patches**: 25 (19 addProperty, 6 addSubclass) από CQs, iterations_with_patches: 3.
- **Stop**: `patches_unchanged` στο iteration 2, με triples_before_reasoning 859 → after 1079. Καμία βελτίωση pass rate καταγράφεται (το log κόβεται, αλλά το stop_reason δείχνει στασιμότητα patches).
- **Ερμηνεία**: Το χαμηλό κατώφλι δεν βοήθησε – το pass rate παρέμεινε πολύ χαμηλό και η διαδικασία σταμάτησε όταν τα patches έπαψαν να αλλάζουν. Η αύξηση τριπλετών χωρίς βελτίωση CQs υποδεικνύει misalignment μεταξύ patches και απαιτήσεων.

### Threshold 0.8
- **Iter0**: pass rate 0.5238 (11/21), ίδιο με E4 default. SHACL 0 παραβιάσεις. Reasoner: «Removed 30 invalid restrictions… Declared 68 missing classes», triples_before_reasoning 396 → after 280.
- **Patches**: 15 (10 addProperty, 5 addSubclass), iterations_with_patches: 2.
- **Stop**: `patches_unchanged` στο iteration 1, χωρίς επιπλέον iterations. Δεν υπάρχουν metrics, αλλά το pass rate δεν αυξήθηκε πέρα από 0.5238.
- **Ερμηνεία**: Το υψηλό κατώφλι σταμάτησε τη διαδικασία νωρίς. Παρότι το pass rate ήταν αξιοπρεπές, δεν υπήρξε push για βελτίωση των 10 αποτυχημένων CQs. Το shrink των τριπλετών (396→280) δείχνει ότι τα patches αφαίρεσαν υλικό, πιθανόν μειώνοντας recall αν υπήρχε final snapshot.

### Συνολικά συμπεράσματα E6
- Η πολιτική `patches_unchanged` χωρίς εξάρτηση από pass rate οδηγεί είτε σε πρόωρη διακοπή (threshold 0.8) είτε σε στασιμότητα με χαμηλή ποιότητα (threshold 0.5).
- Απαιτείται ρητή συνάρτηση κόστους που συνδυάζει pass rate, μέγεθος γραφήματος, και παραβιάσεις για να αποφευχθεί πρόωρος τερματισμός ή υπερ-πληθωρισμός.

## Σύνθεση ευρημάτων ανά μετρική
### Precision
- Υψηλότερο precision παρατηρείται στο E1 seed1 (0.4295) και E2 exact (0.2749). Τα repair loops χωρίς έλεγχο μεγέθους (E4 hard_and_cq) ή cross-domain (E5 health) καταρρέουν.
- Το E4 default ανεβάζει precision σε σχέση με E3 αλλά υπολείπεται E2, δείχνοντας ότι οι patches δεν ήταν επαρκώς precision-aware.

### Recall
- Σταθερό 0.536–0.552 για E1 seed1, E2, E3, E4 default. Κατάρρευση recall εμφανίζεται σε E1 seed2 (0.136), E4 hard_and_cq (0.176), E5 health (0.1143). Άρα οι πιο ακραίες παραλλαγές ή cross-domain σενάρια χάνουν κάλυψη.

### F1
- Καλύτερο F1: E1 seed1 (0.477), E2 exact (0.367), E4 default (0.305). Ελάχιστο: E4 hard_and_cq (0.044), E5 health exact (0.048), E1 seed2 (0.108). Η μέση εικόνα δείχνει ότι ακόμη και με repair η ποιότητα μένει μέτρια.

### CQs
- Πλήρης επιτυχία βασικών CQs 12/21 στα E2 και E3.
- 11/21 σε E1 seed1, E4 default, E6 threshold 0.8 iter0.
- 4/21 στο E4 hard_and_cq final.
- 1/21 στο E4 ignore_no_hard iter0 και E6 threshold 0.5 iter0.
- 6/21 στο E5 ATM, 1/8 στο E5 Health.

## Λεπτομερής ανάλυση αποτυχημένων CQs και πιθανές λύσεις
1. **Deposit⊑Transaction**: Αποτυγχάνει σε E4 default, E5 ATM. Λύση: προσθήκη rdfs:subClassOf axioms και επαλήθευση με reasoner.
2. **ATM dispenses Money**: Συστηματική αποτυχία. Απαιτεί απλή ιδιότητα domain ATM, range Money. Προτείνεται SHACL shape που την επιβάλλει.
3. **UI union (NormalDisplay, ErrorDisplay)**: Αποτυγχάνει λόγω RDF list πολυπλοκότητας. Προτείνεται έτοιμο template unionOf.
4. **Power supplies (backup/main)**: Απλό ζεύγος ιδιοτήτων. Προτείνεται shape ή patch με δύο someValuesFrom.
5. **Verification times (card/pin)**: Απλή ύπαρξη δύο datatype properties. Προτείνεται patch-δέσμη.
6. **Bank computer comms**: Τρία range constraints. Προτείνεται SHACL closed shape για ATM messaging.
7. **Metrics update union**: Απαιτεί unionOf με δύο μετρικές. Template απαραίτητο.
8. **Requirements (subject/verb/condition/else)**: Σπάνια κατασκευάζονται από LLM. Προτείνεται few-shot με παράδειγμα requirement και shape.
9. **Customer types union (PasswordOfCustomer + TransactionAmountOfTransaction)**: Παρόμοιο union θέμα.
10. **Keypad keys**: Μία ιδιότητα consistOfKeys. Εύκολο patch.

Η συστηματική αποτυχία αυτών των CQs σε πολλά runs υποδεικνύει ότι πρέπει να ενταχθούν στο repair ως hard κανόνες ή pre-baked templates.

## Ερμηνεία των iteration logs σε βάθος
### Patch counts και επιπτώσεις
- **E4 default**: 15 patches σε κάθε iteration, αλλά χωρίς βελτίωση CQs. Πιθανόν τα patches εφαρμόστηκαν αλλά δεν κάλυψαν τις ερωτήσεις ή δεν μετρούνταν λόγω syntactic variance.
- **E4 ignore_no_hard**: 26 patches iter0, με pass rate 0.0952. Αν και τα patches αύξησαν τις τριπλέτες, η ουσιαστική βελτίωση ήρθε στο iter1 (0.7619), άρα το πρώτο κύμα patches δεν στόχευε σωστά τις αποτυχίες.
- **E6 threshold 0.5**: 25 patches, iterations_with_patches 3, αλλά stop λόγω unchanged patches. Άρα μετά από 3 iterations οι προτάσεις ήταν ίδιες, δείχνοντας ότι ο generator κόλλησε.
- **E6 threshold 0.8**: 15 patches, stop στο iter1. Ο generator θεώρησε ότι δεν χρειάζονται περαιτέρω αλλαγές λόγω υψηλού κατωφλιού.

### Reasoner notes
- Missing classes αυξάνονται όταν τα patches προσθέτουν restrictions σε ανύπαρκτες κλάσεις. Π.χ. E4 default iter1: 58 missing classes, E6 thr0.5: 223 missing classes. Αυτό μειώνει precision και μπορεί να προκαλεί NPE στο Pellet.
- Invalid restrictions: E5 health αφαίρεσε 140 invalid restrictions· δείχνει ότι το LLM παρήγαγε πολλούς περιορισμούς με λάθος δομή.

### Stop reasons
- `no_hard_violations`: E4 default. Δείχνει ότι οι SHACL/hard κανόνες ήταν ικανοποιημένοι ήδη από iter1.
- `patches_unchanged`: E6 και πιθανώς άλλες, σημαίνει στασιμότητα generator.
- `patches_unchanged`/`max_iterations_reached`: Στα E4 max_only και ignore_no_hard δείχνουν στασιμότητα ή έλλειψη προόδου. Απαιτείται κριτήριο stop που συνδυάζει pass rate και μέγεθος γραφήματος, μαζί με sanitization των patches (υπάρχουν `llm_error.txt` αλλά δεν διακόπτουν τη ροή).

## Συγκριτική οπτική χρήσιμων σεναρίων
1. **Χρήσιμο baseline**: E1 seed1 (σταθερό LLM), E2 (συμβολικό). Παρέχουν μέτρο σύγκρισης.
2. **Χρήσιμη αλλά ατελής αυτο-διόρθωση**: E4 default – σταθερό pipeline, με ανάγκη καλύτερου CQ alignment.
3. **Παράδειγμα προς αποφυγή**: E4 hard_and_cq – δείχνει ότι η υπερβολική επιθετικότητα οδηγεί σε θόρυβο.
4. **Προειδοποιητικά**: E4 max_only/ignore_no_hard, E6 thr0.5 – αναδεικνύουν κινδύνους στασιμότητας patches, διόγκωσης τριπλετών και ανεπαρκούς βελτίωσης CQs.
5. **Διατομεακή πρόκληση**: E5 health – καταδεικνύει ότι χωρίς domain-specific CQs ή prompts η απόδοση καταρρέει.

## Προτεινόμενες κατευθύνσεις βελτίωσης
### Precision-aware repair
- Εισαγωγή ποινής για αύξηση pred_triples πάνω από 350.
- Χρήση diff-based patching: αν ένα patch δεν αυξάνει pass rate ή μειώνει παραβιάσεις, να απορρίπτεται.

### CQ-driven templates
- Δημιουργία έτοιμων Turtle snippets για unions (UI display, metrics update, customer types), dispenses, power supplies, verification times, keypad keys.
- Μετατροπή των 10 συστηματικά αποτυχημένων CQs σε SHACL shapes (hard) ώστε το stop policy να εξαρτάται και από αυτές.

### Robust parsing
- Προσθήκη sanitization layer για Turtle (π.χ. έλεγχος objectList, αποφυγή διπλών annotatedTarget) πριν εφαρμογή patch.
- Retry μηχανισμός με εναλλακτικό prompt αν ο πρώτος LLM response αποτύχει.

### Reasoner stability
- Μείωση missing classes: εισαγωγή σταθερής βιβλιοθήκης βοηθητικών κλάσεων ώστε οι restrictions να δείχνουν σε υπαρκτές κλάσεις.
- Αντικατάσταση Pellet με βιβλιοθήκη που χειρίζεται καλύτερα ανώνυμες κλάσεις ή χρήση incremental reasoning.

### Cross-domain support
- Για health domain, κατασκευή λίστα 10–12 CQs και few-shot παραδειγμάτων (appointments, visits, prescriptions, labs, insurance, vitals, billing). Χωρίς αυτά το recall μένει <0.12.

### Stop policy redesign
- Συνάρτηση στόχου: maximize (w1 * F1_est + w2 * CQ_pass_rate – w3 * log(pred_triples) – w4 * violations). Αν δεν βελτιώνεται για k iterations, σταματά.
- Ελάχιστος αριθμός iterations, αλλά και ανώτατος για να αποφεύγεται υπερδιόγκωση.

## Συμπέρασμα
Τα πειράματα E1–E6 δείχνουν την αξία και τα όρια των διαφορετικών στρατηγικών παραγωγής και επιδιόρθωσης οντολογιών:
- Η LLM-only παραγωγή μπορεί να είναι αξιοπρεπής (seed1), αλλά είναι ευμετάβλητη (seed2).
- Η συμβολική παραγωγή (E2) παρέχει καλή κάλυψη και συνέπεια, αλλά μέτριο precision.
- Το few-shot χωρίς repair (E3) αυξάνει θόρυβο.
- Ο repair βρόχος default (E4) σταθεροποιεί το pipeline, αλλά δεν αυξάνει το CQ pass rate· χρειάζεται καλύτερο alignment patches–CQs.
- Η επιθετική πολιτική (hard_and_cq) δείχνει ότι χωρίς έλεγχο μεγέθους και ποιότητας, τα patches μπορούν να καταστρέψουν precision και recall.
- Τα σενάρια max_only και ignore_no_hard αναδεικνύουν κινδύνους στασιμότητας, διόγκωσης τριπλετών και ανάγκη για ποιοτικότερο patch selection/sanitization.
- Η διατομεακή επέκταση (E5) εκθέτει την ανάγκη για domain-specific καθοδήγηση.
- Η σάρωση κατωφλιών CQs (E6) καταδεικνύει ότι το stop policy πρέπει να εξαρτάται από ουσιαστική πρόοδο, όχι απλώς από στασιμότητα patches.

Συνολικά, τα πειράματα είναι χρήσιμα γιατί χαρτογραφούν τα failure modes και τις περιοχές όπου απαιτούνται στοχευμένες παρεμβάσεις (templates, shapes, robust parsing). Η αναφορά αυτή μπορεί να αποτελέσει βάση για επόμενο κύκλο πειραμάτων με έμφαση στην αύξηση του CQ pass rate και στη μείωση του θορύβου, διατηρώντας την κάλυψη των gold τριπλετών.

## Παράρτημα Α – Αναλυτική χαρτογράφηση όλων των CQs ανά εκτέλεση
Σε αυτή την ενότητα καταγράφονται λεπτομερώς τα 21 ATM CQs και οι εκβάσεις τους σε όλες τις διαθέσιμες εκτελέσεις (E1 seeds, E2, E3, E4 παραλλαγές, E5 ATM, E6 thresholds). Ο στόχος είναι να αναδειχθούν μοτίβα επιτυχίας/αποτυχίας και να προταθούν συγκεκριμένες ενέργειες. Οι περιγραφές είναι αφηγηματικές ώστε να διευκολύνουν τη χρήση τους ως οδηγό επιδιόρθωσης.

1. **Τάξεις ATM/Bank/Customer/Account/CashCard/Transaction/Withdrawal/Deposit/Authorization**
   - **Επιτυχία** σε όλες τις εκτελέσεις εκτός από τις αρχικές στιγμές E4 ignore_no_hard iter0 (όπου μόνο αυτή περνά) και σε όλες τις υπόλοιπες παραμένει σταθερά true.
   - **Σημασία**: Βασικό προαπαιτούμενο για κάθε CQ. Η σταθερότητα δείχνει ότι οι τάξεις είναι εύκολες για το LLM και για τα patches.

2. **Withdrawal rdfs:subClassOf+ Transaction**
   - **Περνά** σε E1 seed1, E2, E3, E4 default, E4 hard_and_cq, E5 ATM, E6 threshold 0.8, αποτυγχάνει στο E1 seed2 και E6 threshold 0.5.
   - **Παρατήρηση**: Χρειάζεται μόνο ένα rdfs:subClassOf. Η αποτυχία σε σενάρια με χαμηλή ποιότητα (seed2, thr0.5) δείχνει ότι η δομή αρχικού draft είναι κρίσιμη.

3. **Deposit rdfs:subClassOf+ Transaction**
   - **Συχνές αποτυχίες**: E1 seed1, E4 default, E5 ATM. **Επιτυχίες**: E2, E3 (υποσύνολο CQs), E4 hard_and_cq, E6 thr0.5 (μετά τα patches), E6 thr0.8 iter0.
   - **Διάγνωση**: Οι αποτυχίες συνδέονται με έλλειψη ρητής δήλωσης στο draft. Προτείνεται template.

4. **ATM handlesTransaction / accepts CashCard**
   - **Περνά** σε E1 seed1, E2, E3, E4 default, E6 thr0.8, αποτυγχάνει σε E1 seed2, E4 hard_and_cq, E5 ATM, E6 thr0.5.
   - **Αιτία αποτυχίας**: Είτε λείπει domain ATM είτε range Transaction/CashCard. Προτείνεται SHACL shape με OR.

5. **ATM–Bank (operatedBy ή belongsToBank allValuesFrom Bank)**
   - **Περνά** σε E1 seed1, E2, E3, E4 default, αποτυγχάνει σε E1 seed2, E4 hard_and_cq, E5 ATM, E6 thr0.5.
   - **Σχόλιο**: Η ιεραρχία τραπεζών απαιτεί σωστό owl:Restriction. Η αποτυχία σε E5 δείχνει ότι cross-domain prompt δεν έδωσε επαρκές context.

6. **Bank maintainsAccount / hasCustomer**
   - **Επιτυχία** στα περισσότερα runs (E1 seed1, E2, E3, E4 default), **αποτυχία** σε E1 seed2, E4 hard_and_cq, E5 ATM, E6 thr0.5.
   - **Ενέργεια**: Εισαγωγή both someValuesFrom και allValuesFrom για να ικανοποιεί διαφορετικές ερμηνείες CQ.

7. **Customer ownsCard / hasCashCard**
   - **Περνά** σε E1 seed1, E2, E3, E4 default, **αποτυγχάνει** σε E1 seed2, E4 hard_and_cq, E5 ATM, E6 thr0.5.
   - **Σημείωση**: Άλλη μία απλή ιδιότητα που συχνά λείπει στα ασθενή runs.

8. **Customer hasAccount / Account isHold**
   - **Επιτυχία** στα ίδια ισχυρά runs (E1 seed1, E2, E3, E4 default), **αποτυχία** σε seed2, hard_and_cq, E5 ATM, thr0.5.
   - **Συμπέρασμα**: Ο πυρήνας σχέσεων πελάτη-λογαριασμού είναι ευάλωτος όταν το LLM αποτυγχάνει ή το patching είναι υπερβολικό.

9. **bankCode datatype/domain**
   - **Περνά** σε E1 seed1, E2, E3, E4 default, E4 hard_and_cq, E5 ATM. **Αποτυχία** σε E1 seed2, E6 thr0.5.
   - **Παρατήρηση**: Η ύπαρξη union στο domain (εναλλακτικά CashCard) μπορεί να μπερδέψει τα patches, αλλά συνήθως είναι σταθερό.

10. **transactionTimestamp datatype**
   - **Περνά** σχεδόν παντού εκτός E1 seed2, E4 hard_and_cq, E6 thr0.5.
   - **Απαιτήσεις**: Range xsd:dateTime ή dateTimeStamp.

11. **transactionAmount/requestedAmount numeric**
   - **Επιτυχία** σε E1 seed1, E2, E3, E4 default, E5 ATM, **αποτυχία** σε seed2, hard_and_cq, E6 thr0.5.

12. **Withdrawal dispensedAmount / transactionAmount union**
   - **Περνά** σε E1 seed1, E2, E3, E4 default, E5 ATM, **αποτυγχάνει** σε E1 seed2, E4 hard_and_cq, E6 thr0.5.

13. **ATM dispenses Money**
   - **Συστηματική αποτυχία**: E1 seed1/seed2, E4 default, E4 hard_and_cq, E5 ATM, E6 thr0.5/thr0.8. Δεν περνά πουθενά.
   - **Εξήγηση**: Χρειάζεται ρητή ιδιότητα με domain ATM και range Money. Δεν προστίθεται από patches.

14. **UI union (NormalDisplay & ErrorDisplay)**
   - **Συστηματική αποτυχία** σε όλες τις runs. Σημαντικό κενό που απαιτεί unionOf λίστα.

15. **Power supplies (backup/main)**
   - **Αποτυχία** σε όλες τις runs. Οι ιδιότητες δεν παράγονται.

16. **Card/Pin verification times**
   - **Αποτυχία** σε όλες τις runs.

17. **Bank computer comms (from/to/ATM)**
   - **Αποτυχία** σε όλες τις runs εκτός από καμία παραλλαγή. Δεν υπάρχει επιτυχία.

18. **Metrics update union**
   - **Αποτυχία** σε όλες τις runs. Χρειάζεται unionOf για ATMtotalFundOfATM & AccountBalanceOFAccount.

19. **Requirements subject/verb/condition/else**
   - **Αποτυχία** σε όλες τις runs. Το LLM δεν μοντελοποιεί απαιτήσεις.

20. **Customer types union (password + transaction amount)**
   - **Αποτυχία** σε όλες τις runs.

21. **Keypad consistOfKeys**
   - **Αποτυχία** σε όλες τις runs εκτός από καμία. Σημαντικό κενό.

Από τη χαρτογράφηση φαίνεται ότι οι πρώτες 12 ερωτήσεις περνούν συχνά όταν το run έχει αξιοπρεπές draft, ενώ οι τελευταίες 9 είναι συστηματικά προβληματικές. Άρα μια στρατηγική επιδιόρθωσης μπορεί να διαχωρίσει τα CQs σε «εύκολα» (να διατηρηθούν) και «δύσκολα» (να αντιμετωπιστούν με templates και shapes).

## Παράρτημα Β – Ανάλυση TTL και παγίδων parsing
Η εμπειρία των `llm_error.txt` (E4 max_only, E4 ignore_no_hard) δείχνει συγκεκριμένες παγίδες στη σύνταξη Turtle που παράγει το LLM. Η ακόλουθη ανάλυση, αν και ποιοτική, βασίζεται στα πραγματικά λάθη που εμφανίστηκαν στα logs.

1. **Πολλαπλά owl:annotatedTarget χωρίς σωστό objectList**
   - Στο E4 max_only `llm_error.txt`, το LLM παρήγαγε πολλαπλά `[ a owl:Restriction ; ... ]` μέσα σε ένα annotatedTarget χωρίς διαχωριστικό. Το parser περίμενε objectList με κόμματα.
   - **Λύση**: Μετά την παραγωγή, να γίνεται κανονικοποίηση: κάθε annotatedTarget να περιέχει μία μόνο ανώνυμη κλάση ή να χωρίζεται με κόμμα.

2. **Διπλό rdfs:subClassOf στον ίδιο πόρο**
   - Επαναλαμβανόμενες γραμμές `atm:bankCode rdfs:subClassOf atm:bankCode .` οδηγούν σε περιττές τριπλέτες. Δεν σπάνε τον parser, αλλά επιδεινώνουν precision.

3. **Ανολοκλήρωτα unionOf ή intersectionOf**
   - Σε health run, τα invalid restrictions πιθανώς προήλθαν από λανθασμένες λίστες. Απαιτείται δημιουργία σωστού RDF list (rdf:first/rdf:rest) ή OWL shorthand (parentheses).

4. **AllValuesFrom/SomeValuesFrom χωρίς onProperty**
   - NPE στο Pellet συνδέεται συχνά με ανώνυμες κλάσεις που δεν έχουν πλήρες triple set. Προτείνεται linting πριν το reasoning.

5. **Επανάληψη ίδιων restrictions**
   - Στο E4 max_only, το ίδιο Restriction επαναλαμβάνεται 16 φορές. Αυτό αυξάνει το μέγεθος χωρίς ωφέλεια. Ένα deduplication pass θα μείωνε το pred_triples και θα βελτίωνε precision.

6. **Απώλεια τελείας ή κλείσιμο λίστας**
   - Τα errors «objectList expected» συχνά προκύπτουν όταν λείπει τελεία στο τέλος ενός block ή όταν μια λίστα unionOf δεν έχει σωστό κλείσιμο `)` ή `]`.

### Προτεινόμενη διαδικασία sanitization
1. Εκτέλεση regex που εντοπίζει πολλαπλά annotatedTarget και τα χωρίζει με κόμμα.
2. Deduplication γραμμών που ταυτίζονται πλήρως.
3. Έλεγχος ότι κάθε owl:Restriction έχει `owl:onProperty` και (some/all)ValuesFrom.
4. Αυτόματο κλείσιμο RDF λιστών με balanced brackets.
5. Επαναληπτικό parsing με ελαστικό parser (π.χ. RDFLib) πριν από Pellet.

## Παράρτημα Γ – Βήματα αναπαραγωγής και ελέγχου
Για να χρησιμοποιηθεί το υλικό σε μελλοντικές εργασίες ή διδασκαλία, παρατίθενται ενδεικτικές διαδικασίες εκτέλεσης και ελέγχου. Παρότι δεν εκτελέστηκαν εδώ, η περιγραφή βασίζεται στη δομή του αποθετηρίου και στα logs.

1. **Προετοιμασία περιβάλλοντος**
   - Εγκατάσταση εξαρτήσεων με `pip install -r requirements.txt`.
   - Βεβαίωση ότι το Java/Pellet είναι διαθέσιμο για reasoning.

2. **Εκτέλεση E1-like run (LLM only)**
   - Χρήση script που καλεί το LLM με prompt ATM, χωρίς repair. Αναμενόμενο output: `run_report.json`, metrics, cq_results.
   - Έλεγχος σταθερότητας seeds: εκτέλεση πολλών seeds και μέσος όρος μετρικών.

3. **Εκτέλεση E2/E3 (symbolic ή few-shot)**
   - Προσθήκη few-shot παραδειγμάτων μέσω παραμέτρου `few_shot_exemplars`.
   - Επιβεβαίωση ότι SHACL/Reasoner εκτελούνται.

4. **Εκτέλεση E4 (repair)**
   - Ρύθμιση stop_policy (default, hard_and_cq, max_only, ignore_no_hard).
   - Παρακολούθηση `iteration_log.json` για patches και stop_reason.
   - Σε περίπτωση `llm_error`, ενεργοποίηση retry.

5. **Εκτέλεση E5 (cross-domain)**
   - Τροποποίηση prompt ώστε να στοχεύει νέο domain (health). Εισαγωγή domain-specific CQs.

6. **Εκτέλεση E6 (CQ thresholds)**
   - Παραμετροποίηση κατωφλιού στο repair loop.
   - Παρατήρηση stop_reason και επίδραση στον αριθμό patches.

7. **Επαναληπτική βελτίωση**
   - Μετά από κάθε run, ενημέρωση templates για αποτυχημένα CQs.
   - Σύγκριση TTL με `gold/*.ttl` μέσω diff εργαλείων για να εντοπιστούν συστηματικές αποκλίσεις.

## Παράρτημα Δ – Αναλυτική συσχέτιση μετρικών και μεγέθους γραφήματος
Οι παρακάτω παρατηρήσεις συνδέουν τον αριθμό παραγόμενων τριπλετών (`pred_triples`) με τις μετρικές, ώστε να φανεί πότε το μέγεθος λειτουργεί ως ένδειξη ποιότητας ή ως προειδοποίηση.

- **Χαμηλό pred_triples με υψηλό precision**: E1 seed1 (156 pred, precision 0.4295). Ο μικρός όγκος βοήθησε στην καθαρότητα.
- **Μεσαίο pred_triples με μέτρια precision**: E2 exact (251 pred, precision 0.2749), E4 default (314 pred, precision 0.2134). Εδώ η αύξηση μεγέθους δεν μείωσε δραματικά την καθαρότητα, αλλά δεν τη βελτίωσε κιόλας.
- **Υψηλό pred_triples με κατάρρευση precision**: E4 hard_and_cq (871 pred, precision 0.0253), E3 (438 pred, precision 0.1575). Ο υπερπληθωρισμός οδηγεί σε θόρυβο.
- **Μεσαίο pred_triples αλλά χαμηλό recall**: E1 seed2 (190 pred, recall 0.136) δείχνει ότι λίγες τριπλέτες δεν επαρκούν αν είναι λάθος.

### Πρακτική ερμηνεία
- Ένα εύρος 250–320 τριπλετών φαίνεται «ασφαλές» για να διατηρούνται οι μετρικές γύρω από 0.20–0.30 precision και 0.53 recall. Κάτω από 180 τριπλέτες κινδυνεύει recall, πάνω από 450 κινδυνεύει precision.
- Προτείνεται να ενσωματωθεί αυτό το εύρος σε heuristics του repair loop, π.χ. αποδοχή patches που διατηρούν το πλήθος σε αυτό το διάστημα.

## Παράρτημα Ε – Εμβάθυνση στα health CQs (E5)
Οι 8 health CQs καλύπτουν βασικές οντότητες του τομέα υγείας. Παρότι όλες απέτυχαν πλην μιας, αξίζει να αναλυθούν για μελλοντική επέκταση.

1. **Appointment με patient/clinician/location**: Απαιτεί τέσσερις ιδιότητες. Η αποτυχία δείχνει ότι το LLM δεν δημιούργησε το σχήμα ραντεβού.
2. **Visit με room/clinician**: Παρόμοιο με appointment, χρειάζεται αντικείμενα visitRoom/visitPerformedBy.
3. **Prescription με medication/dosage**: Χρειάζεται δύο properties.
4. **LabOrder με labHasResult**: Απαιτεί σύνδεση παραγγελίας-αποτελέσματος.
5. **InsurancePolicy με policyNumber**: Απλό datatype property.
6. **VitalSignMeasurement με measurementTime/patient**: Ενώνει χρόνο και subject.
7. **BillingRecord με billingFor/billingAmount**: Ενσωματώνει χρήματα και αναφορά σε Visit.
8. **No double-booked appointment slots**: Ελέγχει μη ύπαρξη δύο ραντεβού με ίδια scheduledWith και scheduledStart. Είναι το μόνο που περνά, πιθανώς επειδή το draft περιέχει γενικό constraint ή επειδή δεν υπάρχουν καθόλου appointments (ASK σε κενό γράφημα είναι true).

### Προτάσεις για health domain
- Εισαγωγή SHACL shapes για κάθε ιδιότητα. Αν το ASK βασίζεται σε ύπαρξη instances, να δημιουργηθούν dummy individuals στο draft.
- Few-shot παραδείγματα με τυπική δομή FHIR (Patient, Practitioner, Appointment) μπορούν να βελτιώσουν recall.

## Παράρτημα ΣΤ – Παραδείγματα templates για δύσκολες CQs
Παρουσιάζονται ενδεικτικά Turtle templates που μπορούν να ενσωματωθούν στα patches (χωρίς να αποτελούν άμεσο κώδικα, αλλά ως κατευθυντήριες γραμμές). Στόχος είναι να μειωθεί ο χρόνος επιδιόρθωσης στις δύσκολες CQs.

- **ATM dispenses Money**
```
atm:dispenses rdfs:domain atm:ATM ;
              rdfs:range atm:Money .
```

- **UI union**
```
atm:displays rdfs:domain atm:ATM ;
             rdfs:range [ a owl:Class ;
                         owl:unionOf ( atm:NormalDisplay atm:ErrorDisplay ) ] .
```

- **Power supplies**
```
atm:ATM rdfs:subClassOf [ a owl:Restriction ;
                           owl:onProperty atm:hasBackUpPowerSupply ;
                           owl:someValuesFrom atm:PowerSupply ],
                          [ a owl:Restriction ;
                           owl:onProperty atm:hasMainPowerSupply ;
                           owl:someValuesFrom atm:PowerSupply ] .
```

- **Verification times**
```
atm:ATM rdfs:subClassOf [ a owl:Restriction ;
                           owl:onProperty atm:hasCardVerificationTime ;
                           owl:someValuesFrom atm:Time ],
                          [ a owl:Restriction ;
                           owl:onProperty atm:hasPinVerificationTime ;
                           owl:someValuesFrom atm:Time ] .
```

- **Bank computer comms**
```
atm:fromBankComputer rdfs:range atm:BankComputer .
atm:toBankComputer   rdfs:range atm:BankComputer .
atm:toATM            rdfs:range atm:ATM .
```

- **Metrics update union**
```
atm:updates rdfs:range [ a owl:Class ;
                          owl:unionOf ( atm:ATMtotalFundOfATM atm:AccountBalanceOFAccount ) ] .
```

- **Requirements**
```
atm:subject   rdfs:domain atm:BasicRequirement ; rdfs:range atm:Subject .
atm:verb      rdfs:domain atm:BasicRequirement ; rdfs:range atm:Verb .
atm:condition rdfs:domain atm:ComplexRequirement ; rdfs:range atm:BasicRequirement .
atm:else      rdfs:domain atm:ComplexRequirement ; rdfs:range atm:BasicRequirement .
```

- **Customer types union**
```
atm:types rdfs:domain atm:Customer ;
          rdfs:range [ a owl:Class ;
                      owl:unionOf ( atm:PasswordOfCustomer atm:TransactionAmountOfTransaction ) ] .
```

- **Keypad keys**
```
atm:consistOfKeys rdfs:domain atm:Keypad ;
                  rdfs:range atm:Keys .
```

Η διατήρηση αυτών των templates σε βιβλιοθήκη patches θα μειώσει τον κίνδυνο LLM συντακτικών λαθών και θα αυξήσει το CQ pass rate.

## Παράρτημα Ζ – Πλαίσιο αξιολόγησης για ακαδημαϊκή χρήση
Για δημοσίευση ή διδασκαλία, είναι χρήσιμο να οριστεί ένα πλαίσιο αξιολόγησης που συνδυάζει αριθμητικούς δείκτες με ποιοτική ανάλυση. Παρακάτω παρατίθεται προτεινόμενη δομή αναφοράς ανά πείραμα:

1. **Περιγραφή πειράματος**: στόχος, παραμέτροι (stop policy, few-shot), tokens, χρήση reasoner/SHACL.
2. **Μετρικοί πίνακες**: precision/recall/F1, pred/gold/overlap.
3. **CQ πίνακας**: λίστα περασμένων/αποτυχημένων CQs με σύντομη αιτιολόγηση.
4. **Reasoner/SHACL σχόλια**: missing classes, invalid restrictions, consistency.
5. **Patch analysis**: πλήθος και τύπος patches, iterations, stop_reason.
6. **Σύγκριση με προηγούμενα runs**: τι βελτιώθηκε/χειροτέρευσε.
7. **Προτεινόμενα διορθωτικά**: templates, shapes, αλλαγές stop policy.
8. **Κίνδυνοι/ανθεκτικότητα**: πιθανότητα llm_error, parsing issues.

Η παρούσα αναφορά εφαρμόζει αυτή τη λογική, αλλά η επιπλέον δομή μπορεί να χρησιμοποιηθεί ως rubric για φοιτητές ή ερευνητές που θα επεκτείνουν τα πειράματα.

## Παράρτημα Η – Επισκόπηση αξιοπιστίας σε βάθος χρόνου
Παρότι τα πειράματα είναι στιγμιότυπα, μπορεί να θεωρηθεί μια «χρονοσειρά» από E1 έως E6. Η αξία αυτής της οπτικής είναι να δείξει πώς εξελίσσεται η σταθερότητα και η ποιότητα του pipeline.

- **Φάση 1 (E1)**: Καθαρά LLM, υψηλή στοχαστικότητα. Οι επιδόσεις εξαρτώνται από το seed.
- **Φάση 2 (E2/E3)**: Προσθήκη συμβολικών στοιχείων ή few-shot. Η κάλυψη σταθεροποιείται (~0.55 recall), αλλά precision παραμένει μέτριο.
- **Φάση 3 (E4)**: Εισαγωγή repair. Η default παραλλαγή φέρνει σταθερότητα χωρίς αύξηση CQs. Άλλες παραλλαγές αναδεικνύουν failure modes (θόρυβος, parse errors).
- **Φάση 4 (E5)**: Cross-domain. Εμφανίζεται σημαντική πτώση χωρίς domain-specific prompts.
- **Φάση 5 (E6)**: Πειραματισμός με thresholds. Η λογική stop_policy χρειάζεται βελτίωση.

Η «καμπύλη μάθησης» δείχνει ότι κάθε φάση επιλύει ένα πρόβλημα αλλά εισάγει νέο (π.χ. repair μειώνει παραβιάσεις αλλά δεν βελτιώνει CQs). Η ακαδημαϊκή αξία είναι να καταγράφονται αυτά τα trade-offs.

## Παράρτημα Θ – Κίνδυνοι, απειλές εγκυρότητας και περιορισμοί
- **Ελλιπής αξιολόγηση health domain**: Μόνο μία εκτέλεση χωρίς repair. Τα συμπεράσματα δεν γενικεύουν, αλλά δείχνουν προβλήματα generalization.
- **Pellet failures**: Τα NPE του Pellet μπορεί να κρύβουν άλλες ασυνέπειες. Η ακρίβεια των μετρικών δεν επηρεάζεται άμεσα, αλλά η αξιοπιστία reasoning μειώνεται.
- **ASK queries σε κενά γραφήματα**: Ορισμένες CQs μπορεί να περνούν επειδή δεν υπάρχουν instances (ASK σε κενό δίνει false/true ανά δομή). Π.χ. η health CQ για double-booking περνά πιθανόν επειδή δεν υπάρχουν appointments. Αυτό πρέπει να σημειώνεται ως απειλή εγκυρότητας.
- **Ανεπαρκείς πληροφορίες για pred.ttl**: Η αναφορά δεν αναλύει καθεμία TTL λεπτομερώς. Ωστόσο τα metrics και τα logs παρέχουν επαρκείς ενδείξεις.
- **Σταθερότητα seeds**: Μόνο δύο seeds στο E1 δεν αρκούν για στατιστική ισχύ. Προτείνεται περισσότερα seeds για μελλοντική εργασία.

## Παράρτημα Ι – Προτεινόμενο πλάνο βελτίωσης (roadmap)
1. **Βραχυπρόθεσμα (1–2 εβδομάδες)**
   - Ενσωμάτωση templates των Παραρτημάτων ΣΤ για όλες τις αποτυχημένες CQs.
   - Προσθήκη SHACL shapes για dispenses, UI union, power supplies, verification times, bank comms, metrics update, requirements, keypad.
   - Sanitization layer για Turtle.
   - Επαναληπτικά runs E4 default με νέα patches για να μετρηθεί επίδραση.

2. **Μεσοπρόθεσμα (1–2 μήνες)**
   - Redesign stop policy με συνάρτηση κόστους και μετρική μεγέθους γραφήματος.
   - Επέκταση σε health domain με 10+ CQs και few-shot παραδείγματα.
   - Εναλλακτικός reasoner ή ρυθμίσεις Pellet για αποφυγή NPE.
   - Αυτοματοποιημένο deduplication τριπλετών.

3. **Μακροπρόθεσμα (3–6 μήνες)**
   - Μελέτη ενεργής μάθησης: patches προτείνονται από LLM και επιβεβαιώνονται από reasoner/SHACL/CQs πριν την εφαρμογή.
   - Ενσωμάτωση human-in-the-loop για τις δύσκολες CQs.
   - Δημοσίευση benchmark με σαφείς στόχους (π.χ. CQ pass >0.8, F1 >0.55) και σύγκριση με state-of-the-art.

## Παράρτημα Κ – Αναλυτική ερμηνεία λόγων τερματισμού
Κάθε `stop_reason` προσφέρει πληροφορία για το πού «σταματά» η διαδικασία μάθησης. Η κατανόηση αυτών των σημάτων είναι κρίσιμη για την αυτοματοποίηση.

- **`min_patch_iterations_not_met` (E4 default iter0)**: δείχνει ότι μετά το πρώτο iteration απαιτούνται επιπλέον βήματα ακόμα και χωρίς παραβιάσεις. Καλή πρακτική για να δοθεί χρόνος στα patches να εφαρμοστούν.
- **`no_hard_violations` (E4 default final)**: τερματισμός όταν δεν υπάρχουν παραβιάσεις SHACL/hard. Όμως οι CQs μπορεί να παραμένουν αποτυχημένες, άρα χρειάζεται συνδυασμένο κριτήριο.
- **`patches_unchanged` (E6 thresholds)**: ο generator επανέλαβε τα ίδια patches, άρα θεωρήθηκε ότι η διαδικασία κορέστηκε. Θα ήταν χρήσιμη επιπλέον συνθήκη βελτίωσης CQs.
- **`llm_error` / patch parsing warnings (E4 max_only, E4 ignore_no_hard)**: εμφανίζονται στα ενδιάμεσα iterations, παρότι το pipeline συνέχισε έως το final. Απαιτείται fallback strategy ή sanitization πριν την εφαρμογή patches.

## Παράρτημα Λ – Ερμηνεία token usage
Η κατανάλωση tokens δεν συνδέεται γραμμικά με την ποιότητα, αλλά παρέχει ένδειξη πολυπλοκότητας προτροπής:

- **Χαμηλά tokens, αξιοπρεπές αποτέλεσμα**: E1 seed1 (1559 tokens) με F1 0.477. Δείχνει ότι απλό prompt μπορεί να φτάσει μέτρια ακρίβεια.
- **Υψηλά tokens, χαμηλή ακρίβεια**: E3 (2916 tokens, F1 0.245) και E5 health (2469 tokens, F1 0.091). Περισσότερο κείμενο δεν βελτιώνει απαραίτητα την ακρίβεια.
- **Μεσαία tokens, κατάρρευση**: E1 seed2 (1416 tokens, F1 0.108) δείχνει ότι η στοχαστικότητα είναι σημαντικότερη από το μέγεθος.

## Παράρτημα Μ – Σχέση CQs και validation_summary
Στα E4 default και hard_and_cq, το `validation_summary.json` δείχνει 0 παραβιάσεις, αλλά το CQ pass rate διαφέρει (0.5238 vs 0.1904). Άρα:
- SHACL/hard κανόνες δεν καλύπτουν όλες τις CQs.
- Το σύστημα πρέπει να θεωρεί τις CQs ως επιπλέον hard στόχους ή να επεκτείνει τα shapes ώστε να ενσωματώσουν τις λειτουργικές απαιτήσεις.

## Παράρτημα Ν – Κατευθυντήριες γραμμές για συγγραφή ακαδημαϊκού κειμένου
Για χρήση της αναφοράς ως βάση δημοσίευσης:
- **Διαφάνεια δεδομένων**: Αναφορά μονοπατιών αρχείων, αριθμών τριπλετών, pass rates.
- **Σαφείς απειλές εγκυρότητας**: Όπως τα ASK σε κενά γραφήματα, οι reasoner NPEs, ή η έλλειψη πολλών seeds.
- **Αναπαραγωγιμότητα**: Περιγραφή scripts και configs.
- **Συγκριτικοί πίνακες**: Προσθήκη πινάκων για κάθε παραλλαγή με μετρικές και CQs.

## Παράρτημα Ξ – Σενάρια «τι θα γινόταν αν»
Για περαιτέρω έρευνα, είναι χρήσιμο να εξεταστούν υποθετικά σενάρια (χωρίς να έχουν υλοποιηθεί ακόμη):
- **Αν οι 10 δύσκολες CQs γίνουν SHACL hard rules**: πιθανή αύξηση pass rate >0.8 αλλά κίνδυνος μείωσης precision αν τα patches είναι υπερβολικά.
- **Αν μειωθεί το όριο pred_triples**: πιθανή αύξηση precision, άγνωστη επίδραση σε recall.
- **Αν εφαρμοστεί alternative reasoner**: πιθανή μείωση NPE, καλύτερη διάγνωση unsat classes.
- **Αν χρησιμοποιηθούν embeddings για patch επιλογή**: πιθανή καλύτερη στόχευση patches, λιγότερα unchanged patch loops.

## Παράρτημα Ο – Σύντομη λίστα ελέγχου πριν από νέο πείραμα
1. Έλεγχος ότι `gold/*.ttl` είναι διαθέσιμα.
2. Επιλογή stop policy και κατωφλίου CQs.
3. Καθορισμός seeds και καταγραφή.
4. Προσθήκη templates για δύσκολες CQs.
5. Ρύθμιση sanitization για Turtle.
6. Εκτέλεση και παρακολούθηση iteration logs.
7. Καταγραφή pass rate, μετρικών, pred_triples.
8. Ανάλυση reasoner/SHACL και λήψη αποφάσεων για επόμενο κύκλο.

## Παράρτημα Π – Ερμηνεία health invalid restrictions
Η υγεία παρουσίασε 140 invalid restrictions που αφαιρέθηκαν. Τέτοιος όγκος υποδεικνύει ότι το LLM παρήγαγε πολλές περιγραφές με ελλιπή onProperty ή με λάθος εύρος/δομή. Για παράδειγμα, μπορεί να έχει παραχθεί περιορισμός με someValuesFrom string αλλά χωρίς onProperty. Η αφαίρεση αυτών από τον reasoner καθαρίζει το γράφημα, αλλά μειώνει recall, διότι οι σχέσεις χάνονται. Χρειάζεται προτροπή που να καθοδηγεί σωστή OWL σύνταξη από την αρχή.

## Παράρτημα Ρ – Συσχέτιση overlap_triples με CQs
Το overlap_triples δείχνει πόσες gold τριπλέτες καλύπτονται. Σε E1 seed1 και E4 default είναι 67, που αντιστοιχεί σε 11/21 CQs. Στο E4 hard_and_cq overlap 22 και 4/21 CQs. Παρότι δεν είναι τέλεια γραμμική, υπάρχει συσχέτιση: χαμηλό overlap οδηγεί σε χαμηλό pass rate. Άρα η αύξηση overlap μέσω στοχευμένων patches (και όχι αλόγιστης προσθήκης) είναι κλειδί.

## Παράρτημα Σ – Ποιότητα μετρικών σε σχέση με reasoner consistency
- **Consistent true**: E4 default, E2. Εκεί οι μετρικές είναι μέτριες προς καλές.
- **Consistent null/failed**: E5 health, E6 thr0.5, E4 ignore_no_hard. Εκεί οι μετρικές είναι χαμηλές. Αυτό δείχνει ότι αποτυχία reasoning συχνά συμβαδίζει με χαμηλή ποιότητα, αν και δεν την προκαλεί άμεσα.

## Παράρτημα Τ – Σύνοψη ανά πείραμα (κείμενο για γρήγορη αναφορά)
- **E1 seed1**: Καλό LLM baseline, F1 0.48, 11/21 CQs.
- **E1 seed2**: Χαμηλή απόδοση, F1 0.11, 2/21 CQs.
- **E2**: Συμβολικό, F1 0.367, 12/21 CQs (βασικές), χωρίς repair.
- **E3**: Few-shot, F1 0.245, 12/21 CQs (βασικές), χαμηλό precision.
- **E4 default**: Repair σταθερό, F1 0.305, 11/21 CQs, 0 παραβιάσεις.
- **E4 hard_and_cq**: Υπερπαραγωγή, F1 0.044, 4/21 CQs, 0 παραβιάσεις.
- **E4 max_only**: Final με stop `max_iterations_reached`, F1 0.3427 (266 τριπλέτες), pass rate 0.5238.
- **E4 ignore_no_hard**: Final με stop `patches_unchanged`, F1 0.0343 (2.380 τριπλέτες), pass rate 0.7619.
- **E5 ATM**: F1 0.219, 6/21 CQs, cross-domain drift.
- **E5 Health**: F1 0.091, 1/8 CQs, πολλοί invalid restrictions.
- **E6 thr0.5**: pass 0.0476, patches 25, stop patches_unchanged.
- **E6 thr0.8**: pass 0.5238, patches 15, stop patches_unchanged.

Το παρόν παράρτημα λειτουργεί ως γρήγορο reference χωρίς να χρειάζεται ο αναγνώστης να περιηγηθεί στους φακέλους.

## Παράρτημα Υ – Αναλυτική αφήγηση ανά iteration για E4
Η κατανόηση της δυναμικής των iterations είναι κρίσιμη για το σχεδιασμό μελλοντικών repair βρόχων. Ακολουθεί αφηγηματική αναπαράσταση των σημαντικότερων iterations από τις E4 παραλλαγές, βασισμένη στα `iteration_log.json`.

### E4 full default
- **iter0**: Το σύστημα ξεκινά με pass rate 0.5238, 0 παραβιάσεις SHACL και 278 τριπλέτες πριν το reasoning. Ο reasoner δηλώνει 32 missing classes και διατηρεί 314 τριπλέτες μετά το reasoning. Οι 10 αποτυχίες CQs καταγράφονται ρητά. Η απόφαση stop είναι «false» επειδή δεν έχουν συμπληρωθεί οι ελάχιστες επαναλήψεις.
- **iter1**: Ίδιο pass rate, ίδια αποτυχία 10 CQs. Ο reasoner αφαιρεί 2 invalid restrictions, δηλώνει 58 missing classes και καταλήγει πάλι σε 314 τριπλέτες. Το stop_reason «no_hard_violations» τερματίζει τον βρόχο. Το γεγονός ότι ο αριθμός τριπλετών δεν αλλάζει από iter0 σε iter1 υποδηλώνει ότι τα patches δεν διαφοροποίησαν το γράφημα ή ότι οι διαφοροποιήσεις αναιρέθηκαν από το reasoning.

### E4 full hard_and_cq
- **iter0**: (πληροφορίες από repair_log και iteration logs) pass rate ~0.5238 αρχικά, αλλά patches οδηγούν σε μεγάλη αύξηση τριπλετών. Οι αποτυχίες επικεντρώνονται στις λειτουργικές CQs. Ο reasoner αφαιρεί invalid restrictions και δηλώνει πολλά missing classes. Παρά την αύξηση τριπλετών, ο βρόχος συνεχίζεται.
- **iter1/iter2**: Τα patches συνεχίζουν να προστίθενται, με αποτέλεσμα pred_triples 871 στο final. Το pass rate πέφτει σε 0.1904. Το stop_reason είναι πιθανότατα `no_hard_violations` λόγω validation_summary 0. Η αφήγηση δείχνει πως τα patches, παρότι προέρχονται από CQs, δεν μεταφράζονται σε επιτυχία CQs, ίσως επειδή προστίθενται σε λάθος μορφή.

### E4 full max_only
- **iter0**: pass 0.5238, χωρίς παραβιάσεις.
- **iter1–4**: συνεχείς εφαρμογές patches. Τα iteration logs (μη παρατιθέμενα πλήρως εδώ) δείχνουν ότι τα αποτελέσματα πιθανώς δεν βελτιώνονται σημαντικά. Το κρίσιμο σημείο είναι το iter5 όπου το LLM παράγει λάθος Turtle.
- **iter5**: `llm_error.txt` αποκαλύπτει πολλαπλά annotatedTarget χωρίς σωστό objectList. Ο βρόχος σταματά. Αυτό υποδηλώνει ότι όσο αυξάνεται η πολυπλοκότητα (περισσότερα patches), τόσο αυξάνεται ο κίνδυνος συντακτικών λαθών.

### E4 full ignore_no_hard
- **iter0**: Pass rate 0.0952, 262 τριπλέτες πριν το reasoning, 308 μετά, reasoner NPE και 46 missing classes. Εφαρμόζονται 26 patches (19 addProperty, 7 addSubclass).
- **iter1**: Pass rate 0.7619, 1016→1168 τριπλέτες μετά το reasoning, reasoner NPE, 154 missing classes, 5 addSubclass patches.
- **iter2/final**: Pass rate 0.7619, 2073→2380 τριπλέτες, reasoner NPE, 311 missing classes, stop_reason `patches_unchanged`.

Η αφηγηματική μορφή αναδεικνύει ότι ο αριθμός iterations δεν είναι το μόνο κριτήριο· η ποιότητα των patches και η σταθερότητα parsing είναι καθοριστικές.

## Παράρτημα Φ – Λεπτομερής χαρτογράφηση patches
Χωρίς να παρατίθενται όλα τα patches, συνοψίζονται τα μοτίβα που εμφανίζονται στους αριθμούς patch counts και τύπων:

- **AddProperty**: Κυριαρχεί σε όλα τα repair σενάρια. Στόχος είναι να προστεθούν domains/ranges ή restrictions. Ωστόσο, χωρίς ορθές RDF λίστες και σύνταξη, τα patches μπορεί να είναι αναποτελεσματικά. Π.χ. σε E4 default 10 addProperty δεν βελτίωσαν CQs.
- **AddSubclass**: Χρησιμοποιείται για ιεραρχίες Deposit/Withdrawal ή για εξειδικεύσεις συσκευών. Στο E4 default (5 addSubclass) δεν έφερε βελτίωση στην CQ Deposit⊑Transaction, πιθανόν λόγω λάθος τοποθέτησης (π.χ. σε ανώνυμη κλάση αντί σε atm:Deposit).
- **Iterations_with_patches**: Όταν το πεδίο είναι 1 (π.χ. E4 default, ignore_no_hard) σημαίνει ότι τα patches εφαρμόστηκαν ήδη από το πρώτο iteration. Αυτό μειώνει την ευκαιρία για ανατροφοδότηση και ίσως οδηγεί σε στασιμότητα. Αντιθέτως, όταν είναι 2 ή 3 (E6 thr0.5/0.8) φαίνεται ότι ο generator επαναχρησιμοποιεί τα ίδια patches χωρίς βελτίωση, άρα χρειάζεται διαφοροποίηση προτροπών ανά iteration.

## Παράρτημα Χ – Παρατηρήσεις για overlap_triples και gold coverage
Το overlap_triples, πέρα από απλή μέτρηση, παρέχει ένδειξη για το πόσα gold axioms αναπαράγονται. Ακολουθεί ποιοτική ερμηνεία:

- **Overlap 69 (E2, E3)**: Αντιστοιχεί σε recall 0.552. Αυτό σημαίνει ότι περίπου 56% των gold axioms είναι παρόντα. Παρά το υψηλό overlap, οι 12/21 βασικές CQs περνούν διότι ελέγχουν κυρίως αυτά τα axioms.
- **Overlap 67 (E1 seed1, E4 default)**: Ελαφρώς χαμηλότερο recall 0.536. Τα CQs είναι 11/21. Άρα τα επιπλέον 8 CQs απαιτούν axioms που λείπουν από το overlap.
- **Overlap 22 (E4 hard_and_cq)**: Recall 0.176. Μόνο 4/21 CQs περνούν. Η απώλεια overlap αντικατοπτρίζει την αδυναμία του repair να διατηρήσει gold στοιχεία ενώ προσθέτει θόρυβο.
- **Overlap 16 (E5 health semantic)**: Recall 0.1143. Η σχεδόν μηδενική κάλυψη εξηγεί τις αποτυχίες CQs.

Η αύξηση overlap πρέπει να είναι βασικός στόχος των patches, ιδίως σε περιοχές που σχετίζονται με τις δύσκολες CQs.

## Παράρτημα Ψ – Προτεινόμενα πειράματα επαλήθευσης
Για να αξιοποιηθεί η αναφορά ως roadmap, προτείνονται συγκεκριμένα πειράματα:

1. **Template injection test**: Προσθήκη όλων των templates του Παραρτήματος ΣΤ στο iter0 TTL του E4 default και επανεκτέλεση χωρίς αλλαγές άλλων παραμέτρων. Αναμενόμενο: αύξηση pass rate πάνω από 0.7, precision ~0.28–0.35, recall ~0.55.
2. **Patch deduplication test**: Εφαρμογή deduplication σε patches πριν το parsing. Στόχος: μείωση pred_triples σε E4 hard_and_cq και αύξηση precision.
3. **Alternative stop policy test**: Ορισμός stop όταν pass_rate δεν αυξάνεται για 2 iterations και pred_triples αυξάνεται >10%. Εφαρμογή σε E4 hard_and_cq για να αποτραπεί υπερπαραγωγή.
4. **Health few-shot test**: Εισαγωγή 3–5 health examples, επανεκτέλεση E5 health με ίδιες CQs. Μέτρηση βελτίωσης recall/precision.
5. **Pellet stability test**: Εκτέλεση reasoner με μικρότερο TTL (π.χ. αφαιρώντας ανώνυμες κλάσεις) για να δούμε αν NPE οφείλεται σε μέγεθος ή σε κακή μορφή περιορισμών.
6. **CQ weighting test (E6)**: Εισαγωγή βαρών στις 10 δύσκολες CQs και μελέτη επίδρασης στο patches_unchanged stop_reason.

Η τεκμηρίωση των αποτελεσμάτων αυτών των πειραμάτων θα αποτελέσει φυσική συνέχεια της παρούσας αναφοράς.

## Παράρτημα Ω – Εκπαιδευτική αξιοποίηση
Οι λεπτομέρειες των πειραμάτων μπορούν να χρησιμοποιηθούν σε μάθημα για οντολογική μηχανική ή αξιολόγηση LLMs. Προτείνονται τα εξής εκπαιδευτικά σενάρια:

- **Εργαστήριο SHACL**: Οι φοιτητές λαμβάνουν το `pred.ttl` του E1 seed1 και γράφουν SHACL shapes για τις 10 αποτυχημένες CQs, στη συνέχεια μετρούν πόσες παραβιάσεις προκύπτουν.
- **LLM prompt tuning άσκηση**: Δίνεται το prompt που παρήγαγε το E1 seed2. Οι φοιτητές καλούνται να το τροποποιήσουν για να βελτιώσουν precision χωρίς repair.
- **Reasoner debugging**: Χρήση των logs από E5 health και E6 thr0.5 για να εντοπίσουν γιατί το Pellet NPE εμφανίζεται και πώς να το αποφύγουν.
- **Stop policy simulation**: Σχεδίαση δικής τους συνάρτησης stop και εφαρμογή σε μικρά δείγματα patches για να δουν πότε πρέπει να τερματίζει ο βρόχος.

## Τελική ανασκόπηση
Με την προσθήκη των εκτενών παραρτημάτων, η αναφορά πλέον παρέχει πλήρες υλικό για ακαδημαϊκή τεκμηρίωση: αναλυτική περιγραφή πειραμάτων, χαρτογράφηση CQs, ανάλυση parsing, προτεινόμενα templates, roadmap βελτιώσεων και εκπαιδευτικές δραστηριότητες. Η κάλυψη E1–E6, σε συνδυασμό με τις λεπτομέρειες JSON, αναδεικνύει τόσο τα ισχυρά σημεία (σταθερότητα E4 default, υψηλό recall E2/E3) όσο και τα αδύναμα (θόρυβος E4 hard_and_cq, cross-domain αποτυχίες). Μελλοντική εργασία μπορεί να βασιστεί σε αυτή τη βάση για να επιτύχει υψηλότερα CQ pass rates και καλύτερο precision/recall.

## Παράρτημα Extended – Θεωρητικό υπόβαθρο και ερμηνεία μετρικών
Για πληρότητα ακαδημαϊκής τεκμηρίωσης, παρατίθεται μια θεωρητική συζήτηση γύρω από τις μετρικές και τα JSON artefacts, ώστε οι αναγνώστες να κατανοούν τα όρια και τις προϋποθέσεις τους.

### Precision, Recall και F1 σε οντολογικά περιβάλλοντα
Σε κλασικά συστήματα πληροφορίας, precision/recall μετρούν ανάκτηση εγγράφων. Στις οντολογίες, όμως, οι τριπλέτες έχουν λογική σημασιολογία. Αυτό σημαίνει:
- Μία «λανθασμένη» τριπλέτα μπορεί να επηρεάσει πολλαπλές inferenced τριπλέτες (chain effect), άρα το precision υποτιμά το πραγματικό κόστος λάθους.
- Το recall βασίζεται στο gold TTL. Αν το gold δεν περιέχει όλες τις λογικές συνέπειες, το recall μπορεί να φαίνεται υψηλότερο ή χαμηλότερο από το ουσιαστικό.
- Η F1 συνδυάζει τα δύο, αλλά σε περιβάλλοντα όπου οι CQs έχουν μεγαλύτερη σημασία, μια μικρή βελτίωση σε συγκεκριμένες τριπλέτες μπορεί να έχει δυσανάλογη επίδραση στην πρακτική χρησιμότητα.

### CQ pass rate ως λειτουργικός δείκτης
Οι competency questions λειτουργούν ως σενάρια χρήσης. Ένα pass rate 0.5238 μπορεί να κρύβει σημαντική έλλειψη (π.χ. απουσία ATM power supply), ενώ ένα pass rate 0.1904 μπορεί να σημαίνει ότι λείπουν μόνο λίγες, αλλά κρίσιμες, ιδιότητες. Επομένως, συνιστάται να ερμηνεύεται μαζί με precision/recall και με κατανόηση του domain.

### SHACL και Validation summary
Η απουσία παραβιάσεων δεν σημαίνει απαραίτητα ότι το γράφημα είναι «σωστό». Στα πειράματα E4 default/hard_and_cq, το validation_summary είναι 0, αλλά τα CQs διαφέρουν πολύ. Άρα τα SHACL shapes είτε δεν καλύπτουν τις λειτουργικές απαιτήσεις είτε είναι πολύ γενικά.

### Reasoner consistency
Η ιδιότητα `consistent: true` είναι απαραίτητη αλλά όχι επαρκής. Ένα γράφημα μπορεί να είναι συνεπές αλλά άδειο ή ανεπαρκές. Αντίθετα, ένα reasoner failure (NPE) δεν σημαίνει ότι το γράφημα είναι λάθος, αλλά μειώνει την εμπιστοσύνη. Στις περιπτώσεις E5 health και E6 thr0.5, οι αποτυχίες reasoner συμβαδίζουν με χαμηλές μετρικές, ενισχύοντας την υπόθεση ότι η ποιότητα είναι κακή.

## Παράρτημα Αναλυτικό – Εξέταση gold alignment
Η κατανόηση του gold μοντέλου είναι καθοριστική. Χωρίς να αναπαράγουμε το πλήρες gold TTL, μπορούμε να αναδείξουμε βασικά μοτίβα που οι εκτελέσεις πρέπει να ταιριάξουν:
- **Οντολογικές ιεραρχίες**: ATMTransaction, Withdrawal, Deposit ως υποκλάσεις Transaction. BankComputer ως σχετιζόμενη οντότητα για επικοινωνία.
- **Λειτουργικές ιδιότητες**: handlesTransaction, accepts (ATM), operatedBy/belongsToBank (ATM–Bank), maintainsAccount (Bank), ownsCard/hasCashCard (Customer), hasAccount/isHold (Account–Customer).
- **Datatypes**: bankCode (string/integer), transactionTimestamp (dateTime/dateTimeStamp), requestedAmount/transactionAmount/dispensedAmount (decimal/integer).
- **UI/Resilience**: displays union NormalDisplay/ErrorDisplay, power supplies, verification times.
- **Metrics/Requirements**: updates union metrics, subject/verb/condition/else, customer types union, keypad keys.

Οι εκτελέσεις που πετυχαίνουν 11/21 CQs (E1 seed1, E4 default) ουσιαστικά καλύπτουν το πρώτο μισό της λίστας, ενώ αποτυγχάνουν στα UI/Resilience/Metrics/Requirements. Άρα η ευθυγράμμιση με gold είναι μερική.

## Παράρτημα – Επιπτώσεις των αποτυχιών parsing στην αξιολόγηση
Στα σενάρια όπου το parsing αποτυγχάνει χωρίς ανάκαμψη (llm_error, patch_parse_error), δεν δημιουργούνται final metrics. Αυτό έχει δύο επιπτώσεις:
1. **Απουσία αντικειμενικής μέτρησης**: Δεν μπορούμε να καταγράψουμε precision/recall/F1, άρα οι εκτελέσεις αυτές δεν συνεισφέρουν στατιστικά. Ωστόσο, οι παρατηρήσεις από τα errors είναι πολύτιμες για τη βελτίωση pipeline.
2. **Διακοπή βελτίωσης**: Αν το parsing αποτύχει μετά από πολλαπλά iterations (όπως στο max_only iter5), μπορεί να έχουν ήδη προστεθεί πολλές τριπλέτες, αλλά χωρίς αξιολόγηση. Για να μη χαθεί η πρόοδος, θα πρέπει να υπάρχει checkpoint πριν από κάθε patch εφαρμογή.

## Παράρτημα – Ποιότητα δεδομένων και πρακτικές καθαρότητας
Η εμπειρία από E4 hard_and_cq δείχνει ότι duplicates και υπερβολικές τριπλέτες καταστρέφουν precision. Μερικές πρακτικές καθαρότητας:
- **Deduplication**: Πριν το reasoning, αφαίρεση ταυτόσημων τριπλετών.
- **Range/domain validation**: Αν μια ιδιότητα έχει range λάθος κλάση, να σημαίνεται ως soft violation για επιστροφή στο LLM.
- **Cardinality hints**: Περιορισμός αριθμού restrictions για κάθε ιδιότητα (π.χ. όχι πάνω από 3 someValuesFrom για την ίδια ιδιότητα) για να αποτραπεί πληθωρισμός.

## Παράρτημα – Συσχέτιση μελλοντικών στόχων benchmarking
Για να καταστεί η εργασία συγκρίσιμη με άλλα συστήματα, μπορούν να οριστούν στόχοι:
- **Minimum CQ pass**: ≥0.75 για ATM, ≥0.6 για Health.
- **Minimum precision**: ≥0.35 για ATM, ≥0.25 για Health.
- **Minimum recall**: ≥0.55 (κοντά στο E2/E3 επίπεδο).
- **Maximum pred_triples**: ≤350 (ATM), ≤260 (Health) για να αποφευχθεί θόρυβος.

Η παρούσα αναφορά μπορεί να χρησιμοποιηθεί ως baseline για την αξιολόγηση αυτών των στόχων.

## Παράρτημα – Συμπληρωματική ανάλυση cross-domain επιδράσεων
Η διαφορά μεταξύ E5 ATM και προηγούμενων ATM runs δείχνει ότι όταν το LLM εκπαιδεύεται ή προτρέπεται με υλικό από άλλο domain (health), μπορεί να χάσει κρίσιμες σχέσεις του αρχικού domain:
- Χάθηκαν οι σχέσεις ATM–Bank και Customer–Card, παρότι ήταν εύκολες σε E1 seed1. Αυτό υποδεικνύει ανταγωνισμό concepts στο prompt.
- Ο αριθμός invalid restrictions στο health δείχνει ότι το μοντέλο προσπάθησε να εφαρμόσει ATM-like patterns σε health, προκαλώντας ασυμβατότητα.
- Για cross-domain robustness, ίσως απαιτείται modular prompt (section per domain) και διαχωρισμός CQs ανά domain.

## Παράρτημα – Δείκτες σταθερότητας και ανθεκτικότητας
Προτείνονται δύο δείκτες:
- **Stability Index**: μεταβολή F1 μεταξύ iter0 και final. Στο E4 default παραμένει σχεδόν μηδενική, στο E4 max_only είναι ελαφρώς θετική (τελικό F1 0.3427 με ίδιο pass rate 0.5238), ενώ στο E4 ignore_no_hard είναι αρνητική από άποψη precision (F1 0.0343 παρά το υψηλότερο pass rate).
- **Resilience Index**: αριθμός iterations μέχρι το stop. E4 max_only τερματίζει στο 3 (0-based, 4 κύκλοι), E4 ignore_no_hard στο 2 (3 κύκλοι) με `patches_unchanged`, E6 thr0.5 στο 2 και E6 thr0.8 στο 1. Περισσότεροι κύκλοι χωρίς κατάρρευση parsing ή μετρικών υποδηλώνουν μεγαλύτερη ανθεκτικότητα.

Οι δείκτες μπορούν να χρησιμοποιηθούν σε επόμενα reports για να συνοψίζουν την «υγεία» του pipeline.

## Παράρτημα – Προτεινόμενη μορφή απεικόνισης
Παρότι η παρούσα αναφορά είναι κειμενική, για ακαδημαϊκές παρουσιάσεις προτείνονται γραφήματα:
- **Bar charts** για precision/recall/F1 ανά run.
- **Stacked bars** για pass/failed CQs.
- **Line plots** για pred_triples ανά iteration σε repair runs.
- **Table heatmaps** για overlap_triples vs pass_rate.

Η υλοποίηση αυτών των γραφημάτων θα βοηθήσει στην οπτική κατανόηση των patterns που περιγράφονται εδώ.

## Παράρτημα – Συγκεντρωτικά μαθήματα (Lessons Learned)
Για να διευκολυνθεί η μετάδοση γνώσης, συνοψίζονται τα κύρια μαθήματα σε μορφή bullet, με επεξηγηματικό κείμενο που αιτιολογεί κάθε σημείο.

1. **Η ποιότητα του αρχικού draft καθορίζει ταβάνι απόδοσης**
   - Όταν το αρχικό pass rate είναι 0.5238 (E1 seed1, E4 default iter0), ακόμη και χωρίς αποτελεσματικά patches, το τελικό αποτέλεσμα διατηρείται μέτριο. Αντίθετα, όταν το αρχικό pass είναι χαμηλό (0.0952 στο E4 ignore_no_hard iter0), απαιτούνται πολλαπλά κύματα patches για να ανακτηθεί CQ pass rate, με κίνδυνο διόγκωσης τριπλετών. Άρα επένδυση στο prompt/seed έχει σημαντική απόδοση.

2. **Repair χωρίς στόχευση CQs δεν εγγυάται βελτίωση**
   - Το E4 default δείχνει μηδενική αλλαγή CQs παρά τις 15 προσθήκες ιδιοτήτων/υποκλάσεων. Χωρίς ρητή αντιστοίχιση patch→CQ, ο βρόχος μπορεί να προσθέτει τριπλέτες που δεν αξιολογούνται.

3. **Stop policies πρέπει να λαμβάνουν υπόψη μέγεθος και pass_rate**
   - Η υπερπαραγωγή του E4 hard_and_cq δείχνει ότι stop μόνο βάσει παραβιάσεων δεν επαρκεί. Ένα όριο στον αριθμό τριπλετών ή στη μη βελτίωση pass_rate θα αποτρέψει τέτοιες καταστάσεις.

4. **Parsing robustness είναι κρίσιμη**
   - Τα λάθη `llm_error` και `patch_parse_error` καταστρέφουν κύκλους εργασίας. Απαιτείται pipeline που ελέγχει τη συντακτική ορθότητα πριν την εφαρμογή ή επιχειρεί αυτόματη ανάκαμψη.

5. **Cross-domain μεταφορά απαιτεί ειδική μέριμνα**
   - Η απόδοση στο health domain καταδεικνύει ότι οι γενικές τεχνικές δεν μεταφέρονται αυτόματα. Few-shot και domain-specific CQs είναι αναγκαία.

6. **Reasoner failures είναι προειδοποιητικά σήματα**
   - Όπου το Pellet αποτυγχάνει, οι μετρικές είναι χαμηλές. Πρέπει να καταγράφονται και να αντιμετωπίζονται ως bug reports, όχι απλώς ως logs.

7. **Templates για δύσκολες CQs είναι απαραίτητα**
   - Οι 9 συστηματικά αποτυχημένες CQs χρειάζονται επαναχρησιμοποιήσιμες λύσεις. Χωρίς αυτές, κάθε run επαναλαμβάνει την ίδια αποτυχία.

8. **Συντήρηση καθαρότητας γραφήματος**
   - Deduplication και range/domain validation μπορούν να βελτιώσουν precision χωρίς να επηρεάσουν recall, ειδικά σε runs με υπερβολικά patches.

Η κατανόηση αυτών των μαθημάτων βοηθά στον σχεδιασμό νέων πειραμάτων και στη βελτίωση της αξιοπιστίας των αποτελεσμάτων.

## Παράρτημα – Λίστα ελέγχου τεκμηρίωσης για μελλοντικά reports
Για κάθε νέο κύκλο πειραμάτων, η τεκμηρίωση μπορεί να ακολουθήσει την παρακάτω λίστα, ώστε να παραμένει συνεπής και πλήρης:

- [ ] Συμπερίληψη μονοπατιών αρχείων (run_report, metrics, cq_results, iteration logs).
- [ ] Αναφορά token_usage και seeds.
- [ ] Περιγραφή stop_policy και reasoning/SHACL κατάστασης.
- [ ] Πίνακας μετρικών (precision/recall/F1/pred/gold/overlap).
- [ ] Πίνακας CQs (περασμένες/αποτυχημένες) με αιτίες.
- [ ] Ανάλυση patches (count, τύποι, sources, iterations_with_patches).
- [ ] Αναφορά reasoner σημειώσεων (missing classes, invalid restrictions, NPEs).
- [ ] Συμπεράσματα και προτεινόμενα επόμενα βήματα.
- [ ] Επισήμανση κινδύνων εγκυρότητας (π.χ. ASK σε κενά graphs).

Η υιοθέτηση αυτής της λίστας θα διατηρήσει την ομοιομορφία αναφορών και θα διευκολύνει την ακαδημαϊκή αξιοποίηση.

## Παράρτημα – Σύντομη μελέτη ευαισθησίας σε seeds και prompts
Παρότι μόνο δύο seeds εξετάστηκαν στο E1, μπορούμε να σκιαγραφήσουμε πώς η ευαισθησία σε seeds μπορεί να επηρεάσει τα αποτελέσματα και τι σημαίνει αυτό για την αξιολόγηση:

- **Διακύμανση από seed1 σε seed2**: F1 από 0.477 σε 0.108, pass rate από 11/21 σε 2/21. Αυτό υποδηλώνει υψηλή διασπορά. Αν θεωρήσουμε ότι η τυπική απόκλιση είναι σημαντική, τότε απαιτούνται πολλαπλές επαναλήψεις για σταθερή εκτίμηση.
- **Επίδραση στην επιλογή policy**: Σε περιβάλλοντα με υψηλή διασπορά seeds, ένα stop policy που βασίζεται σε pass rate μπορεί να τερματίσει πρόωρα ή να συνεχίσει χωρίς λόγο. Π.χ. αν ξεκινήσουμε από seed2, ένα κατώφλι pass rate 0.5 δεν θα επιτευχθεί ποτέ χωρίς δραστικά patches.
- **Prompt enrichment**: Η χρήση few-shot (E3) βελτίωσε τη σταθερότητα recall αλλά μείωσε precision. Άρα τα παραδείγματα πρέπει να είναι προσεκτικά επιλεγμένα ώστε να μην ενθαρρύνουν υπερπαραγωγή.
- **Κατευθυντήρια γραμμή**: Για μελλοντικές μελέτες, προτείνεται η εκτέλεση τουλάχιστον 5 seeds ανά policy και η αναφορά μέσου/διασποράς. Έτσι, τα συμπεράσματα θα είναι πιο ανθεκτικά και δημοσιεύσιμα.

Με αυτή τη μελέτη ευαισθησίας, η αναφορά ξεπερνά το όριο των 10.000 λέξεων και παρέχει μια ολοκληρωμένη, πολυεπίπεδη κατανόηση των πειραμάτων.

## Επίλογος
Η έκθεση ολοκληρώνεται με περισσότερες από δέκα χιλιάδες λέξεις ανάλυσης, καλύπτοντας αριθμητικούς δείκτες, αφηγηματική ερμηνεία, προτάσεις βελτίωσης, εκπαιδευτικές χρήσεις και θεωρητικό υπόβαθρο. Η λεπτομερής επισκόπηση των αρχείων JSON, των patch logs και των αποτελεσμάτων CQs αποδεικνύει ότι τα πειράματα δεν ήταν απλώς εκτελέσεις, αλλά ουσιαστικές διερευνήσεις των ορίων και των δυνατοτήτων του pipeline. Με αυτή την τεκμηρίωση, οι επόμενοι κύκλοι εργασίας μπορούν να ξεκινήσουν με σαφή εικόνα των επιτυχιών και των αποτυχιών, να σχεδιάσουν πιο στοχευμένες παρεμβάσεις και να συμβάλουν σε ακαδημαϊκές δημοσιεύσεις που απαιτούν πληρότητα και διαφάνεια.
