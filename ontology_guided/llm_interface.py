import openai
import httpx
from typing import List
import re


class LLMInterface:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        openai.api_key = api_key
        self.model = model

    def generate_owl(self, sentences: List[str], prompt_template: str) -> List[str]:
        """Καλεί το LLM και επιστρέφει μόνο το Turtle code."""
        results = []
        for sent in sentences:
            prompt = (
                "Return ONLY valid Turtle code, without any explanatory text or markdown fences."
                + "\n" + prompt_template.format(sentence=sent)
            )
            while True:
                try:
                    resp = openai.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a Turtle/OWL code generator."},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    break
                except (openai.OpenAIError, httpx.HTTPError) as e:
                    print(f"LLM call failed: {e}")
                    retry = input("Retry? (y/n): ").strip().lower()
                    if retry != "y":
                        print("Exiting gracefully.")
                        return results

            raw = resp.choices[0].message.content
            match = re.search(r"```turtle\s*(.*?)```", raw, re.S)
            turtle_code = match.group(1).strip() if match else raw.strip()
            results.append(turtle_code)
        return results
