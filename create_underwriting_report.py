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


def load_all_json_files():
    """Load all JSON files from loan_docs_json directory"""
    json_dir = Path("loan_docs_json")
    
    if not json_dir.exists():
        print(f"Error: {json_dir} directory not found!")
        return {}
    
    all_data = {}
    
    for json_file in json_dir.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                all_data[json_file.name] = data
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse {json_file.name}: {e}")
    
    return all_data


def create_underwriting_report():
    """
    Load all JSON files and have the Loan Underwriter Agent create a comprehensive report
    """
    
    print("Loading all loan document JSON files...")
    all_documents = load_all_json_files()
    
    if not all_documents:
        print("No JSON files found!")
        return
    
    print(f"Loaded {len(all_documents)} JSON files")
    print("Files:", ", ".join(all_documents.keys()))
    print("\n" + "="*60)
    print("Analyzing documents and creating underwriting report...")
    print("="*60 + "\n")
    
    # Convert all documents to a formatted string for the prompt
    documents_json = json.dumps(all_documents, indent=2)
    
    client = AzureOpenAI(
        api_version=api_version, 
        azure_endpoint=endpoint, 
        api_key=subscription_key
    )
    
    response = client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are an expert Loan Underwriter Agent with years of experience in residential mortgage underwriting. 

Your task is to:
1. Analyze all provided loan documents (paystubs, W-2s, credit reports, appraisals, mortgage statements, etc.)
2. Reconcile any discrepancies between documents
3. Calculate key underwriting metrics:
   - Front-End DTI (Housing payment / Gross monthly income)
   - Back-End DTI (All monthly debt payments / Gross monthly income)
   - Current monthly income from all sources
   - Total monthly debt obligations
   - Available assets and reserves
   - Credit profile summary
4. Assess the borrower's overall creditworthiness
5. Identify any red flags or areas of concern
6. Provide a comprehensive underwriting recommendation

Create a professional HTML report with:
- Clean, modern styling with CSS
- Executive Summary section
- Borrower Information
- Income Analysis (with calculations shown)
- Debt Analysis
- DTI Calculations (Front-End and Back-End with formulas)
- Credit Summary
- Asset Summary
- Property Information (if available)
- Risk Assessment
- Underwriting Recommendation
- Supporting Details section

Use tables, proper formatting, and color coding (green for good, yellow for caution, red for concerns).
Return ONLY the complete HTML document (starting with <!DOCTYPE html>), no other text."""
            },
            {
                "role": "user",
                "content": f"""Please analyze all these loan documents and create a comprehensive underwriting report.

Here are all the extracted loan documents in JSON format:

{documents_json}

Remember: Return ONLY the complete HTML document, no explanations or markdown."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    html_report = response.choices[0].message.content
    
    print("Report generated!")
    
    # Save HTML report to loan_summary directory
    output_dir = Path("loan_summary")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "underwriting_report.html"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"\n{'='*60}")
    print(f"✓ Underwriting report saved to: {output_path}")
    print(f"{'='*60}")
    print("\nYou can open the HTML file in your browser to view the report.")


if __name__ == "__main__":
    create_underwriting_report()
