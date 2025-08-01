import builtins
from data_loader import DataLoader


def test_demo_txt_loading_and_preprocessing():
    loader = DataLoader()
    texts = loader.load_requirements(["demo.txt"])
    # Should load exactly one text from demo.txt
    assert len(texts) == 1
    sentences = []
    for t in texts:
        sentences.extend(loader.preprocess_text(t))
    assert sentences == [
        "The ATM must log every user transaction.",
        "The system shall notify the user on failure.",
    ]