import openai
from typing import List

class LLMInterface:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        openai.api_key = api_key
        self.model = model

    def generate_owl(self, sentences: List[str], prompt_template: str) -> List[str]:
        """
        Παίρνει λίστα προτάσεων και ένα prompt template,
        επιστρέφει λίστα με raw Turtle/OWL strings.
        """
        results = []
        for sent in sentences:
            prompt = prompt_template.format(sentence=sent)
            resp = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            results.append(resp.choices[0].message.content)
        return results
