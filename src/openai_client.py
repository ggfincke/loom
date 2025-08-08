import os
import json
from dotenv import load_dotenv
from openai import OpenAI


# validate JSON response from OpenAI API
def openai_json(prompt: str, model: str = "gpt-4o-mini") -> dict:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY in environment or .env")
    client = OpenAI()
    resp = client.responses.create(model=model, input=prompt, temperature=0.2)
    # ensure valid JSON (model should already be constrained by prompt)
    try:
        return json.loads(resp.output_text)
    except json.JSONDecodeError as e:
        # fail
        raise RuntimeError(f"Model did not return valid JSON. Raw:\n{resp.output_text}") from e