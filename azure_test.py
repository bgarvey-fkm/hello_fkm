import os 
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION") 

# Load base64 image and extracted text for img_2_test
image_files_dir = Path("image_files")
with open(image_files_dir / "img_2_test_png_base64.txt", "r") as f:
    base64_image = f.read()
with open(image_files_dir / "img_2_test_text.txt", "r", encoding="utf-8") as f:
    extracted_text = f.read()

client = AzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=subscription_key) 

response = client.chat.completions.create(     
    messages=[         
        {
            "role": "system",
            "content": "You are a helpful assistant that analyzes documents. Given both an image and text extraction of a document, understand the content and return a JSON object with a schema that best represents the data in the document."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Here is the extracted text from the document:\n\n{extracted_text}\n\nPlease analyze both the image and text, understand the document structure and content, then return a JSON object with an appropriate schema that captures the key information. Only return valid JSON, no other text."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }    
    ],
    max_completion_tokens=16384, 
    model=deployment
) 

json_response = response.choices[0].message.content
print("Response from model:")
print(json_response)

# Save JSON response to file
output_path = image_files_dir / "img_2_test_response.json"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(json_response)

print(f"\nSaved response to: {output_path}")
 