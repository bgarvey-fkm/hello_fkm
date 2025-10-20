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


def load_all_json_files(exclude_spring=False, loan_id="1000182227"):
    """Load all JSON files from loan_docs/{loan_id}/json directory"""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        print(f"Error: {json_dir} directory not found!")
        return {}
    
    all_data = {}
    
    for json_file in json_dir.glob("*.json"):
        # Exclude Spring EQ files if requested
        if exclude_spring and "spring" in json_file.name.lower():
            print(f"  Excluding: {json_file.name}")
            continue
            
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                all_data[json_file.name] = data
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse {json_file.name}: {e}")
    
    return all_data


def load_spring_eq_files(loan_id="1000182277"):
    """Load only Spring EQ related JSON files"""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        return {}
    
    spring_data = {}
    
    for json_file in json_dir.glob("*.json"):
        if "spring" in json_file.name.lower():
            print(f"  Loading: {json_file.name}")
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    spring_data[json_file.name] = data
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse {json_file.name}: {e}")
    
    return spring_data


def turn_1_independent_analysis():
    """
    TURN 1: Analyze all documents EXCEPT Spring EQ underwriting worksheet
    Generate independent income determination in JSON format
    """
    
    print("\n" + "="*60)
    print("TURN 1: Independent Income Analysis")
    print("="*60)
    
    print("\nLoading documents (excluding Spring EQ underwriting)...")
    all_documents = load_all_json_files(exclude_spring=True)
    
    if not all_documents:
        print("No JSON files found!")
        return None
    
    print(f"\nLoaded {len(all_documents)} JSON files for independent analysis")
    
    documents_json = json.dumps(all_documents, indent=2)
    
    client = AzureOpenAI(
        api_version=api_version, 
        azure_endpoint=endpoint, 
        api_key=subscription_key
    )
    
    print("\nAnalyzing income documentation independently...")
    
    response = client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are an expert Income Verification Specialist for mortgage lending. You will analyze borrower income documentation and provide an independent determination of qualifying monthly income.

**YOUR TASK:**
Analyze all provided loan documents (paystubs, W-2s, credit reports, 1003 application, etc.) and determine the appropriate monthly income for loan underwriting.

**CRITICAL: You do NOT have access to any underwriting worksheet or final determination. You must make an INDEPENDENT assessment based solely on the source documents.**

**Analysis Requirements:**

1. **Identify ALL income sources:**
   - Base Salary (W-2, paystubs, 1003 application)
   - Overtime, Bonus, Commission (paystubs, W-2 - use 2-year average if available)
   - Self-Employment Income (tax returns)
   - Investment Income (tax returns, bank statements)
   - Social Security, Pension, Disability
   - Other documented income

2. **Apply Standard Underwriting Guidelines:**
   - Base salary: Use current pay rate from most recent paystub
   - Variable income (bonus/commission/overtime): 
     * Require 2-year history
     * Calculate 2-year average from W-2s
     * Only include if stable or increasing
   - Self-employment: Use 2-year tax return average
   - Investment income: Use 2-year average from tax returns
   - Be CONSERVATIVE - when in doubt, use lower amount or exclude

3. **Calculate Monthly Qualifying Income:**
   - Show all calculations with formulas
   - Cite specific documents and dates for each component
   - Explain why each component is included or excluded
   - Provide final determination

4. **Output Format - Return ONLY valid JSON with this structure:**

