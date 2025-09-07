import json

from scripts.save_prompt_config import save_prompt_config


def test_save_prompt_config_includes_retrieval_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prompt = "demo prompt"
    dev_ids = ["1", "2"]
    hyperparams = {"model": "gpt", "temperature": 0.5}
    log_path = tmp_path / "log.json"
    save_prompt_config(
        prompt,
        dev_ids,
        hyperparams,
        use_retrieval=True,
        retrieve_k=7,
        retrieval_method="tfidf_cosine",
        prompt_log=log_path,
    )
    config_path = tmp_path / "results" / "prompt_config.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["use_retrieval"] is True
    assert data["retrieve_k"] == 7
    assert data["retrieval_method"] == "tfidf_cosine"
    assert data["prompt_log"].endswith("log.json")
