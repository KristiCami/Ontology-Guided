import types
import openai
from llm_interface import LLMInterface


def test_generate_owl_with_mock(monkeypatch):
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