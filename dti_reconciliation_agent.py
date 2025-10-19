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


def load_markdown_files(loan_id="1000182277"):
    """Load the independent analysis markdown files"""
    summary_dir = Path("reports")
    
    income_md_path = summary_dir / f"{loan_id}_income_analysis.md"
    debt_md_path = summary_dir / f"{loan_id}_debt_analysis.md"
    
    markdown_data = {}
    
    if income_md_path.exists():
        with open(income_md_path, "r", encoding="utf-8") as f:
            markdown_data["income_analysis"] = f.read()
            print(f"  ✓ Loaded: {income_md_path.name}")
    else:
        print(f"  ✗ Warning: {income_md_path.name} not found!")
    
    if debt_md_path.exists():
        with open(debt_md_path, "r", encoding="utf-8") as f:
            markdown_data["debt_analysis"] = f.read()
            print(f"  ✓ Loaded: {debt_md_path.name}")
    else:
        print(f"  ✗ Warning: {debt_md_path.name} not found!")
    
    return markdown_data


def load_spring_eq_files(loan_id="1000182277"):
    """Load Spring EQ JSON files"""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        return {}
    
    spring_data = {}
    
    for json_file in json_dir.glob("*.json"):
        if "spring" in json_file.name.lower():
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    spring_data[json_file.name] = data
                    print(f"  ✓ Loaded: {json_file.name}")
                except json.JSONDecodeError as e:
                    print(f"  ✗ Warning: Could not parse {json_file.name}: {e}")
    
    return spring_data


def load_all_source_json_files(loan_id="1000182277"):
    """Load all source document JSON files for reference"""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        return {}
    
    all_data = {}
    
    for json_file in json_dir.glob("*.json"):
        # Exclude Spring EQ files (already loaded separately)
        if "spring" not in json_file.name.lower():
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    all_data[json_file.name] = data
                except json.JSONDecodeError as e:
                    print(f"  ✗ Warning: Could not parse {json_file.name}: {e}")
    
    print(f"  ✓ Loaded {len(all_data)} source document JSON files")
    
    return all_data


def create_dti_reconciliation_report():
    """
    Create a comprehensive DTI reconciliation report comparing independent analysis with Spring EQ
    """
    
    print("\n" + "="*60)
    print("DTI RECONCILIATION ANALYSIS")
    print("="*60)
    
    print("\nLoading independent agent analysis...")
    markdown_files = load_markdown_files()
    
    if not markdown_files.get("income_analysis") or not markdown_files.get("debt_analysis"):
        print("\nError: Missing required markdown files!")
        print("Please run income_verification_2turn.py and debt_verification_2turn.py first.")
        return
    
    print("\nLoading Spring EQ underwriting worksheet...")
    spring_documents = load_spring_eq_files()
    
    if not spring_documents:
        print("\nWarning: No Spring EQ documents found!")
        return
    
    print("\nLoading source document JSONs for reference...")
    source_documents = load_all_source_json_files()
    
    print(f"\n{'='*60}")
    print("Creating DTI reconciliation report...")
    print(f"{'='*60}\n")
    
    # Convert all data to JSON strings for the prompt
    spring_json = json.dumps(spring_documents, indent=2)
    source_json = json.dumps(source_documents, indent=2)
    
    client = AzureOpenAI(
        api_version=api_version, 
        azure_endpoint=endpoint, 
        api_key=subscription_key
    )
    
    response = client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are an expert Loan Quality Control Analyst specializing in DTI (Debt-to-Income) ratio verification and reconciliation.

**YOUR TASK:**
Compare the independent income and debt analysis with the Spring EQ underwriting worksheet and create a comprehensive DTI reconciliation report.

**FOCUS: Front-End DTI and Back-End DTI ONLY**
- Do NOT calculate or discuss Pro Forma DTI
- Focus on the current DTI ratios as they stand

**YOU HAVE ACCESS TO:**
1. **Independent Income Analysis** - Expert determination of qualifying monthly income
2. **Independent Debt Analysis** - Expert determination of Front-End and Back-End debt obligations
3. **Spring EQ Underwriting Worksheet** - The underwriter's DTI calculations
4. **Source Document JSONs** - Raw document data for spot-checking and verification

**DTI RECONCILIATION FRAMEWORK:**

