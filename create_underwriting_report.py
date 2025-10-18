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

IMPORTANT CONTEXT:
- Form 1003 is typically filled out FIRST by the borrower and then verified later with documentation
- Loan terms may change during the underwriting process
- The Spring EQ underwriting summary represents the FINAL underwritten position after verification

Your task is to:
1. Analyze all provided loan documents (paystubs, W-2s, credit reports, appraisals, mortgage statements, 1003 application, Spring EQ underwriting summary, etc.)
2. **CRITICAL: If a Spring EQ underwriting summary is present, compare ALL data points against the source documents**
   - Verify income figures match paystubs/W-2s
   - Verify debt obligations match credit reports and statements
   - Verify property information matches appraisal
   - Compare 1003 application data with Spring EQ underwrite (note: differences are normal as 1003 comes first)
   - **UNDERSTAND CONSERVATIVE VS. AGGRESSIVE UNDERWRITING:**
     
     **CONSERVATIVE (Lower Risk - POSITIVE):**
     - Spring EQ uses LOWER income than documented → Good, reduces risk
     - Spring EQ uses HIGHER debts than documented → Good, reduces risk
     - Spring EQ uses LOWER property value than appraisal → Good, reduces risk
     - Spring EQ calculates HIGHER DTI than raw documents show → Good, more conservative
     - Spring EQ shows HIGHER interest rate than final loan → Good, qualified at higher payment
     - Spring EQ shows HIGHER loan amount than final loan → Good, qualified at higher payment
     - Spring EQ shows HIGHER monthly payment than final loan → Good, qualified at higher payment
     - **KEY CONCEPT:** If borrower qualified at a HIGHER payment (higher rate/amount) but gets a LOWER payment (lower rate/amount), that's CONSERVATIVE and GOOD
     - Mark these as "Conservative Approach" in GREEN - these are RISK MITIGATIONS, not concerns
     
     **AGGRESSIVE (Higher Risk - CONCERN):**
     - Spring EQ uses HIGHER income than documented → RED FLAG, overstating ability to pay
     - Spring EQ uses LOWER debts than credit report shows → RED FLAG, understating obligations
     - Spring EQ uses HIGHER property value than appraisal → RED FLAG, overstating collateral
     - Spring EQ calculates LOWER DTI than documents support → RED FLAG, understating risk
     - Spring EQ shows LOWER interest rate for qualification than final loan → RED FLAG, qualified at lower payment
     - Spring EQ shows LOWER loan amount for qualification than final loan → RED FLAG, qualified at lower payment
     - Spring EQ shows LOWER monthly payment for qualification than final loan → RED FLAG, qualified at lower payment
     - **KEY CONCEPT:** If borrower qualified at a LOWER payment but will have a HIGHER payment, that's AGGRESSIVE and BAD
     - Mark these as "Aggressive Assumption" in RED - these are REAL CONCERNS

3. Calculate key underwriting metrics independently from source documents:
   - Front-End DTI (Housing payment / Gross monthly income)
   - Back-End DTI (All monthly debt payments / Gross monthly income)
   - Current monthly income from all sources
   - Total monthly debt obligations
   - Available assets and reserves
   - Credit profile summary
4. Compare YOUR calculations with Spring EQ underwriting summary
5. Assess the borrower's overall creditworthiness
6. Identify any red flags or areas of concern
7. Provide a comprehensive underwriting recommendation

Create a professional HTML report with:
- Clean, modern styling with CSS
- Executive Summary section
- **DISCREPANCY ANALYSIS** (if Spring EQ or other underwriting summary exists)
  - List ALL discrepancies found between the summary and source documents
  - Include side-by-side comparison table with columns:
    * Data Point
    * Source Document Value
    * Spring EQ Underwrite Value
    * Your Calculated Value
    * Risk Assessment (Conservative/Neutral/Aggressive)
    * Impact (Positive/Neutral/Concern)
  - **CLEARLY DISTINGUISH** between conservative (good) and aggressive (bad) discrepancies
- Borrower Information
- Income Analysis (with calculations shown and sources cited)
- Debt Analysis (with all debts listed from source documents)
- DTI Calculations (Front-End and Back-End with formulas and step-by-step math)
- Credit Summary
- Asset Summary
- Property Information (if available)
- Risk Assessment
- Underwriting Recommendation
- Supporting Details section with document sources

Use tables, proper formatting, and color coding:
- **DARK GREEN** for conservative underwriting (positive risk mitigation)
- **LIGHT GREEN** for verified/matching data
- **YELLOW** for neutral discrepancies or needs verification
- **RED** for aggressive assumptions or major concerns
- **BLUE** for informational notes (e.g., 1003 vs final terms differences)

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
