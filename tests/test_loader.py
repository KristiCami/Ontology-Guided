from ontology_guided.data_loader import DataLoader


def test_demo_txt_loading_and_preprocessing():
    loader = DataLoader()
    texts = loader.load_requirements(["demo.txt"])
    assert len(texts) == 1
    sentences = []
    for t in texts:
        sentences.extend(loader.preprocess_text(t))
    assert sentences == [
        "The ATM must log all user transactions after card insertion, linking each transaction to the user who performed it."
    ]
