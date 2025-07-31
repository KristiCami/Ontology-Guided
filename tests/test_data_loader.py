import pytest
from data_loader import DataLoader

def test_preprocess_text():
    loader = DataLoader()
    text = "The ATM logs transactions. Users withdraw cash."
    sentences = loader.preprocess_text(text)
    assert sentences == ["The ATM logs transactions.", "Users withdraw cash."]