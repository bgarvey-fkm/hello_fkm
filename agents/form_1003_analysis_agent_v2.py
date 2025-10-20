"""
Form 1003 Analysis Agent (Schema-Driven Approach)

This version uses a pre-defined JSON schema template and instructs the LLM
to fill in values from raw JSON documents, ensuring consistent structure.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


def load_schema_template() -> Dict:
    """Load the Form 1003 JSON schema template."""
    schema_path = Path("utils/form_1003_schema.json")
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all_loan_json_files(loan_id: str) -> Dict[str, Dict]:
    """Load all JSON files for a given loan."""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        print(f"JSON directory not found: {json_dir}")
        return {}
    
    json_files = {}
    for json_file in json_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                json_files[json_file.stem] = data
        except Exception as e:
            print(f"Error loading {json_file.name}: {e}")
    
    return json_files


def extract_1003_with_schema(loan_id: str, json_data: Dict[str, Dict], schema: Dict) -> Dict:
    """
    Extract Form 1003 data using the provided schema as a strict template.
    The LLM fills in the schema fields from raw JSON documents.
    """
    
    print(f"\n{'='*80}")
    print("SCHEMA-DRIVEN FORM 1003 EXTRACTION")
    print(f"{'='*80}\n")
    
    print("Loading schema template...")
    print(f"Analyzing {len(json_data)} JSON documents...")
    
    # Create the comprehensive prompt
    prompt = f"""You are an expert mortgage document analyst extracting Form 1003 (Uniform Residential Loan Application) data.

**CRITICAL INSTRUCTIONS:**

You will be provided with:
1. A JSON SCHEMA TEMPLATE that defines the exact structure required
2. Raw JSON documents from a mortgage loan file

Your task:
- Fill in the schema template with values extracted from the raw JSON documents
- Follow the schema structure EXACTLY - do not add or remove fields
- Use the data types specified in the schema (strings, numbers, booleans, arrays, objects)
- If a field cannot be found in the documents, use null for optional fields or appropriate empty values
- The Form 1003 document may be split across multiple files (form_1003, mtg_1003, application, etc.)

**JSON SCHEMA TEMPLATE TO FILL:**

{json.dumps(schema, indent=2)}

**RAW LOAN DOCUMENTS (all JSON files in the package):**

{json.dumps(json_data, indent=2)}

**YOUR TASK:**

Return the FILLED schema as valid JSON. Every field in the schema should be populated with actual values from the documents or appropriate null/empty values if data is not available.

IMPORTANT:
- Set loan_id to "{loan_id}"
- Set analysis_date to the current ISO timestamp
- Extract ALL Form 1003 data you find across all documents
- Be thorough and accurate - downstream agents depend on this data
- Use exact values from documents (don't paraphrase or summarize)
- For dates, use YYYY-MM-DD format
- For phone numbers, use (XXX) XXX-XXXX format
- For dollar amounts, use numbers (not strings)

Return ONLY the filled JSON schema. No explanations, no markdown, just valid JSON.
"""
    
    print("Calling Azure OpenAI with schema template...")
    print("This may take a moment due to comprehensive extraction...\n")
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage document analyst. You extract Form 1003 data with perfect accuracy and fill JSON schemas precisely according to specifications."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=16000
        )
        
        filled_schema = json.loads(response.choices[0].message.content)
        
        print(f"✅ Successfully extracted Form 1003 data using schema template!")
        
        # Print summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"   Loan ID: {filled_schema.get('loan_id', 'Unknown')}")
        
        assertions = filled_schema.get('assertions', {})
        
        if 'process_anchor' in assertions:
            anchor = assertions['process_anchor']
            app_date = anchor.get('application_date', 'Not found')
            print(f"   Application Date (Day 0): {app_date}")
        
        if 'borrower_information' in assertions:
            borrowers = assertions['borrower_information']
            if borrowers.get('primary_borrower'):
                print(f"   Primary Borrower: {borrowers['primary_borrower'].get('name', 'Unknown')}")
            if borrowers.get('co_borrower') and borrowers['co_borrower'].get('name'):
                print(f"   Co-Borrower: {borrowers['co_borrower'].get('name')}")
        
        if 'loan_details' in assertions:
            loan = assertions['loan_details']
            print(f"   Loan Amount: ${loan.get('loan_amount_requested', 0):,.2f}")
            print(f"   Loan Purpose: {loan.get('loan_purpose', 'Unknown')}")
        
        if 'employment_and_income' in assertions:
            emp = assertions['employment_and_income']
            if emp.get('primary_borrower'):
                income = emp['primary_borrower'].get('gross_monthly_income', {})
                print(f"   Primary Income: ${income.get('total', 0):,.2f}/month")
            if emp.get('co_borrower'):
                income = emp['co_borrower'].get('gross_monthly_income', {})
                print(f"   Co-Borrower Income: ${income.get('total', 0):,.2f}/month")
        
        return filled_schema
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: LLM did not return valid JSON: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return {}


def save_1003_analysis(loan_id: str, analysis: Dict):
    """Save the analysis to a JSON file for downstream processing."""
    
    # Save to JSON in loan-specific reports folder
    report_dir = Path(f"loan_docs/{loan_id}/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = report_dir / "form_1003_analysis.json"
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"💾 Analysis saved to: {json_file}")
    print(f"{'='*80}\n")
    
    return json_file


def main():
    # Accept loan_id from command line argument or use default
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    print(f"\n{'='*80}")
    print("FORM 1003 ANALYSIS AGENT (Schema-Driven v2)")
    print(f"{'='*80}\n")
    
    # Load schema template
    print("Loading JSON schema template...")
    schema = load_schema_template()
    print(f"✅ Schema loaded with {len(schema.keys())} top-level fields\n")
    
    # Load all JSON files
    print(f"Loading loan documents for {loan_id}...")
    json_data = load_all_loan_json_files(loan_id)
    
    if not json_data:
        print("❌ No JSON files found!")
        return
    
    print(f"✅ Loaded {len(json_data)} JSON documents\n")
    
    # Extract using schema
    analysis = extract_1003_with_schema(loan_id, json_data, schema)
    
    if not analysis:
        print("\n❌ Failed to extract Form 1003 data!")
        return
    
    # Save results
    output_file = save_1003_analysis(loan_id, analysis)
    
    print("\n" + "="*80)
    print("✅ FORM 1003 ANALYSIS COMPLETE")
    print("="*80)
    print("\nBenefits of Schema-Driven Approach:")
    print("  ✅ Consistent JSON structure across all loans")
    print("  ✅ Predictable field names for downstream agents")
    print("  ✅ Easier to validate and parse")
    print("  ✅ Better for automation and integration")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
