import openai
from ontology_guided.llm_interface import LLMInterface
import time

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


def test_generate_owl_exit_on_error(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    def fake_create(*args, **kwargs):
        raise openai.OpenAIError("boom")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)
    monkeypatch.setattr(time, "sleep", lambda *args, **kwargs: None)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result = llm.generate_owl(["irrelevant"], "{sentence}", max_retries=1, retry_delay=0)
    assert result == []


def test_generate_owl_retry_then_success(monkeypatch, tmp_path):
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
    result = llm.generate_owl(["irrelevant"], "{sentence}", max_retries=2, retry_delay=0)
    assert result == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]


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
        return FakeResponse("ex:A ex:B ex:C .")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    llm.generate_owl(["irrelevant"], "{sentence}", available_terms=(['ex:Class'], ['ex:prop']))
    assert 'ex:Class' in captured['prompt']
    assert 'ex:prop' in captured['prompt']


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
        return FakeResponse("ex:A ex:B ex:C .")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)

    llm = LLMInterface(api_key="dummy", model="gpt-4", cache_dir=str(tmp_path))
    result1 = llm.generate_owl(["same"], "{sentence}")
    result2 = llm.generate_owl(["same"], "{sentence}")
    assert result1 == result2 == ["ex:A ex:B ex:C ."]
    assert calls["count"] == 1
