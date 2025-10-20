"""
Form 1003 Analysis Agent (Two-Turn Process)

The Form 1003 (Uniform Residential Loan Application) is the ANCHOR of the underwriting process.
Everything else in the loan file exists to VALIDATE what the borrowers declared on the 1003.

Turn 1: Identify all JSON files that contain 1003 data or related pages
Turn 2: Extract all borrower assertions from the 1003 that require validation

Validation categories:
- PULLED DATA: Credit reports, property appraisals, title reports, VOE
- SUBMITTED DOCUMENTS: Paystubs, W-2s, bank statements, tax returns, insurance
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
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

DEPLOYMENT_NAME = deployment


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


def turn1_identify_1003_files(loan_id: str, json_data: Dict[str, Dict]) -> List[str]:
    """
    TURN 1: Identify all JSON files that contain Form 1003 data.
    
    The 1003 may be split across multiple files (pages) or have related documents.
    """
    
    print(f"\n{'='*80}")
    print("TURN 1: Identifying Form 1003 Documents")
    print(f"{'='*80}\n")
    
    # Create a summary of all files for the agent
    file_summary = {}
    for filename, data in json_data.items():
        doc_type = data.get('document_type', 'Unknown')
        # Get a preview of the content
        preview = {
            'document_type': doc_type,
            'keys': list(data.keys())[:20],  # First 20 keys
            'sample_data': {}
        }
        
        # Add some sample fields
        for key in ['application_date', 'borrower_name', 'loan_amount', 'property_address']:
            if key in data:
                preview['sample_data'][key] = data[key]
        
        file_summary[filename] = preview
    
    # Create prompt for agent
    prompt = f"""You are analyzing a mortgage loan file to identify all documents related to the Form 1003 (Uniform Residential Loan Application).

The Form 1003 is THE ANCHOR DOCUMENT for mortgage underwriting. It is the standard industry-wide application form where borrowers declare:
- Personal information (names, SSNs, DOBs, contact info)
- Employment and income
- Assets and liabilities
- Property information
- Loan details and purpose
- Declarations about their financial situation

The 1003 may be:
1. A single multi-page document split into multiple JSON files (form_1003_pg1.json, form_1003_pg2.json, etc.)
2. An electronic application (eApp, e1003, application.json)
3. Listed as "Uniform Residential Loan Application" or "URLA"

Here is a summary of all {len(json_data)} JSON files in the loan package:

{json.dumps(file_summary, indent=2)}

Your task:
Identify ALL filenames that contain Form 1003 data or are pages of the 1003.

Return your response as a JSON array of filenames, like this:
{{"1003_files": ["form_1003_pg1", "form_1003_pg2", "application", "urla"]}}

Only include files that are actually the 1003 or parts of it. Do NOT include validation documents like credit reports, paystubs, or appraisals.
"""
    
    print("Calling Azure OpenAI to identify 1003 files...")
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage document analyst. You identify Form 1003 documents with high accuracy."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        identified_files = result.get('1003_files', [])
        
        print(f"\n✅ Identified {len(identified_files)} Form 1003 file(s):")
        for filename in identified_files:
            print(f"   - {filename}")
        
        return identified_files
        
    except Exception as e:
        print(f"Error in Turn 1: {e}")
        return []


def turn2_extract_1003_assertions(loan_id: str, json_data: Dict[str, Dict], form_1003_files: List[str]) -> Dict:
    """
    TURN 2: Extract all borrower assertions from the 1003 that require validation.
    
    These assertions fall into two categories:
    1. PULLED DATA - Lender pulls data to verify (credit, appraisal, VOE, title)
    2. SUBMITTED DOCUMENTS - Borrower provides documentation (paystubs, W-2s, bank statements)
    """
    
    print(f"\n{'='*80}")
    print("TURN 2: Extracting Form 1003 Assertions")
    print(f"{'='*80}\n")
    
    # Combine all 1003 data
    combined_1003_data = {}
    for filename in form_1003_files:
        if filename in json_data:
            combined_1003_data[filename] = json_data[filename]
    
    if not combined_1003_data:
        print("❌ No 1003 data found!")
        return {}
    
    # Create prompt for extraction
    prompt = f"""You are analyzing the Form 1003 (Uniform Residential Loan Application) to extract ALL borrower assertions that require validation.

