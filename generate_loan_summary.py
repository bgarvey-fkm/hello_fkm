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

# Load both JSON files
image_files_dir = Path("image_files")
with open(image_files_dir / "img_test_response.json", "r", encoding="utf-8") as f:
    payroll_data = json.load(f)
with open(image_files_dir / "img_2_test_response.json", "r", encoding="utf-8") as f:
    mortgage_data = json.load(f)

client = AzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=subscription_key) 

response = client.chat.completions.create(     
    messages=[         
        {
            "role": "system",
            "content": "You are a financial analyst assistant that creates comprehensive HTML reports. You will analyze payroll and mortgage data to create a detailed summary including DTI (Debt-to-Income) ratio calculations used in mortgage lending."
        },
        {
            "role": "user",
            "content": f"""I have two JSON documents:

1. Payroll/Paystub Data:
{json.dumps(payroll_data, indent=2)}

2. Mortgage Statement Data:
{json.dumps(mortgage_data, indent=2)}

Please create a comprehensive HTML report that:
1. Summarizes the key information from both documents
2. Calculates the current DTI (Debt-to-Income) ratio using standard mortgage lending calculations
3. Provides insights on the borrower's financial situation
4. Includes proper styling with CSS for a professional appearance
5. Highlights important metrics and ratios

Return ONLY the complete HTML document (starting with <!DOCTYPE html>), no other text or explanations."""
        }    
    ],
    max_completion_tokens=16384, 
    model=deployment
) 

html_report = response.choices[0].message.content
print("Generated HTML report")

# Save HTML report to loan_summary directory
output_dir = Path("loan_summary")
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "financial_summary_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_report)

print(f"Saved report to: {output_path}")
