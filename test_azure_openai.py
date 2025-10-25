import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables - override any existing ones
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
 
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# Debug output
print(f"Endpoint: {endpoint}")
print(f"Deployment: {deployment}")
print(f"Key: {subscription_key[:20]}...")
print(f"API Version: {api_version}")
print()
 
client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)
 
response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_completion_tokens=16384,
    model=deployment
)
 
print(response.choices[0].message.content)
