import openai
from ontology_guided.llm_interface import LLMInterface
import time
import logging
import pytest
import json

def test_generate_owl_with_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    # Fake response structure mimicking openai return
    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    def fake_create(*args, **kwargs):
        return FakeResponse("""```turtle
@prefix ex: <http://example.com/> .
ex:A ex:B ex:C .
```""")

    # Patch the OpenAI API call
    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result = llm.generate_owl(["irrelevant"], "{sentence}")
    assert result == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]


def test_generate_owl_adds_known_prefix(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    def fake_create(*args, **kwargs):
        # Returns Turtle using a known prefix without declaring it
        return FakeResponse("schema:Person a schema:Class .")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result = llm.generate_owl(["irrelevant"], "{sentence}")
    assert result == ["@prefix schema: <http://schema.org/> .\nschema:Person a schema:Class ."]


def test_generate_owl_exit_on_error(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    def fake_create(*args, **kwargs):
        raise openai.OpenAIError("boom")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError) as excinfo:
        llm.generate_owl(
            ["irrelevant"],
            "{sentence}",
            max_retries=3,
            retry_delay=1,
            max_retry_delay=2,
        )
    assert sleep_calls == [1, 2, 2]
    assert "LLM call failed" in caplog.text
    assert "after 3 retries" in str(excinfo.value)


def test_generate_owl_retry_then_success(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    calls = {"count": 0}

    def fake_create(*args, **kwargs):
        if calls["count"] == 0:
            calls["count"] += 1
            raise openai.OpenAIError("fail")
        return FakeResponse("""```turtle
@prefix ex: <http://example.com/> .
ex:A ex:B ex:C .
```""")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    with caplog.at_level(logging.WARNING):
        result = llm.generate_owl(["irrelevant"], "{sentence}", max_retries=2, retry_delay=0)
    assert result == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]
    assert "LLM call failed" in caplog.text


def test_generate_owl_with_terms(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    captured = {}

    def fake_create(*args, **kwargs):
        captured["system"] = kwargs["messages"][0]["content"]
        captured["user"] = kwargs["messages"][1]["content"]
        return FakeResponse("""@prefix ex: <http://example.com/> .\nex:A ex:prop ex:B .""")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    terms = {
        "classes": ["ex:Class"],
        "properties": ["ex:prop"],
        "domain_range_hints": {"ex:prop": {"domain": ["ex:A"], "range": ["ex:B"]}},
        "synonyms": {"ex:quick": "ex:fast"},
    }
    llm.generate_owl(["irrelevant"], "{sentence}", available_terms=terms)
    assert captured["user"] == "irrelevant"
    assert 'ex:Class' in captured['system']
    assert 'ex:prop' in captured['system']
    assert 'ex:prop domain ex:A' in captured['system']
    assert 'ex:quick -> ex:fast' in captured['system']


def test_generate_owl_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    calls = {"count": 0}

    def fake_create(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse("""@prefix ex: <http://example.com/> .\nex:A ex:B ex:C .""")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result1 = llm.generate_owl(["same"], "{sentence}")
    result2 = llm.generate_owl(["same"], "{sentence}")
    assert result1 == result2 == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]
    assert calls["count"] == 1


def test_cache_key_stable_with_permuted_terms(tmp_path):
    llm = LLMInterface(api_key="", backend="cache", cache_dir=str(tmp_path))
    sentence = "Test"
    terms_original = {
        "classes": ["ex:B", "ex:A"],
        "properties": ["ex:prop2", "ex:prop1"],
        "domain_range_hints": {
            "ex:prop2": {"domain": ["ex:B", "ex:A"], "range": ["ex:C"]},
            "ex:prop1": {"domain": ["ex:D"], "range": ["ex:E", "ex:F"]},
        },
        "synonyms": {"foo": "bar", "baz": "qux"},
    }
    llm._save_cache(sentence, terms_original, "http://example.com/#", "ex", "ttl")

    # Same content, different ordering to mimic non-deterministic term loaders
    terms_permuted = {
        "classes": ["ex:A", "ex:B"],
        "properties": ["ex:prop1", "ex:prop2"],
        "domain_range_hints": {
            "ex:prop1": {"range": ["ex:F", "ex:E"], "domain": ["ex:D"]},
            "ex:prop2": {"range": ["ex:C"], "domain": ["ex:A", "ex:B"]},
        },
        "synonyms": {"baz": "qux", "foo": "bar"},
    }
    cached = llm._load_cache(sentence, terms_permuted, "http://example.com/#", "ex")
    assert cached == "ttl"


def test_cache_loads_legacy_entries(tmp_path):
    llm = LLMInterface(api_key="", backend="cache", cache_dir=str(tmp_path))
    sentence = "Legacy"
    terms = {
        "classes": ["ex:A"],
        "properties": ["ex:p"],
        "domain_range_hints": {},
        "synonyms": {},
    }
    base = "http://example.com/#"
    legacy_path = LLMInterface._legacy_cache_file(
        tmp_path, sentence, terms, base, "ex"
    )
    legacy_path.write_text(json.dumps({"result": "old"}))
    value = llm._load_cache(sentence, terms, base, "ex")
    assert value == "old"
    canonical = llm._cache_file(sentence, terms, base, "ex")
    assert canonical.exists()

    # Minimal legacy caches (sentence+vocab) are also promoted.
    minimal_terms = {
        "classes": ["ex:B", "ex:A"],
        "properties": ["ex:p2", "ex:p1"],
        "domain_range_hints": {"ex:p1": {"domain": ["ex:A"]}},
        "synonyms": {"foo": "bar"},
    }
    minimal_path = LLMInterface._legacy_cache_file_minimal(
        tmp_path, sentence, minimal_terms, base, "ex"
    )
    minimal_path.write_text(json.dumps({"result": "minimal"}))
    promoted = llm._load_cache(sentence, minimal_terms, base, "ex")
    assert promoted == "minimal"
    assert llm._cache_file(sentence, minimal_terms, base, "ex").exists()


def test_cache_snippet_search(tmp_path):
    llm = LLMInterface(api_key="", backend="cache", cache_dir=str(tmp_path))
    sentence = "The ATM shall greet the customer"
    snippet_file = tmp_path / "snippet.json"
    snippet_file.write_text(
        json.dumps(
            {
                "result": "@prefix ex: <http://example.com/> .\n# The ATM shall greet the customer",
            }
        )
    )
    terms = {"classes": ["ex:ATM"], "properties": [], "domain_range_hints": {}, "synonyms": {}}
    cached = llm._load_cache(sentence, terms, "http://example.com/#", "ex")
    assert cached.startswith("@prefix ex:")


def test_generate_owl_retry_on_invalid_turtle(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    calls = {"count": 0}
    prompts = []

    def fake_create(*args, **kwargs):
        prompts.append(kwargs["messages"][1]["content"])
        if calls["count"] == 0:
            calls["count"] += 1
            return FakeResponse("ex:A ex:B ex:C .")
        return FakeResponse("""@prefix ex: <http://example.com/> .\nex:A ex:B ex:C .""")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result = llm.generate_owl(["irrelevant"], "{sentence}", max_retries=2, retry_delay=0)
    assert result == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]
    assert len(prompts) == 2
    assert "Previous output was invalid Turtle" in prompts[1]


def test_generate_owl_returns_empty_after_invalid_turtle(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    def fake_create(*args, **kwargs):
        return FakeResponse("ex:A ex:B ex:C .")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result = llm.generate_owl(["irrelevant"], "{sentence}", max_retries=1, retry_delay=0)
    assert result == [""]


def test_generate_owl_passes_temperature_and_examples(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    captured = {}

    def fake_create(*args, **kwargs):
        captured["temperature"] = kwargs.get("temperature")
        captured["messages"] = kwargs["messages"]
        return FakeResponse("@prefix ex: <http://example.com/> .\nex:A ex:B ex:C .")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    examples = [{"user": "Example", "assistant": "@prefix ex: <http://example.com/> ."}]
    llm = LLMInterface(
        api_key="dummy",
        model="gpt-4",
        cache_dir=str(tmp_path),
        temperature=0.3,
        examples=examples,
    )
    llm.generate_owl(["irrelevant"], "{sentence}")

    assert captured["temperature"] == 0.3
    assert captured["messages"][1] == {"role": "user", "content": "Example"}
    assert captured["messages"][2] == {
        "role": "assistant",
        "content": "@prefix ex: <http://example.com/> .",
    }
    assert captured["messages"][3]["role"] == "user"


def test_retrieval_logging(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    def fake_create(*args, **kwargs):
        return FakeResponse("@prefix ex: <http://example.com/> .\nex:A a ex:B .")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    dev_pool = [
        {"sentence_id": "1", "sentence": "quick brown fox"},
        {"sentence_id": "2", "sentence": "lazy dog"},
        {"sentence_id": "3", "sentence": "brown fox jumps"},
    ]

    log_path = tmp_path / "prompts.log"
    llm = LLMInterface(
        api_key="dummy",
        model="gpt-4",
        cache_dir=str(tmp_path / "cache"),
        use_retrieval=True,
        dev_pool=dev_pool,
        retrieve_k=2,
        prompt_log=log_path,
    )

    llm.generate_owl([
        {"text": "quick fox", "sentence_id": "T"}
    ], "{sentence}")

    data = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert data[0]["sentence_id"] == "T"
    assert set(data[0]["examples"]) == {"1", "3"}