The Form 1003 is THE STARTING POINT of the underwriting process. The borrowers signed this form on a specific date, making declarations about their financial situation, employment, income, assets, debts, and the property they want to finance.

EVERYTHING ELSE in the loan file exists to VALIDATE these assertions through either:

1. PULLED DATA (Lender pulls verification):
   - Credit report (validates debts, credit history, payment history)
   - Appraisal (validates property value)
   - Verification of Employment/VOE (validates employment and income)
   - Title report (validates property ownership, liens)
   - Verification of Deposit/VOD (validates bank accounts)

2. SUBMITTED DOCUMENTS (Borrower provides evidence):
   - Paystubs (validate income)
   - W-2s (validate income history)
   - Tax returns (validate self-employment income)
   - Bank statements (validate assets, deposits)
   - Insurance declarations (validate property insurance)
   - Purchase agreement (validates transaction)

Here is the complete Form 1003 data (may be across multiple pages):

{json.dumps(combined_1003_data, indent=2)}

Your task is to extract a comprehensive JSON structure containing:

1. PROCESS ANCHOR:
   - application_date (when 1003 was signed - this is day 0 of the process)
   - borrower_signatures (who signed and when)
   - submission_method (electronic, paper, etc.)

2. BORROWER ASSERTIONS (what they declared):
   
   A. BORROWER INFORMATION:
      - Primary borrower: name, SSN (last 4), DOB, contact
      - Co-borrower(s): name, SSN (last 4), DOB, contact
   
   B. EMPLOYMENT & INCOME (requires paystubs, W-2s, VOE):
      - For each borrower:
        * Employer name
        * Job title/position
        * Start date
        * Monthly income (base, overtime, bonus, commission)
        * Employment type (W-2, self-employed, etc.)
   
   C. ASSETS (requires bank statements, investment statements):
      - Bank accounts (type, institution, balance)
      - Retirement accounts
      - Other assets (stocks, bonds, real estate)
   
   D. LIABILITIES (requires credit report validation):
      - Mortgages (creditor, balance, payment)
      - Auto loans
      - Student loans
      - Credit cards
      - Other debts
   
   E. PROPERTY INFORMATION (requires appraisal, title):
      - Property address
      - Property type
      - Occupancy (primary, second home, investment)
      - Estimated value
      - Purchase price (if applicable)
   
   F. LOAN DETAILS:
      - Loan amount requested
      - Loan purpose (purchase, refinance, cash-out)
      - Loan type (conventional, FHA, VA, etc.)
   
   G. DECLARATIONS (yes/no questions that may require explanation):
      - Outstanding judgments
      - Bankruptcy history
      - Foreclosure history
      - Lawsuit involvement
      - Loan on property
      - Down payment borrowed

