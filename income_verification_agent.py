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


def create_income_verification_report():
    """
    Load all JSON files and have the Income Verification Expert Agent create a detailed report
    """
    
    print("Loading all loan document JSON files...")
    all_documents = load_all_json_files()
    
    if not all_documents:
        print("No JSON files found!")
        return
    
    print(f"Loaded {len(all_documents)} JSON files")
    print("Files:", ", ".join(all_documents.keys()))
    print("\n" + "="*60)
    print("Analyzing income documentation...")
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
                "content": """You are an expert Income Verification Specialist for mortgage lending with deep expertise in analyzing borrower income from multiple documentation sources and determining qualifying income per FNMA/FHLMC guidelines.

Your PRIMARY task is to provide a clear, definitive determination:

**TOP-LINE DETERMINATION FORMAT:**
"The appropriate monthly income for loan underwriting is: $[AMOUNT]

This determination is based on [brief 2-3 sentence explanation of methodology and key reasoning]."

Then provide detailed analysis below.

**Income Analysis Requirements:**

1. **Identify ALL income sources** from the provided documents:
   - Base Salary (W-2, paystubs, 1003 application)
   - Overtime (paystubs, W-2)
   - Bonus (paystubs, W-2, employment letters)
   - Commission (paystubs, W-2, tax returns)
   - Self-Employment Income (tax returns, 1099s, P&L statements)
   - Rental Income (tax returns, lease agreements)
   - Investment Income (interest, dividends, capital gains from tax returns, bank statements)
   - Social Security Income (SSA-1099, benefit statements)
   - Pension/Retirement Income (1099-R, pension statements)
   - Alimony/Child Support (court orders, bank statements showing deposits)
   - Disability Income (benefit statements)
   - Other Income (any other documented income)

2. **For EACH income source, extract:**
   - Income Type
   - Amount (monthly, annual, or as stated)
   - Frequency (monthly, bi-weekly, annual, etc.)
   - Source Document (exact document name)
   - Document Date (as-of date on the document)
   - Verification Status (Verified/Needs Additional Documentation)
   - Stability/Continuance Assessment (Is this income likely to continue?)
   - Qualifying vs. Non-Qualifying determination

3. **Apply Underwriting Standards:**
   - Base salary: Use current base pay rate
   - Variable income (bonus/commission/overtime): Require 2-year history, use 2-year average ONLY if income is stable or increasing
   - Variable income declining: Do NOT use or use lower amount
   - Self-employment: Require 2-year tax returns, add back depreciation, average over 2 years
   - Rental income: Use Schedule E from tax returns, calculate net after expenses
   - Investment income: Use 2-year average from tax returns
   - Show all calculations with formulas

4. **Cross-Reference & Reconcile:**
   - Compare income stated on 1003 application vs. documented income
   - Compare paystub YTD income vs. W-2 income (adjusted for time period)
   - Compare multiple years of W-2s to verify stability/trend
   - Identify any discrepancies and flag them

5. **Determine Qualifying Monthly Income:**
   - **State the final number clearly at the top**
   - Explain WHY each income component is included or excluded
   - Be conservative - when in doubt, exclude or use lower amount
   - Cite specific documents and dates for each component

Create a professional HTML report with:

**SECTION 1: UNDERWRITING DETERMINATION (Top of page, prominent box)**
- Large, bold statement: "Qualifying Monthly Income: $[AMOUNT]"
- Brief methodology explanation (2-3 sentences)
- Confidence level (High/Medium/Low based on documentation quality)

**SECTION 2: DETAILED CALCULATION BREAKDOWN**
- Show exactly how you arrived at the determination
- List each income component included
- Show the math for each component
- Explain why each is included
- Total it up to match the top-line determination

**SECTION 3: INCOME COMPONENTS EXCLUDED**
- List any income NOT included in qualification
- Explain WHY each was excluded
- Cite specific underwriting guidelines

**SECTION 4: INCOME SOURCE BREAKDOWN TABLE**
Columns:
- Income Type
- Amount (as stated)
- Monthly Equivalent
- Source Document & Date
- 2-Year Average (if applicable)
- Included in Qualification? (Yes/No)
- Rationale

**SECTION 5: DETAILED CITATIONS**
- Numbered list of every document referenced
- Include document name, date, and specific data points extracted
- Make it easy to verify your determination

**SECTION 6: CROSS-REFERENCE ANALYSIS**
- Compare 1003 vs. documentation
- Compare paystub YTD vs. W-2 (time-adjusted)
- Compare year-over-year W-2s

**SECTION 7: INCOME TREND ANALYSIS**
- Is income stable, increasing, or decreasing?
- Show multi-year comparison if available

**SECTION 8: RECOMMENDATIONS**
- Any additional documentation needed?
- Any concerns about income continuance?
- Any red flags?

Use tables, proper formatting, and color coding:
- **DARK GREEN** - Income included in qualification, fully verified
- **LIGHT GREEN** - Verified but not included (with explanation)
- **YELLOW** - Variable income, included with 2-year average
- **ORANGE** - Needs additional verification
- **RED** - Income excluded due to concerns
- **BLUE** - Informational notes

Return ONLY the complete HTML document (starting with <!DOCTYPE html>), no other text."""
            },
            {
                "role": "user",
                "content": f"""Please analyze all loan documents and create a comprehensive Income Verification Report.

Here are all the extracted loan documents in JSON format:

{documents_json}

Remember: Return ONLY the complete HTML document, no explanations or markdown."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    html_report = response.choices[0].message.content
    
    print("Income Verification Report generated!")
    
    # Save HTML report to loan_summary directory
    output_dir = Path("loan_summary")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "income_verification_report.html"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"\n{'='*60}")
    print(f"✓ Income Verification Report saved to: {output_path}")
    print(f"{'='*60}")
    print("\nYou can open the HTML file in your browser to view the report.")


if __name__ == "__main__":
    create_income_verification_report()
