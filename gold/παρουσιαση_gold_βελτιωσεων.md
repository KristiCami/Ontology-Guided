# Παρουσίαση βελτιώσεων στα αρχεία gold

## 1. Επισκόπηση
Με βάση τις οδηγίες αξιολόγησης, ολοκληρώθηκαν στο gold δύο συμπληρωματικές παρεμβάσεις:
- Εμπλουτισμός του ontologίου `atm_gold.ttl` με δομικά κλειδώματα για τις βασικές συναλλαγές και με ξεκάθαρα αναγνωριστικά για τις κάρτες ATM.
- Ανακατασκευή του SHACL αρχείου `shapes_atm.ttl` ώστε να παρέχει αυστηρό αλλά και χρηστικό feedback για τις κρίσιμες οντότητες (Transactions, CashCards, ATMs).

## 2. Τι είναι ήδη εντός προδιαγραφών
- Έχουν δηλωθεί και τεκμηριωθεί όλες οι βασικές κλάσεις και ιεραρχίες (ATM, Bank/BankComputer, Customer, Account, CashCard, Transaction/Withdrawal/Deposit/BalanceInquiry, Authorization, Message).
- Οι βασικές object properties φέρουν σωστά domains/ranges για τα competency questions (performedBy, onAccount, usesCard, handlesTransaction κ.λπ.).
- Τα σημαντικά datatype properties είναι διαθέσιμα με κατάλληλους τύπους: requestedAmount, dispensedAmount, transactionTimestamp (functional), serialNumber, bankCode.

## 3. Σημεία που βελτιώθηκαν ουσιαστικά
### 3.1 Δομικοί περιορισμοί στις συναλλαγές
- Στις κλάσεις `Withdrawal`, `Deposit` και `BalanceInquiry` προστέθηκαν necessary conditions (owl:Restrictions) που εγγυώνται ότι κάθε συναλλαγή συνδέεται με Customer, Account και CashCard, και –όπου απαιτείται– με requested/dispensedAmount τύπου xsd:decimal.
- Το `transactionTimestamp` δηλώθηκε functional ώστε κάθε Transaction να έχει μοναδική χρονική σφραγίδα, βοηθώντας στα CQs και στα SHACL checks.

### 3.2 Ταυτότητα CashCard
- Τα `bankCode` και `serialNumber` έγιναν functional properties στο CashCard.
- Προστέθηκε OWL key `owl:hasKey ( atm:bankCode atm:serialNumber )`, διασφαλίζοντας μοναδικότητα κάρτας χωρίς επιπλέον ισοδυναμίες.

### 3.3 ATM ↔ Bank messaging
- Εισήχθη η κλάση `BankComputer` και τα ζεύγη ιδιοτήτων `sendsMessageTo` / `receivesMessageFrom` για να περιγραφεί ρητά ο δίαυλος επικοινωνίας ATM–Bank, καλύπτοντας σχετικά CQs.
- Οι `operatedBy` / `handlesTransaction` χρησιμοποιούνται συντονισμένα, εξασφαλίζοντας σταθερές απαντήσεις.

### 3.4 Συνέπεια ονοματολογίας
- Ελέγχθηκε ότι όλα τα ονόματα που αναφέρονται στα CQs υπάρχουν και στα δύο αρχεία (handlesTransaction, operatedBy, ownsCard, maintainsAccount, bankCode, transactionTimestamp, requestedAmount, dispensedAmount).

## 4. SHACL validation (shapes_atm.ttl)
### 4.1 WithdrawalShape
- Επιβάλλει ακριβώς έναν πελάτη, λογαριασμό και κάρτα ανά ανάληψη, καθώς και ύπαρξη/μη αρνητικότητα για requestedAmount και dispensedAmount (με literals τύπου "0"^^xsd:decimal).
- Παρέχει σαφή μηνύματα και severity `sh:Violation` για να γνωρίζει ο χρήστης τι λείπει.

### 4.2 PerTransactionLimitShape
- Soft policy (severity Warning) που ειδοποιεί όταν το requestedAmount υπερβαίνει το "1000"^^xsd:decimal, χωρίς να απορρίπτει τη συναλλαγή.

### 4.3 AuthorizationShape
- Όλα τα Transactions πρέπει να συνδέονται με `Authorization` και να έχουν `transactionTimestamp` τύπου xsd:dateTime (minCount 1). Εξασφαλίζει πλήρη audit trail.

### 4.4 CashCardShape & CashCardKeyShape
- Υποχρεώνει κάθε κάρτα να έχει ακριβώς ένα serialNumber και bankCode, καθώς και κάποιον κάτοχο (inverse ownsCard).
- Το πρόσθετο SPARQL constraint εγγυάται global uniqueness για το ζεύγος bankCode+serialNumber, συμπληρώνοντας τον OWL key μηχανισμό.

### 4.5 ATMShape
- Κάθε ATM οφείλει να έχει σχέση operatedBy με Bank, αλλιώς επιστρέφεται Violation.

## 5. Οφέλη για τα CQs
- Οι περιορισμοί στις Transactions εξασφαλίζουν ότι οι ερωτήσεις για «ποιος έκανε τι, σε ποιον λογαριασμό και με ποια κάρτα» απαντώνται χωρίς αμφισημία.
- Η λειτουργικότητα των bankCode/serialNumber και το OWL key επιτρέπουν αξιόπιστη ταυτοποίηση κάρτας σε downstream σενάρια ασφαλείας.
- Οι νέες SHACL shapes παρέχουν άμεσο feedback (με σαφή μηνύματα και severities) πριν τα δεδομένα περάσουν στο reasoner ή στη γραμμή παραγωγής.

## 6. Επόμενα βήματα (προαιρετικά)
- Εάν απαιτηθούν επιπλέον CQs για UI/Power/Timing, μπορούν να προστεθούν ελαφριές κλάσεις/ιδιότητες (π.χ. PowerSupply, hasMainPowerSupply) ακολουθώντας το ίδιο μοτίβο.
- Εξετάζεται η προσθήκη closed shapes σε κρίσιμους κόμβους για τον εντοπισμό άγνωστων ιδιοτήτων.

Με τις παραπάνω βελτιώσεις, τα αρχεία του φακέλου gold είναι πλήρως εναρμονισμένα με τις ανάγκες των competency questions και παρέχουν πιο αυστηρούς ελέγχους ποιότητας δεδομένων.
