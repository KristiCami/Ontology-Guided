import os
from dotenv import load_dotenv
from llm_interface import LLMInterface

# Φόρτωση .env μεταβλητών
load_dotenv()

# Ανάκτηση του API key
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    raise RuntimeError('Ρύθμισε την μεταβλητή περιβάλλοντος OPENAI_API_KEY στο .env')

# Δείγμα requirement
sample = [
    "The ATM must log every user transaction after card insertion."
]
# Prompt template για Turtle OWL
PROMPT = (
    "Convert the following requirement into OWL axioms in Turtle syntax:\n\n"
    "Requirement: {sentence}\n\nOWL:"
)

# Κλήση LLM
llm = LLMInterface(api_key=API_KEY)
outputs = llm.generate_owl(sample, PROMPT)

# Εκτύπωση στην οθόνη
print("=== LLM Output ===")
print(outputs[0])

# Αποθήκευση σε αρχείο
os.makedirs('results', exist_ok=True)
with open('results/llm_output.ttl', 'w', encoding='utf-8') as f:
    f.write(outputs[0])

print("Written results/llm_output.ttl")