**FRONT-END DTI (Housing Ratio):**
- Formula: (Proposed PITIA) / Gross Monthly Income × 100
- PITIA = Principal + Interest + Taxes + Insurance + Association dues
- This represents the borrower's housing payment burden

**BACK-END DTI (Total Debt Ratio):**
- Formula: (PITIA + All Monthly Debts) / Gross Monthly Income × 100
- This represents the borrower's total debt burden

**IMPORTANT UNDERWRITING CONCEPTS:**

**CONSERVATIVE (Lower Risk - POSITIVE):**
- Spring EQ uses LOWER income than independent analysis → Reduces risk ✓
- Spring EQ uses HIGHER debt payments than independent analysis → Reduces risk ✓
- Spring EQ calculates HIGHER DTI than independent analysis → More conservative ✓
- Mark these as "Conservative Approach" in GREEN

**AGGRESSIVE (Higher Risk - CONCERN):**
- Spring EQ uses HIGHER income than independent analysis → RED FLAG
- Spring EQ uses LOWER debt payments than independent analysis → RED FLAG
- Spring EQ calculates LOWER DTI than independent analysis → RED FLAG
- Mark these as "Aggressive Assumption" in RED

**NEUTRAL/ACCEPTABLE:**
- Minor rounding differences (0.5% or less)
- Different but acceptable methodologies
- Mark as "Acceptable Variance" in BLUE

**CREATE A PROFESSIONAL HTML REPORT WITH:**

---

## SECTION 1: EXECUTIVE SUMMARY

**Large, Prominent Summary Box:**

### DTI COMPARISON OVERVIEW

| Metric | Independent Analysis | Spring EQ Underwriting | Variance | Assessment |
|--------|---------------------|----------------------|----------|------------|
| **Monthly Income** | $X,XXX | $X,XXX | $XXX (±X%) | Conservative/Neutral/Aggressive |
| **Front-End Debt (PITIA)** | $X,XXX | $X,XXX | $XXX (±X%) | Conservative/Neutral/Aggressive |
| **Back-End Debt (Total)** | $X,XXX | $X,XXX | $XXX (±X%) | Conservative/Neutral/Aggressive |
| **Front-End DTI** | XX.XX% | XX.XX% | ±X.XX% | Conservative/Neutral/Aggressive |
| **Back-End DTI** | XX.XX% | XX.XX% | ±X.XX% | Conservative/Neutral/Aggressive |