{
  "analysis_metadata": {
    "analysis_date": "YYYY-MM-DD",
    "analyst": "Independent Income Verification Agent",
    "documents_reviewed": 99,
    "confidence_level": "High|Medium|Low",
    "confidence_rationale": "Explanation of confidence level"
  },
  "income_determination": {
    "total_qualifying_monthly_income": 99999.99,
    "methodology_summary": "2-3 sentence explanation of approach"
  },
  "borrowers": [
    {
      "name": "Borrower Name",
      "total_monthly_income": 99999.99,
      "income_components": [
        {
          "type": "Base Salary|Bonus|Commission|Overtime|Self-Employment|Investment|Other",
          "monthly_amount": 9999.99,
          "annual_amount": 99999.99,
          "calculation": "Detailed calculation showing math",
          "source_documents": ["document1.pdf", "document2.pdf"],
          "source_dates": ["YYYY-MM-DD"],
          "included": true,
          "rationale": "Why included or excluded",
          "concerns": ["Any concerns about this income"]
        }
      ]
    }
  ],
  "cross_reference": {
    "form_1003_stated_income": 99999.99,
    "verified_income": 99999.99,
    "variance_amount": 999.99,
    "variance_percentage": 9.99,
    "variance_explanation": "Explanation of any difference"
  },
  "documentation_review": {
    "paystubs": [
      {
        "borrower": "Name",
        "document": "filename",
        "date": "YYYY-MM-DD",
        "pay_period_end": "YYYY-MM-DD",
        "days_old": 99,
        "gross_pay": 9999.99,
        "ytd_gross": 99999.99,
        "status": "Fresh|Stale",
        "usable": true
      }
    ],
    "w2_forms": [
      {
        "borrower": "Name",
        "year": 2024,
        "employer": "Company Name",
        "box1_wages": 99999.99,
        "document": "filename"
      }
    ],
    "other_documents": [
      {
        "type": "VOE|Tax Return|Bank Statement|Other",
        "borrower": "Name",
        "date": "YYYY-MM-DD",
        "key_data": "Relevant information extracted"
      }
    ]
  },
  "income_trends": {
    "overall_trend": "Stable|Increasing|Decreasing",
    "analysis": "Multi-year comparison if available",
    "stability_assessment": "Assessment of income continuance likelihood"
  },
  "components_excluded": [
    {
      "income_type": "Type of income",
      "potential_amount": 9999.99,
      "reason_excluded": "Detailed explanation"
    }
  ],
  "recommendations": [
    "Additional documentation needed",
    "Concerns about income continuance",
    "Other recommendations"
  ],
  "red_flags": [
    "Any concerns identified during analysis"
  ]
}

Return ONLY the JSON structure above. Do NOT include markdown, code blocks, or any other text. Just pure JSON."""
            },
            {
                "role": "user",
                "content": f"""Please analyze these loan documents and provide your independent income verification determination.

**IMPORTANT: You do NOT have access to any underwriting worksheet. Make your determination based solely on the source documents provided.**

Here are all the loan documents in JSON format:

{documents_json}

