import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
from google.genai import types
client = genai.Client(
    api_key=os.environ["LLM_API_KEY"],
    http_options=types.HttpOptions(timeout=30000),  # milliseconds
)

model = os.environ.get("LLM_MODEL", "").strip()
if not model:
    print("Models available to your key:")
    for m in client.models.list():
        if "generateContent" in (m.supported_actions or []):
            print("  ", m.name)
    print("\nPick a Flash-class model, set LLM_MODEL in .env (e.g. models/xyz -> xyz), and rerun.")
else:
    r = client.models.generate_content(
        model=model,
        contents="Write one BigQuery SQL query that counts rows in a table called orders. Return only SQL.",
    )
    print(r.text)