Return a comprehensive JSON object with all extracted information clearly organized.
Use this structure as a guide but include ALL data you find.
"""
    
    print("Calling Azure OpenAI to extract 1003 assertions...")
    print("This may take a moment due to the comprehensive analysis required...\n")
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage underwriter. You extract comprehensive borrower assertions from Form 1003 applications with perfect accuracy and completeness."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=16000
        )
        
        assertions = json.loads(response.choices[0].message.content)
        
        print(f"\n✅ Successfully extracted Form 1003 assertions!")
        
        # Print summary
        if 'process_anchor' in assertions:
            anchor = assertions['process_anchor']
            print(f"\n📌 PROCESS ANCHOR:")
            print(f"   Application Date: {anchor.get('application_date', 'Not found')}")
            print(f"   This is DAY 0 of the underwriting process")
        
        if 'borrower_information' in assertions:
            print(f"\n👤 BORROWERS:")
            borrowers = assertions['borrower_information']
            if 'primary_borrower' in borrowers:
                print(f"   Primary: {borrowers['primary_borrower'].get('name', 'Unknown')}")
            if 'co_borrower' in borrowers:
                print(f"   Co-borrower: {borrowers['co_borrower'].get('name', 'Unknown')}")
        
        if 'employment_and_income' in assertions:
            print(f"\n💼 EMPLOYMENT & INCOME (requires validation via paystubs, W-2s, VOE)")
            emp = assertions['employment_and_income']
            for borrower_key in emp:
                if isinstance(emp[borrower_key], dict):
                    employer = emp[borrower_key].get('employer_name', 'Unknown')
                    income = emp[borrower_key].get('monthly_income', {})
                    print(f"   {borrower_key}: {employer}")
        
        if 'liabilities' in assertions:
            print(f"\n💳 LIABILITIES (requires validation via credit report)")
            liabs = assertions['liabilities']
            total_liabs = len(liabs) if isinstance(liabs, list) else len(liabs.keys()) if isinstance(liabs, dict) else 0
            print(f"   {total_liabs} liabilities declared")
        
        if 'property_information' in assertions:
            print(f"\n🏠 PROPERTY (requires validation via appraisal, title)")
            prop = assertions['property_information']
            addr = prop.get('property_address', 'Unknown')
            value = prop.get('estimated_value', 'Unknown')
            print(f"   Address: {addr}")
            print(f"   Estimated Value: {value}")
        
        return assertions
        
    except Exception as e:
        print(f"Error in Turn 2: {e}")
        return {}


def save_1003_analysis(loan_id: str, form_1003_files: List[str], assertions: Dict):
    """Save the analysis to a JSON file for downstream processing."""
    
    output = {
        'loan_id': loan_id,
        'analysis_date': datetime.now().isoformat(),
        'form_1003_files': form_1003_files,
        'assertions': assertions,
        'metadata': {
            'description': 'Form 1003 is the anchor of the underwriting process. All other documents validate these assertions.',
            'validation_categories': {
                'pulled_data': ['credit_report', 'appraisal', 'voe', 'title_report', 'vod'],
                'submitted_documents': ['paystubs', 'w2s', 'tax_returns', 'bank_statements', 'insurance', 'purchase_agreement']
            }
        }
    }
    
    # Save to JSON in loan-specific reports folder
    report_dir = Path(f"loan_docs/{loan_id}/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = report_dir / "form_1003_analysis.json"
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"📄 Analysis saved to: {json_file}")
    print(f"{'='*80}\n")
    
    return json_file


def main():
    loan_id = "1000182227"
    
    print(f"\n{'='*80}")
    print("FORM 1003 ANALYSIS AGENT")
    print("Two-Turn Process to Identify and Extract Borrower Assertions")
    print(f"{'='*80}\n")
    
    # Load all JSON files
    print(f"Loading loan documents for {loan_id}...")
    json_data = load_all_loan_json_files(loan_id)
    
    if not json_data:
        print("❌ No JSON files found!")
        return
    
    print(f"✅ Loaded {len(json_data)} JSON documents\n")
    
    # TURN 1: Identify 1003 files
    form_1003_files = turn1_identify_1003_files(loan_id, json_data)
    
    if not form_1003_files:
        print("\n❌ No Form 1003 files identified!")
        return
    
    # TURN 2: Extract assertions
    assertions = turn2_extract_1003_assertions(loan_id, json_data, form_1003_files)
    
    if not assertions:
        print("\n❌ Failed to extract assertions!")
        return
    
    # Save results
    output_file = save_1003_analysis(loan_id, form_1003_files, assertions)
    
    print("\n" + "="*80)
    print("✅ FORM 1003 ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext Steps:")
    print("1. Use the application_date as DAY 0 for timeline analysis")
    print("2. Match validation documents to assertions:")
    print("   - Credit report → validates liabilities")
    print("   - Paystubs/W-2s → validate employment & income")
    print("   - Appraisal → validates property value")
    print("   - Bank statements → validate assets")
    print("3. Check document dates against application date for freshness")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
