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

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            # Fallback to blank English model if not installed
            self.nlp = spacy.blank("en")
            self.nlp.add_pipe("sentencizer")

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

    def preprocess_text(self, text: str) -> List[str]:
        cleaned = clean_text(text)
        doc = self.nlp(cleaned)
        return [sent.text.strip() for sent in doc.sents]
