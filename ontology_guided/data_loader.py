import os
import logging
import re
from typing import Iterable, Iterator, List
import spacy
from docx import Document  # pip install python-docx


def clean_text(text: str) -> str:
    """Καθαρίζει το κείμενο από bullets/λίστες, περιττούς χαρακτήρες και πολλαπλά κενά."""
    cleaned = re.sub(r"^\s*[\d\-\*]+[.)]?\s*", "", text)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
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

    def load_docx_file(self, file_path: str) -> Iterator[str]:
        """Yield each paragraph from a DOCX file as a separate line."""
        doc = Document(file_path)
        for para in doc.paragraphs:
            yield para.text

    def load_requirements(self, input_paths: List[str]) -> Iterable[str]:
        for path in input_paths:
            if not os.path.exists(path):
                logging.warning("File %s does not exist and will be skipped", path)
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext == ".txt":
                yield from self.load_text_file(path)
            elif ext == ".docx":
                yield from self.load_docx_file(path)
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

    def preprocess_text(
        self,
        text: str,
        batch_size: int = 100,
        n_process: int = 1,
        keywords: Iterable[str] | None = ("shall", "must", "should"),
    ) -> List[str]:
        """Καθαρίζει το κείμενο και το επεξεργάζεται τμηματικά με το spaCy.

        Το κείμενο χωρίζεται σε γραμμές, καθαρίζεται και στη συνέχεια
        επεξεργάζεται με την ``nlp.pipe`` ώστε να αποφεύγεται η φόρτωση
        ολόκληρου του κειμένου στη μνήμη.  Αν δοθεί λίστα ``keywords``
        τότε φιλτράρονται οι προτάσεις που τις περιέχουν.  Όταν
        ``keywords`` είναι ``None`` δεν εφαρμόζεται φιλτράρισμα βάσει
        λέξεων-κλειδιών.
        """

        lines = (line for line in text.splitlines() if line.strip())
        cleaned_iter = (clean_text(line) for line in lines)
        keyword_set = {k.lower() for k in keywords} if keywords is not None else None
        sentences: List[str] = []
        for doc in self.nlp.pipe(cleaned_iter, batch_size=batch_size, n_process=n_process):
            for sent in doc.sents:
                sent_text = sent.text.strip()
                tokens_lower = {token.text.lower() for token in sent}
                has_keyword = (
                    keyword_set is not None and any(k in tokens_lower for k in keyword_set)
                )
                has_verb = any(token.pos_ in {"VERB", "AUX"} for token in sent)
                if (
                    keyword_set is None
                    and not has_verb
                    and all(token.pos_ == "" for token in sent)
                ):
                    # spaCy model without POS tagger; do not filter by verbs
                    has_verb = True
                if has_keyword or has_verb:
                    sentences.append(sent_text)
        # Remove duplicates while preserving order
        return list(dict.fromkeys(sentences))