Return ONLY valid JSON following the specified structure. No markdown, no code blocks, just JSON."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    response_content = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if present
    if response_content.startswith("```"):
        lines = response_content.split('\n')
        response_content = '\n'.join(lines[1:-1])  # Remove first and last lines
    
    # Parse to validate it's proper JSON
    try:
        income_analysis = json.loads(response_content)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: LLM did not return valid JSON: {e}")
        print("Response was:")
        print(response_content[:500])
        return None
    
    # Save Turn 1 analysis to JSON file in loan-specific reports
    loan_id = "1000182227"
    output_dir = Path(f"loan_docs/{loan_id}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    turn1_path = output_dir / "income_verification.json"
    
    with open(turn1_path, "w", encoding="utf-8") as f:
        json.dump(income_analysis, f, indent=2)
    
    print(f"\n✓ Turn 1 Independent Analysis saved to: {turn1_path}")
    
    return income_analysis


def turn_2_reconciliation(turn1_analysis):
    """
    TURN 2: Load Spring EQ underwriting worksheet and reconcile with Turn 1 analysis
    Create comparison report showing discrepancies
    """
    
    print("\n" + "="*60)
    print("TURN 2: Reconciliation with Spring EQ Underwriting")
    print("="*60)
    
    print("\nLoading Spring EQ underwriting documents...")
    spring_documents = load_spring_eq_files()
    
    if not spring_documents:
        print("Warning: No Spring EQ documents found!")
        return
    
    spring_json = json.dumps(spring_documents, indent=2)
    
    client = AzureOpenAI(
        api_version=api_version, 
        azure_endpoint=endpoint, 
        api_key=subscription_key
    )
    
    print("\nReconciling independent analysis with Spring EQ underwriting...")
    
    response = client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are an expert Loan Quality Control Analyst. You will compare an independent income analysis against a Spring EQ underwriting worksheet and identify any discrepancies.

**YOUR TASK:**
1. Review the independent income analysis (Turn 1)
2. Review the Spring EQ underwriting worksheet
3. Compare the two and identify ALL discrepancies
4. Assess whether discrepancies represent conservative or aggressive underwriting
5. Create a comprehensive reconciliation report

**IMPORTANT CONCEPTS:**

**CONSERVATIVE (Lower Risk - POSITIVE):**
- Spring EQ uses LOWER income than independent analysis → Good, reduces risk
- Spring EQ uses HIGHER debts than documented → Good, reduces risk
- Spring EQ qualified at HIGHER payment than final loan → Good, stress tested
- Mark as "Conservative Approach" in GREEN - these are RISK MITIGATIONS

**AGGRESSIVE (Higher Risk - CONCERN):**
- Spring EQ uses HIGHER income than independent analysis → RED FLAG
- Spring EQ uses LOWER debts than documented → RED FLAG
- Spring EQ qualified at LOWER payment than final loan → RED FLAG
- Mark as "Aggressive Assumption" in RED - these are CONCERNS

**NEUTRAL:**
- Minor rounding differences
- Different but acceptable methodologies
- Mark as "Acceptable Variance" in BLUE

Create a professional HTML report with:

**SECTION 1: EXECUTIVE SUMMARY**
- Side-by-side comparison box:
  * Independent Analysis (Turn 1): $[amount]
  * Spring EQ Underwriting: $[amount]
  * Variance: $[difference] ([percentage]%)
  * Assessment: [Match/Conservative/Aggressive/Needs Review]

**SECTION 2: DETAILED COMPARISON TABLE**
| Income Component | Turn 1 Analysis | Spring EQ UW | Variance | Assessment | Impact |
|-----------------|-----------------|--------------|----------|------------|---------|
| Base Salary | $X,XXX | $X,XXX | $XX | Match/Conservative/Aggressive | Risk Level |
| Bonus | $XXX | $XXX | $XX | Match/Conservative/Aggressive | Risk Level |
| [etc.] | | | | | |
| **TOTAL** | **$X,XXX** | **$X,XXX** | **$XXX** | | |

**SECTION 3: DISCREPANCY ANALYSIS**
For each discrepancy:
- **Income Component:** [name]
- **Turn 1 Determination:** $[amount] - [methodology]
- **Spring EQ Value:** $[amount] - [their methodology if visible]
- **Variance:** $[difference] ([percentage]%)
- **Root Cause:** [Why the difference exists]
- **Risk Assessment:** [Conservative/Neutral/Aggressive]
- **Recommendation:** [Accept/Question/Reject]

**SECTION 4: METHODOLOGY COMPARISON**
- How did Turn 1 calculate income?
- How did Spring EQ calculate income?
- Are different guidelines being applied?
- Are different time periods being used?

**SECTION 5: DOCUMENT CITATIONS**
- List all documents used in Turn 1 analysis
- List all Spring EQ documents
- Note any documents one analysis had that the other didn't

**SECTION 6: OVERALL ASSESSMENT**
- Is Spring EQ underwriting conservative, neutral, or aggressive?
- Are there any red flags?
- Is the Spring EQ determination acceptable?
- What questions should be asked?

**SECTION 7: RECOMMENDATIONS**
- Accept Spring EQ underwriting as-is?
- Request clarification on specific items?
- Request additional documentation?
- Override certain determinations?

Use color coding:
- **DARK GREEN** - Conservative approach (Spring EQ lower than Turn 1)
- **LIGHT GREEN** - Match or acceptable variance
- **YELLOW** - Minor discrepancy, needs clarification
- **ORANGE** - Moderate concern
- **RED** - Major discrepancy or aggressive assumption
- **BLUE** - Informational/neutral

Return ONLY the complete HTML document (starting with <!DOCTYPE html>), no other text."""
            },
            {
                "role": "user",
                "content": f"""Please reconcile the independent income analysis with the Spring EQ underwriting worksheet.

**TURN 1 INDEPENDENT ANALYSIS:**
{turn1_analysis}

**SPRING EQ UNDERWRITING DOCUMENTS:**
{spring_json}

Create a comprehensive reconciliation report comparing the two and identifying all discrepancies."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    reconciliation_html = response.choices[0].message.content
    
    # Save Turn 2 reconciliation report
    output_dir = Path("loan_summary")
    turn2_path = output_dir / "turn2_income_reconciliation.html"
    
    with open(turn2_path, "w", encoding="utf-8") as f:
        f.write(reconciliation_html)
    
    print(f"\n✓ Turn 2 Reconciliation Report saved to: {turn2_path}")


def main():
    """
    Run the independent income verification analysis
    """
    
    print("\n" + "="*60)
    print("INDEPENDENT INCOME VERIFICATION ANALYSIS")
    print("="*60)
    print("\nThis process will:")
    print("1. Analyze income from source documents (excluding Spring EQ)")
    print("2. Determine appropriate monthly qualifying income")
    print("3. Generate JSON report for next agent in chain")
    
    # Independent analysis without Spring EQ worksheet
    turn1_result = turn_1_independent_analysis()
    
    if not turn1_result:
        print("\nError in analysis. Aborting.")
        return
    
    print("\n" + "="*60)
    print("INCOME VERIFICATION COMPLETE")
    print("="*60)
    print("\nGenerated file:")
    print("  - loan_docs/1000182227/reports/income_verification.json")
    print("\nThis JSON file can be consumed by the next agent in the chain.")


if __name__ == "__main__":
    main()
