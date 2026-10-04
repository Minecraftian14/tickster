from openai import OpenAI

from gai_providers import OPENROUTER_CONFIG

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_CONFIG["default"],
)

response = client.embeddings.create(
    model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
    input="What is this project about?"
)

def test_this():
    print("Hello")
    print("Hello")
    print(response)
