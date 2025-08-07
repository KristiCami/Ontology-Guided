import os
import logging
from typing import Iterable, Iterator, List
import spacy
from docx import Document  # pip install python-docx


def clean_text(text: str) -> str:
    """Καθαρίζει το κείμενο από περιττούς χαρακτήρες και πολλαπλά κενά."""
    cleaned = text.replace("\r", " ").replace("\n", " ")
    return " ".join(cleaned.split())


class DataLoader:
    """Κλάση για φόρτωση και προεπεξεργασία φυσικών γλώσσών απαιτήσεων."""

    def __init__(self, spacy_model: str = "en_core_web_sm", max_length: int = 2_000_000):
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            # Fallback to blank English model if not installed
            self.nlp = spacy.blank("en")
            self.nlp.add_pipe("sentencizer")
        # Increase the maximum allowed document length to handle large files
        self.nlp.max_length = max_length

    def load_text_file(self, file_path: str) -> Iterator[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                yield line

    def load_docx_file(self, file_path: str) -> str:
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)

    def load_requirements(self, input_paths: List[str]) -> Iterable[str]:
        for path in input_paths:
            if not os.path.exists(path):
                logging.warning("File %s does not exist and will be skipped", path)
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext == ".txt":
                yield from self.load_text_file(path)
            elif ext == ".docx":
                yield self.load_docx_file(path)
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

    def preprocess_text(
        self, text: str, batch_size: int = 100, n_process: int = 1
    ) -> List[str]:
        """Καθαρίζει το κείμενο και το επεξεργάζεται τμηματικά με το spaCy.

        Το κείμενο χωρίζεται σε γραμμές, καθαρίζεται και στη συνέχεια
        επεξεργάζεται με την ``nlp.pipe`` ώστε να αποφεύγεται η φόρτωση
        ολόκληρου του κειμένου στη μνήμη.
        """

        lines = (line for line in text.splitlines() if line.strip())
        cleaned_iter = (clean_text(line) for line in lines)
        sentences: List[str] = []
        for doc in self.nlp.pipe(cleaned_iter, batch_size=batch_size, n_process=n_process):
            sentences.extend(sent.text.strip() for sent in doc.sents)
        return sentences
