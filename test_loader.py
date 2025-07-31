from data_loader import DataLoader

loader = DataLoader()
texts = loader.load_requirements(['demo.txt'])
sentences = []
for t in texts:
    sentences.extend(loader.preprocess_text(t))

print(f"Βρέθηκαν {len(sentences)} προτάσεις:")
for s in sentences:
    print(" -", s)
