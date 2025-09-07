import json
import os
from typing import Iterable, Any, Dict


def save_prompt_config(prompt_text: str, dev_sentence_ids: Iterable[str], hyperparameters: Dict[str, Any]) -> None:
    """Persist prompt configuration to results/prompt_config.json."""
    os.makedirs("results", exist_ok=True)
    config = {
        "prompt": prompt_text,
        "dev_sentence_ids": list(dev_sentence_ids),
        "hyperparameters": hyperparameters,
    }
    with open(os.path.join("results", "prompt_config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
