import openai
from ontology_guided.llm_interface import LLMInterface
import time
import logging
import pytest

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
        captured["prompt"] = kwargs["messages"][1]["content"]
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
    assert 'ex:Class' in captured['prompt']
    assert 'ex:prop' in captured['prompt']
    assert 'domain ex:A' in captured['prompt']
    assert 'ex:quick -> ex:fast' in captured['prompt']


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


def test_generate_owl_raises_after_invalid_turtle(monkeypatch, tmp_path):
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
    with pytest.raises(ValueError):
        llm.generate_owl(["irrelevant"], "{sentence}", max_retries=1, retry_delay=0)
