import json
import os
from pathlib import Path
from typing import Iterable, Any, Dict, Optional, Union


def save_prompt_config(
    prompt_text: str,
    dev_sentence_ids: Iterable[str],
    hyperparameters: Dict[str, Any],
    *,
    use_retrieval: bool = False,
    retrieve_k: int = 0,
    retrieval_method: Optional[str] = None,
    prompt_log: Optional[Union[str, Path]] = None,
) -> None:
    """Persist prompt configuration to ``results/prompt_config.json``.

    Parameters
    ----------
    prompt_text:
        The prompt text used for generation.
    dev_sentence_ids:
        IDs of development sentences used as few-shot examples.
    hyperparameters:
        Mapping of additional hyperparameters such as temperature and model.
    use_retrieval:
        Whether retrieval-augmented prompting was enabled.
    retrieve_k:
        Number of examples retrieved when ``use_retrieval`` is ``True``.
    retrieval_method:
        Name of the retrieval method used to select examples, if any.
    prompt_log:
        Path to the prompt log file produced during generation, if any.
    """

    os.makedirs("results", exist_ok=True)
    config = {
        "prompt": prompt_text,
        "dev_sentence_ids": list(dev_sentence_ids),
        "hyperparameters": hyperparameters,
        "use_retrieval": use_retrieval,
        "retrieve_k": retrieve_k,
        "retrieval_method": retrieval_method,
        "prompt_log": str(prompt_log) if prompt_log is not None else None,
    }
    with open(os.path.join("results", "prompt_config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
