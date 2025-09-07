from ontology_guided.exemplar_selector import select_examples


def test_select_examples_basic():
    sentence = "quick brown fox"
    dev_pool = [
        {"sentence_id": "1", "sentence": "quick fox"},
        {"sentence_id": "2", "sentence": "lazy dog"},
        {"sentence_id": "3", "sentence": "brown fox fast"},
    ]
    top = select_examples(sentence, dev_pool, 2)
    ids = {ex["sentence_id"] for ex in top}
    assert ids == {"1", "3"}
