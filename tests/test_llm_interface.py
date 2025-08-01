import types
import openai
from llm_interface import LLMInterface


def test_generate_owl_with_mock(monkeypatch):
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

    llm = LLMInterface(api_key="dummy", model="gpt-4")
    result = llm.generate_owl(["irrelevant"], "{sentence}")
    assert result == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]


def test_generate_owl_exit_on_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    def fake_create(*args, **kwargs):
        raise openai.OpenAIError("boom")

    monkeypatch.setattr(openai.chat.completions, "create", fake_create)
    monkeypatch.setattr("builtins.input", lambda *args: "n")

    llm = LLMInterface(api_key="dummy", model="gpt-4")
    result = llm.generate_owl(["irrelevant"], "{sentence}")
    assert result == []


def test_generate_owl_retry_then_success(monkeypatch):
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
    monkeypatch.setattr("builtins.input", lambda *args: "y")

    llm = LLMInterface(api_key="dummy", model="gpt-4")
    result = llm.generate_owl(["irrelevant"], "{sentence}")
    assert result == ["@prefix ex: <http://example.com/> .\nex:A ex:B ex:C ."]