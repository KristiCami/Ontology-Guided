# Αναφορά υλοποίησης απαιτήσεων ATM (gold)

Το παρόν συνοψίζει σε ποια σημεία του κώδικα καλύπτονται οι απαιτήσεις της “General Guidance for Completing the Gold TTL” και οι πρόσθετες παρατηρήσεις βελτίωσης.

## Δομικό λεξιλόγιο (gold/atm_gold.ttl)
- **Μόνο δομικές κλάσεις, όχι ροές/καταστάσεις:** Περιλαμβάνονται μόνο οντότητες του κόσμου (ATM, Bank, BankComputer, Customer, Account, CashCard, Transaction, Withdrawal, Deposit, BalanceInquiry, Authorization, Message). Δεν υπάρχουν procedural/flow κλάσεις.  
- **Διαχωρισμός κλάσης–ατόμου:** Όλες οι οντότητες δηλώνονται ως κλάσεις (π.χ. Bank, BankComputer). Δεν μοντελοποιούνται συγκεκριμένα άτομα στον gold ορισμό.  
- **Σχέσεις και τιμές:** Χρησιμοποιούνται αντικειμενικές ιδιότητες για τους δεσμούς πελάτη/τραπέζης/κάρτας/λογαριασμού (maintainsAccount, hasAccount, ownsCard, handledBy ATM μέσω operatedBy και handlesTransaction, επικοινωνία sendsMessageTo/receivesMessageFrom). Τα ποσά και τα ids είναι τυποποιημένα ως xsd:decimal ή xsd:string.  
- **Αναγκαίοι περιορισμοί στα transactions:**  
  - Withdrawal ⊑ performedBy some Customer ⊓ onAccount some Account ⊓ usesCard some CashCard ⊓ requestedAmount some xsd:decimal ⊓ dispensedAmount some xsd:decimal.  
  - Deposit ⊑ performedBy some Customer ⊓ onAccount some Account ⊓ usesCard some CashCard ⊓ requestedAmount some xsd:decimal.  
  - BalanceInquiry ⊑ performedBy some Customer ⊓ onAccount some Account ⊓ usesCard some CashCard.  
  Οι περιορισμοί αυτοί υλοποιούν τα “core roles” και τις ποσότητες (βλ. atm_gold.ttl γραμμές 13–66).  
- **Λειτουργικές ιδιότητες & ταυτότητα κάρτας:** transactionTimestamp, bankCode και serialNumber είναι functional· επιπλέον εφαρμόζεται OWL hasKey (bankCode, serialNumber) για CashCard ώστε να διασφαλίζεται η μοναδικότητα ζεύγους (atm_gold.ttl γραμμές 118–142).

## SHACL έλεγχοι (gold/shapes_atm.ttl)
- **Αναλήψεις με ακριβείς συμμετέχοντες:** WithdrawalShape επιβάλλει exactly-1 performedBy/onAccount/usesCard (minCount=1, maxCount=1) και μη αρνητικά ποσά requestedAmount/dispensedAmount με minCount 1 και typed decimal literals ("0"^^xsd:decimal) (γραμμές 5–46).  
- **Πολιτική ορίου συναλλαγής (soft):** PerTransactionLimitShape ορίζει maxInclusive "1000"^^xsd:decimal με severity sh:Warning (γραμμές 48–56).  
- **Εξουσιοδότηση & χρονική σήμανση:** AuthorizationShape απαιτεί τουλάχιστον ένα Authorization και ένα transactionTimestamp τύπου xsd:dateTime, με Violation severities και μηνύματα (γραμμές 58–73).  
- **Κάρτες με ιδιοκτησία και μοναδικότητα:** CashCardShape επιβάλλει μοναδικό bankCode/serialNumber (min/maxCount 1), υποχρεωτική αντιστροφή ownsCard για τουλάχιστον έναν Customer, ενώ CashCardKeyShape προσθέτει SPARQL constraint για global uniqueness του (bankCode, serialNumber) (γραμμές 75–122).  
- **ATM ↔ Bank:** ATMShape απαιτεί operatedBy προς Bank (γραμμές 124–132).  
- **Σοβαρότητα/μηνύματα:** Όλες οι SHACL ιδιότητες φέρουν sh:severity (Violation ή Warning) και sh:message για καθαρό feedback.

## Σχήμα συμφραζομένων (gold/atm_schema_context.ttl)
- Παρέχει τον ίδιο κατάλογο κλάσεων/ιδιοτήτων με domain/range, χωρίς περιορισμούς ή instances, ώστε εργαλεία παραγωγής/ελέγχου να έχουν ελαφρύ context για prefixes και δομή.

## Κάλυψη πρόσθετων παρατηρήσεων
- **Cardinality = 1 σε core ρόλους & amounts:** Υλοποιείται στις SHACL ιδιότητες με minCount=1/maxCount=1 για performedBy/onAccount/usesCard και με minCount 1 για requestedAmount/dispensedAmount.  
- **usesCard στους ελέγχους Withdrawal:** Περιλαμβάνεται τόσο στο TBox (αναγκαίοι περιορισμοί) όσο και στο WithdrawalShape.  
- **Μη αρνητικά ποσά με τυποποιημένα literals:** minInclusive "0"^^xsd:decimal εφαρμόζεται σε requestedAmount και dispensedAmount.  
- **Περιορισμοί παραμέτρων (k, m, n, t):** Δεν μοντελοποιούνται ως οντότητες στο TBox· το μόνο soft όριο m (per transaction) εφαρμόζεται σε SHACL ως Warning.  
- **Αποφυγή ισοδυναμίας με αριθμητικές τιμές:** Δεν υπάρχουν owl:equivalentClass με αριθμητικές σταθερές.  
- **Μηνύματα/severity:** Όλα τα SHACL constraints περιέχουν sh:severity και sh:message.  
- **Closed shapes (προαιρετικό):** Δεν ενεργοποιούνται, αλλά η υπάρχουσα κάλυψη κρίσιμων ιδιοτήτων επιτυγχάνεται με explicit min/max counts.  
- **CQ/SHACL ονόματα & συνέπεια:** Όλα τα χρησιμοποιούμενα ονόματα (performedBy, onAccount, usesCard, requestedAmount, dispensedAmount, transactionTimestamp, bankCode, serialNumber, operatedBy, handlesTransaction) υπάρχουν στο gold TBox και στα shapes.
