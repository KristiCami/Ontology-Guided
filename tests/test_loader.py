import logging
import pytest

from ontology_guided.data_loader import DataLoader


def test_demo_txt_loading_and_preprocessing():
    loader = DataLoader()
    texts = list(loader.load_requirements(["demo.txt"]))
    assert len(texts) == 1
    sentences = []
    for t in texts:
        sentences.extend(loader.preprocess_text(t))
    assert sentences == [
        "The ATM must log all user transactions after card insertion.",
    ]


def test_load_requirements_warns_and_raises(tmp_path, caplog):
    loader = DataLoader()

    missing_file = tmp_path / "missing.txt"
    with caplog.at_level(logging.WARNING):
        texts = list(loader.load_requirements([str(missing_file)]))
    assert "does not exist" in caplog.text
    assert texts == []

    bad_file = tmp_path / "bad.pdf"
    bad_file.write_text("dummy")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        list(loader.load_requirements([str(bad_file)]))