**Overall Assessment:**
[1-2 sentences: Is Spring EQ conservative, neutral, or aggressive overall? What's the net risk impact?]

**Key Findings:**
- [Bullet point 1: Most significant variance]
- [Bullet point 2: Any red flags]
- [Bullet point 3: Overall quality of underwriting]

---

## SECTION 2: INCOME RECONCILIATION

### Independent Analysis Income Determination:
- **Qualifying Monthly Income:** $X,XXX
- **Methodology:** [Summarize how independent agent calculated this]
- **Key Components:**
  * Base Salary: $X,XXX
  * Bonus/OT/Commission (2-yr avg): $XXX
  * Other Income: $XXX
- **Source Documents:** [List key documents cited]

### Spring EQ Income Used:
- **Monthly Income:** $X,XXX
- **Source:** [From Spring EQ worksheet]

### Variance Analysis:
- **Difference:** $XXX (±X.X%)
- **Root Cause:** [Why is there a difference?]
  * Is Spring EQ using different income sources?
  * Is Spring EQ using different time periods?
  * Is Spring EQ excluding certain income?
  * Is Spring EQ being conservative or aggressive?
- **Verification:** [Cross-check against source documents]
- **Risk Assessment:** [Conservative/Neutral/Aggressive]
- **Recommendation:** [Accept/Question/Require Explanation]

---

## SECTION 3: FRONT-END DTI RECONCILIATION

### Independent Analysis Front-End:

**Housing Payment (PITIA):**
| Component | Amount | Source |
|-----------|--------|--------|
| Principal & Interest | $X,XXX | [document] |
| Property Taxes | $XXX | [document] |
| Homeowners Insurance | $XXX | [document] |
| HOA/Condo Fees | $XXX | [document] |
| **Total PITIA** | **$X,XXX** | |

**Front-End DTI Calculation:**
- PITIA: $X,XXX
- Gross Monthly Income: $X,XXX
- **Front-End DTI:** $X,XXX / $X,XXX × 100 = **XX.XX%**

### Spring EQ Front-End:

**Housing Payment (PITIA):**
| Component | Amount | Source |
|-----------|--------|--------|
| Principal & Interest | $X,XXX | [Spring EQ worksheet] |
| Property Taxes | $XXX | [Spring EQ worksheet] |
| Homeowners Insurance | $XXX | [Spring EQ worksheet] |
| HOA/Condo Fees | $XXX | [Spring EQ worksheet] |
| **Total PITIA** | **$X,XXX** | |

**Front-End DTI:**
- PITIA: $X,XXX
- Gross Monthly Income: $X,XXX
- **Front-End DTI:** XX.XX%

### Component-by-Component Comparison:

| Component | Independent | Spring EQ | Variance | Assessment |
|-----------|------------|-----------|----------|------------|
| P&I | $X,XXX | $X,XXX | $XX | [Analysis] |
| Taxes | $XXX | $XXX | $XX | [Analysis] |
| Insurance | $XXX | $XXX | $XX | [Analysis] |
| HOA | $XXX | $XXX | $XX | [Analysis] |
| **Total PITIA** | **$X,XXX** | **$X,XXX** | **$XX** | [Analysis] |
| Income | $X,XXX | $X,XXX | $XX | [Analysis] |
| **Front-End DTI** | **XX.XX%** | **XX.XX%** | **±X.XX%** | **[Final Assessment]** |

**Variance Explanation:**
[Detailed explanation of why Front-End DTI differs between independent analysis and Spring EQ]

---

## SECTION 4: BACK-END DTI RECONCILIATION

### Independent Analysis Back-End:

**Total Monthly Obligations:**
| Debt Type | Monthly Payment | Source |
|-----------|----------------|--------|
| PITIA (Housing) | $X,XXX | [Above] |
| Mortgage/HELOC | $X,XXX | [document] |
| Auto Loan(s) | $XXX | [document] |
| Student Loans | $XXX | [document] |
| Credit Cards | $XXX | [document] |
| Other Installment | $XXX | [document] |
| Child Support/Alimony | $XXX | [document] |
| **Total Monthly Debt** | **$X,XXX** | |

**Back-End DTI Calculation:**
- Total Monthly Debt: $X,XXX
- Gross Monthly Income: $X,XXX
- **Back-End DTI:** $X,XXX / $X,XXX × 100 = **XX.XX%**

### Spring EQ Back-End:

**Total Monthly Obligations:**
| Debt Type | Monthly Payment | Source |
|-----------|----------------|--------|
| PITIA (Housing) | $X,XXX | [Spring EQ] |
| [List all debts] | $XXX | [Spring EQ] |
| **Total Monthly Debt** | **$X,XXX** | |

**Back-End DTI:**
- Total Monthly Debt: $X,XXX
- Gross Monthly Income: $X,XXX
- **Back-End DTI:** XX.XX%

### Debt-by-Debt Comparison:

| Debt/Creditor | Independent | Spring EQ | Variance | Assessment |
|---------------|------------|-----------|----------|------------|
| PITIA | $X,XXX | $X,XXX | $XX | [Analysis] |
| [Creditor 1] | $XXX | $XXX | $XX | [Analysis] |
| [Creditor 2] | $XXX | $XXX | $XX | [Analysis] |
| [etc.] | | | | |
| **Total Debt** | **$X,XXX** | **$X,XXX** | **$XX** | [Analysis] |
| Income | $X,XXX | $X,XXX | $XX | [Analysis] |
| **Back-End DTI** | **XX.XX%** | **XX.XX%** | **±X.XX%** | **[Final Assessment]** |

**Variance Explanation:**
[Detailed explanation of why Back-End DTI differs]

**Missing or Excluded Debts:**
- Debts in Independent Analysis but NOT in Spring EQ: [List with concern level]
- Debts in Spring EQ but NOT in Independent Analysis: [List with explanation]

---

## SECTION 5: SOURCE DOCUMENT VERIFICATION

**Spot-Check Key Variances Against Source Documents:**

For significant discrepancies, verify against actual source documents:

**[Variance Item 1]:**
- Independent Analysis says: $XXX
- Spring EQ says: $XXX
- **Source Document Check:** [What does the actual credit report/paystub/tax bill show?]
- **Conclusion:** [Which one is correct? Or are both acceptable?]

[Repeat for each significant variance]

---

## SECTION 6: RISK ASSESSMENT

**Conservative Elements (Positive):**
- [List all areas where Spring EQ is more conservative than independent analysis]
- Net impact: [Calculate cumulative effect on DTI]

**Aggressive Elements (Concerns):**
- [List all areas where Spring EQ is less conservative than independent analysis]
- Net impact: [Calculate cumulative effect on DTI]

**Acceptable Variances:**
- [List minor differences that are within acceptable bounds]

**Net Risk Assessment:**
- Overall, is Spring EQ underwriting conservative, neutral, or aggressive?
- What is the net impact on DTI ratios?
- Are the DTI ratios within acceptable lending guidelines?
- Are there material concerns that require resolution?

---

## SECTION 7: LENDING GUIDELINE COMPLIANCE

**Typical DTI Guidelines:**
- Conventional: Front-End ≤ 28%, Back-End ≤ 43%
- FHA: Front-End ≤ 31%, Back-End ≤ 43%
- VA: Back-End ≤ 41%
- Non-QM: Varies

**Independent Analysis DTI:**
- Front-End: XX.XX% → [Pass/Fail] for [loan type]
- Back-End: XX.XX% → [Pass/Fail] for [loan type]

**Spring EQ DTI:**
- Front-End: XX.XX% → [Pass/Fail] for [loan type]
- Back-End: XX.XX% → [Pass/Fail] for [loan type]

**Guideline Impact:**
- [Does the variance affect loan approval?]
- [Are compensating factors needed?]

---

## SECTION 8: RECOMMENDATIONS

**1. Items to Accept:**
- [List reconciled items that are acceptable]

**2. Items Requiring Clarification:**
- [List items where Spring EQ should explain their methodology]

**3. Items Requiring Correction:**
- [List items where Spring EQ appears to have errors]

**4. Items Requiring Additional Documentation:**
- [List items where more source documents are needed]

**5. Critical Issues:**
- [List any RED FLAG items that must be resolved before loan approval]

---

**COLOR CODING:**
- **DARK GREEN** - Conservative (Spring EQ higher DTI = more conservative)
- **LIGHT GREEN** - Match or acceptable variance
- **YELLOW** - Minor discrepancy requiring clarification
- **ORANGE** - Moderate concern requiring attention
- **RED** - Major discrepancy or aggressive assumption
- **BLUE** - Informational/neutral note

Return ONLY the complete HTML document (starting with <!DOCTYPE html>), no other text."""
            },
            {
                "role": "user",
                "content": f"""Please create a comprehensive DTI reconciliation report comparing the independent analysis with Spring EQ underwriting.

**INDEPENDENT INCOME ANALYSIS:**
{markdown_files['income_analysis']}

**INDEPENDENT DEBT ANALYSIS:**
{markdown_files['debt_analysis']}

**SPRING EQ UNDERWRITING WORKSHEET:**
{spring_json}

**SOURCE DOCUMENT JSONS (for verification):**
{source_json}

Focus on Front-End DTI and Back-End DTI only. Compare independent agent determinations with Spring EQ calculations, identify all variances, assess risk (conservative vs aggressive), and provide recommendations."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    reconciliation_html = response.choices[0].message.content
    
    # Save reconciliation report
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "1000182277_dti_reconciliation.html"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reconciliation_html)
    
    print(f"\n{'='*60}")
    print(f"✓ DTI Reconciliation Report saved to: {output_path}")
    print(f"{'='*60}")
    print("\nYou can open the HTML file in your browser to view the report.")


def main():
    """
    Create DTI reconciliation report
    """
    
    print("\n" + "="*60)
    print("DTI RECONCILIATION AGENT")
    print("="*60)
    print("\nThis agent will:")
    print("1. Load independent income analysis (.md)")
    print("2. Load independent debt analysis (.md)")
    print("3. Load Spring EQ underwriting worksheet (.json)")
    print("4. Load source document JSONs for verification")
    print("5. Compare Front-End DTI calculations")
    print("6. Compare Back-End DTI calculations")
    print("7. Identify variances and assess risk")
    print("8. Generate comprehensive HTML reconciliation report")
    
    create_dti_reconciliation_report()
    
    print("\n" + "="*60)
    print("DTI RECONCILIATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
