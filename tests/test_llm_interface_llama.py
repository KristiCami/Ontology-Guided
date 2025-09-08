import sys
import types
import logging
import pytest

from ontology_guided.llm_interface import LLMInterface


def setup_fake_llama(monkeypatch, decode_output, *, error=None, calls=None):
    """Prepare fake torch and transformers modules for llama backend tests."""
    calls = calls or {"count": 0}

    # Fake torch module
    fake_torch = types.SimpleNamespace()
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)

    class NoGrad:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_torch.no_grad = lambda: NoGrad()
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    # Fake tokenizer and model
    class FakeInputIds(list):
        @property
        def shape(self):
            return (len(self),)

    class FakeBatch(dict):
        def to(self, device):
            return self

    class FakeTokenizer:
        def __call__(self, prompt, return_tensors=None):
            batch = FakeBatch()
            batch["input_ids"] = FakeInputIds([1, 2, 3])
            return batch

        def decode(self, tokens, skip_special_tokens=True):
            return decode_output

    class FakeModel:
        def to(self, device):
            return self

        def generate(self, **kwargs):
            calls["count"] += 1
            if error:
                raise error
            return [[1, 2, 3, 4, 5]]

    class FakeAutoTokenizer:
        @classmethod
        def from_pretrained(cls, model_name):
            return FakeTokenizer()

    class FakeAutoModel:
        @classmethod
        def from_pretrained(cls, model_name):
            return FakeModel()

    fake_transformers = types.SimpleNamespace(
        AutoTokenizer=FakeAutoTokenizer,
        AutoModelForCausalLM=FakeAutoModel,
    )
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    return calls


def test_llama_generate_owl_with_mock_and_cache(monkeypatch, tmp_path):
    decode_output = "@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."
    calls = setup_fake_llama(monkeypatch, decode_output, calls={"count": 0})

    llm = LLMInterface(
        api_key="dummy", model="fake", backend="llama", cache_dir=str(tmp_path)
    )
    result1 = llm.generate_owl(["same"], "{sentence}")
    result2 = llm.generate_owl(["same"], "{sentence}")

    assert result1 == result2 == [decode_output]
    assert calls["count"] == 1


def test_llama_generate_owl_exit_on_error(monkeypatch, tmp_path, caplog):
    calls = setup_fake_llama(
        monkeypatch, "", error=RuntimeError("boom"), calls={"count": 0}
    )
    sleep_calls = []
    monkeypatch.setattr(
        "ontology_guided.llm_interface.time.sleep", lambda s: sleep_calls.append(s)
    )

    llm = LLMInterface(
        api_key="dummy", model="fake", backend="llama", cache_dir=str(tmp_path)
    )

    with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError) as excinfo:
        llm.generate_owl(
            ["irrelevant"],
            "{sentence}",
            max_retries=2,
            retry_delay=1,
            max_retry_delay=2,
        )

    assert calls["count"] == 3
    assert sleep_calls == [1, 2]
    assert "LLM call failed" in caplog.text
    assert "after 2 retries" in str(excinfo.value)
