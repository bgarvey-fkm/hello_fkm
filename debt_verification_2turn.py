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


def load_all_json_files(exclude_spring=False):
    """Load all JSON files from loan_docs_json directory"""
    json_dir = Path("loan_docs_json")
    
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


def load_spring_eq_files():
    """Load only Spring EQ related JSON files"""
    json_dir = Path("loan_docs_json")
    
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


def turn_1_independent_debt_analysis():
    """
    TURN 1: Analyze all documents EXCEPT Spring EQ underwriting worksheet
    Generate independent debt obligation determination
    """
    
    print("\n" + "="*60)
    print("TURN 1: Independent Debt Obligations Analysis")
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
    
    print("\nAnalyzing debt obligations independently...")
    
    response = client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are an expert Debt Obligations Analyst for mortgage lending. You will analyze borrower debt obligations from credit reports and other documentation.

**YOUR TASK:**
Analyze all debt obligations and provide a comprehensive debt analysis including Front-End DTI, Back-End DTI, and Pro Forma DTI calculations.

**CRITICAL: You do NOT have access to any underwriting worksheet. Make your determination based solely on the source documents.**

**Analysis Requirements:**

1. **Identify ALL Debt Obligations from Credit Reports & Documents:**
   - Mortgage/Home Loans (HELOC, First Mortgage, Second Mortgage)
   - Auto Loans/Leases
   - Student Loans
   - Credit Cards (use minimum payment or % of balance per guidelines)
   - Personal Loans
   - Installment Loans
   - Child Support/Alimony (court-ordered)
   - Other Monthly Obligations

2. **For EACH Debt, Extract:**
   - Creditor Name
   - Account Type
   - Current Balance
   - Monthly Payment
   - Interest Rate (if stated)
   - Remaining Term/Months (if available)
   - Account Status (Current, Delinquent, Paid Off)
   - Source Document (exact document name and date)

3. **Interest Rate Estimation (if not stated):**
   For debts where rate is not explicitly stated, use financial formulas to estimate:
   
   **Formula: Use Present Value of Annuity**
   - PV = PMT × [(1 - (1 + r)^-n) / r]
   - Where: PV = Current Balance, PMT = Monthly Payment, n = Remaining Months, r = Monthly Interest Rate
   - Solve for r (annual rate = r × 12)
   
   **Methodology:**
   - Auto Loans: Typical range 3-8%, use payment/balance/term to estimate
   - Credit Cards: Typical range 15-25%, estimate from minimum payment patterns
   - Student Loans: Federal (3-7%) vs Private (5-12%)
   - Personal Loans: Typical range 6-15%
   
   Show your calculation method and assumptions for each estimated rate.

4. **Calculate DTI Ratios:**

   **FRONT-END DTI (Housing Ratio):**
   - Formula: (Proposed PITIA) / Gross Monthly Income × 100
   - PITIA = Principal + Interest + Taxes + Insurance + Association Dues
   - Extract proposed loan info from 1003 or loan application
   - Extract property taxes from tax bills
   - Extract insurance estimates if available
   
   **BACK-END DTI (Total Debt Ratio) - CRITICAL CONCEPT:**
   
   **CURRENT Back-End DTI (Before This Loan):**
   - Formula: (Current Housing Payment + All Current Monthly Debts) / Gross Monthly Income × 100
   - This shows the borrower's CURRENT debt burden
   
   **PROPOSED Back-End DTI (After This Loan Closes):**
   - Formula: (New PITIA + Remaining Debts After Payoffs) / Gross Monthly Income × 100
   - **THIS IS THE KEY DTI FOR UNDERWRITING APPROVAL**
   
   **UNDERSTANDING DEBT CONSOLIDATION & PAYOFFS:**
   
   Borrowers often take out new loans to:
   1. **Refinance** - Replace existing mortgage with new mortgage
   2. **Cash-Out Refinance** - Replace mortgage AND pay off other debts
   3. **Home Equity Loan/HELOC** - Take out second lien to consolidate debts
   
   **HOW TO IDENTIFY DEBTS THAT WILL BE PAID OFF:**
   
   Look for these indicators in documents:
   
   ✓ **Payoff Letters/Statements:**
     - Any document titled "Payoff Statement" or "Payoff Quote"
     - Shows amount needed to fully satisfy a debt
     - Usually dated and time-sensitive
     - **These debts WILL be paid off at closing**
   
   ✓ **Refinance Scenarios:**
     - If borrower is refinancing, the CURRENT mortgage being replaced will be paid off
     - Look for "refinance" language in 1003 or loan application
     - Current mortgage payment should NOT be included in new Back-End DTI
     - New mortgage payment SHOULD be included
   
   ✓ **Cash-Out or Debt Consolidation:**
     - Look in 1003 "Purpose of Loan" section
     - May state "debt consolidation" or "payoff credit cards"
     - Check if loan amount exceeds property value minus current mortgage = cash out
     - Cash out amount often used to pay off debts listed in payoff letters
   
   ✓ **Explicit Payoff Instructions:**
     - Some documents may list "Debts to be paid off at closing"
     - HUD-1/Closing Disclosure may show payoffs (if available)
     - Form 1003 Section VIII may list debts to be satisfied
   
   ✓ **Credit Report Notations:**
     - Some credit reports flag accounts as "to be paid by mortgage"
     - Look for special status codes
   
   **CRITICAL RULES FOR CALCULATING PROPOSED BACK-END DTI:**
   
   **EXCLUDE from new Back-End DTI:**
   - ✗ Current mortgage being refinanced (old payment drops off)
   - ✗ Any debt with a payoff letter/statement
   - ✗ Any debt explicitly stated as "to be paid at closing"
   - ✗ Second mortgages/HELOCs being paid off in cash-out refi
   - ✗ Credit cards/installment loans listed in payoff documents
   
   **INCLUDE in new Back-End DTI:**
   - ✓ New mortgage payment (PITIA)
   - ✓ All other debts NOT being paid off (auto loans, student loans, etc.)
   - ✓ Credit cards remaining open (minimum payment)
   - ✓ Child support/alimony (ongoing obligations)
   
   **EXAMPLE SCENARIO:**
   
   Current Situation:
   - Current Mortgage: $1,500/month
   - HELOC: $300/month
   - Auto Loan: $400/month
   - Credit Card 1: $100/month
   - Credit Card 2: $75/month
   - Total Current Debt: $2,375/month
   
   New Loan Scenario (Cash-Out Refinance):
   - New Mortgage PITIA: $1,800/month
   - Payoff Letter shows: Current Mortgage ($200k payoff) ✗ EXCLUDE
   - Payoff Letter shows: HELOC ($25k payoff) ✗ EXCLUDE
   - Payoff Letter shows: Credit Card 1 ($5k payoff) ✗ EXCLUDE
   - Auto Loan: Still owed ✓ INCLUDE ($400/month)
   - Credit Card 2: No payoff letter ✓ INCLUDE ($75/month)
   
   **Proposed Back-End Calculation:**
   - New PITIA: $1,800
   - Auto Loan: $400
   - Credit Card 2: $75
   - **Total Proposed Monthly Debt: $2,275**
   - (Note: This is LESS than current $2,375 despite higher mortgage payment)
   
   **DTI Improvement Example:**
   - Income: $6,000/month
   - Current Back-End DTI: $2,375 / $6,000 = 39.58%
   - Proposed Back-End DTI: $2,275 / $6,000 = 37.92%
   - **Improvement: 1.66% reduction in DTI**

5. **Output Format (Markdown):**

# Independent Debt Obligations Analysis

## DETERMINATION SUMMARY

## DETERMINATION SUMMARY

### Front-End DTI (Housing Ratio): [X.XX]%
- Proposed PITIA: $[amount]
- Gross Monthly Income: $[amount]
- Calculation: $[PITIA] / $[income] × 100 = [X.XX]%

### Back-End DTI (Total Debt Ratio - PROPOSED AFTER LOAN CLOSES): [X.XX]%
**This is the key DTI for underwriting approval**
- New PITIA: $[amount]
- Remaining Debts (after payoffs): $[amount]
- **Total Proposed Monthly Debt: $[amount]**
- Gross Monthly Income: $[amount]
- **Calculation: $[total] / $[income] × 100 = [X.XX]%**

### Current Back-End DTI (Before This Loan - For Reference):
- Current Housing Payment: $[amount]
- All Current Debts: $[amount]
- Total Current Monthly Debt: $[amount]
- Gross Monthly Income: $[amount]
- Current DTI: $[total] / $[income] × 100 = [X.XX]%

### DTI Impact:
- **Proposed Back-End DTI: [X.XX]%**
- Current Back-End DTI: [X.XX]%
- **Change: [±X.XX]%** ([Improvement/Increase])

---

## DETAILED DEBT INVENTORY

| Creditor | Type | Balance | Monthly Payment | Interest Rate | Term Remaining | Status | Source |
|----------|------|---------|----------------|---------------|----------------|--------|--------|
| [Name] | Mortgage | $XXX,XXX | $X,XXX | X.XX% | XX months | Current | [doc, date] |
| [Name] | Auto Loan | $XX,XXX | $XXX | X.XX% (estimated) | XX months | Current | [doc, date] |
| [etc.] | | | | | | | |
| **TOTAL** | | **$XXX,XXX** | **$X,XXX** | | | | |

---

## INTEREST RATE CALCULATIONS

### Debts with Stated Rates:
- [Creditor]: [X.XX]% (stated in [document])

### Debts with Estimated Rates:
For debts without explicit rates, calculated using PV of annuity formula:

**[Creditor Name] - [Loan Type]**
- Current Balance: $[amount]
- Monthly Payment: $[amount]
- Estimated Remaining Term: [X] months
- Calculation Method: [explain approach]
- **Estimated Rate: [X.XX]%**
- Rationale: [why this rate is reasonable for this loan type]

[Repeat for each estimated rate]

---

## FRONT-END DTI CALCULATION

### Proposed Housing Payment (PITIA):
- Principal & Interest: $[amount]
  - Source: [1003 application / loan estimate]
- Property Taxes: $[amount]/month
  - Source: [tax bill, date]
  - Calculation: $[annual] ÷ 12 = $[monthly]
- Homeowners Insurance: $[amount]/month
  - Source: [insurance quote / estimate]
- HOA/Condo Fees: $[amount]/month (if applicable)
  - Source: [document]
- **Total PITIA: $[amount]**

### Income:
- Gross Monthly Income: $[amount]
  - Source: [reference to income analysis]

### Front-End DTI:
- $[PITIA] / $[income] × 100 = **[X.XX]%**

---

## BACK-END DTI CALCULATION

### Total Monthly Obligations:
- Proposed PITIA: $[amount]
- Auto Loan(s): $[amount]
- Student Loans: $[amount]
- Credit Cards: $[amount]
- Other Installment Loans: $[amount]
- [Other debts]: $[amount]
- **Total Monthly Debt: $[amount]**

### Back-End DTI:
- $[total debt] / $[income] × 100 = **[X.XX]%**

---

## DEBT PAYOFF ANALYSIS (CRITICAL FOR BACK-END DTI)

### Purpose of This Loan:
- [Refinance / Cash-Out Refinance / Purchase / Home Equity]
- Source: [Form 1003 / Loan Application]
- Loan Amount: $[amount]
- Property Value: $[amount]
- Cash Out Amount (if applicable): $[amount]

### Debts Being Paid Off with Loan Proceeds:

**THESE DEBTS ARE EXCLUDED FROM PROPOSED BACK-END DTI**

| Creditor | Type | Current Monthly Payment | Payoff Amount | Evidence | Status |
|----------|------|------------------------|---------------|----------|--------|
| [Name] | Current Mortgage | $X,XXX | $XXX,XXX | Payoff Letter [date] | ✗ EXCLUDE |
| [Name] | HELOC | $XXX | $XX,XXX | Payoff Letter [date] | ✗ EXCLUDE |
| [Name] | Credit Card 1 | $XXX | $X,XXX | Payoff Letter [date] | ✗ EXCLUDE |
| [etc.] | | | | | |
| **TOTAL PAID OFF** | | **$X,XXX** | **$XXX,XXX** | | |

**Evidence Sources:**
- [List all payoff letters/statements found]
- [Note if refinance scenario (old mortgage automatically excluded)]
- [Note if Form 1003 lists "debts to be satisfied"]

### Debts Remaining After This Loan Closes:

**THESE DEBTS ARE INCLUDED IN PROPOSED BACK-END DTI**

| Creditor | Type | Monthly Payment | Reason Included |
|----------|------|----------------|-----------------|
| New Mortgage | PITIA | $X,XXX | ✓ NEW LOAN PAYMENT |
| [Name] | Auto Loan | $XXX | ✓ No payoff letter, still owed |
| [Name] | Student Loan | $XXX | ✓ No payoff letter, still owed |
| [Name] | Credit Card 2 | $XXX | ✓ Remains open, no payoff |
| [etc.] | | | |
| **TOTAL REMAINING** | | **$X,XXX** | |

### Proposed Back-End DTI Calculation (After Loan Closes):

**This is the DTI used for loan approval**

- New PITIA: $[amount]
- Remaining Debts (after payoffs): $[amount]
- **Total Proposed Monthly Debt: $[amount]**
- Gross Monthly Income: $[amount]
- **Proposed Back-End DTI: $[amount] / $[income] × 100 = [X.XX]%**

### Current Back-End DTI (Before This Loan - For Comparison):

- Current Housing Payment: $[amount]
- Current Auto/Student/CC Payments: $[amount]
- Debts That Will Be Paid Off: $[amount]
- **Total Current Monthly Debt: $[amount]**
- Gross Monthly Income: $[amount]
- **Current Back-End DTI: [X.XX]%**

### DTI Impact Summary:

- **Current Back-End DTI:** [X.XX]%
- **Proposed Back-End DTI:** [X.XX]%
- **Change:** [±X.XX]%
- **Result:** [DTI Improves / DTI Increases / DTI Stays Same]

**Explanation:**
[Explain why DTI changed - e.g., "Borrower is consolidating $X,XXX in monthly debt payments into the new mortgage, reducing total monthly obligations by $XXX despite a higher housing payment."]

---

## DOCUMENTATION REVIEW

### Credit Reports Reviewed:
- [Credit bureau]: [date], [borrower name]
- Key findings: [list accounts, balances, payment history]

### Payoff Letters/Statements:
- [List all payoff documents with dates]

### Form 1003 Review:
- Debts listed by borrower: [summarize]
- Comparison with credit report: [note discrepancies]

---

## DEBT RECONCILIATION

### Discrepancies Found:
- Credit Report shows: [X debts totaling $X]
- Form 1003 shows: [Y debts totaling $Y]
- Variance: $[difference]
- Explanation: [analyze why different]

---

## CONFIDENCE LEVEL

[High/Medium/Low] - [Explain based on documentation quality]

Factors:
- Credit report date: [recent/old]
- Payoff letters: [available/not available]
- Interest rate data: [X% stated, Y% estimated]

---

## RECOMMENDATIONS

1. Additional Documentation Needed:
   - [List any missing payoff letters]
   - [List any debts needing clarification]

2. Rate Confirmation:
   - [List debts where estimated rate should be confirmed]

3. Payoff Strategy:
   - [Recommend which debts to pay off for best DTI]

---

Return your analysis in clean Markdown format. Be thorough, show all calculations, and cite specific documents."""
            },
            {
                "role": "user",
                "content": f"""Please analyze these loan documents and provide your independent debt obligations analysis.

**IMPORTANT: You do NOT have access to any underwriting worksheet. Make your determination based solely on the source documents provided.**

Here are all the loan documents in JSON format:

{documents_json}

Provide your complete analysis in Markdown format with all DTI calculations."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    turn1_markdown = response.choices[0].message.content
    
    # Save Turn 1 analysis to markdown file
    output_dir = Path("loan_summary")
    output_dir.mkdir(exist_ok=True)
    turn1_path = output_dir / "turn1_independent_debt_analysis.md"
    
    with open(turn1_path, "w", encoding="utf-8") as f:
        f.write(turn1_markdown)
    
    print(f"\n✓ Turn 1 Independent Debt Analysis saved to: {turn1_path}")
    
    return turn1_markdown


def turn_2_reconciliation(turn1_analysis):
    """
    TURN 2: Load Spring EQ underwriting worksheet and reconcile with Turn 1 analysis
    Create comparison report showing discrepancies in debt calculations
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
    
    print("\nReconciling independent debt analysis with Spring EQ underwriting...")
    
    response = client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are an expert Loan Quality Control Analyst specializing in debt obligation verification. You will compare an independent debt analysis against a Spring EQ underwriting worksheet.

**YOUR TASK:**
1. Review the independent debt analysis (Turn 1)
2. Review the Spring EQ underwriting worksheet
3. Compare debt calculations, DTI ratios, and payoff assumptions
4. Identify ALL discrepancies
5. Assess whether discrepancies represent conservative or aggressive underwriting

**IMPORTANT CONCEPTS:**

**CONSERVATIVE (Lower Risk - POSITIVE):**
- Spring EQ includes HIGHER debt payments than documented → Good, more conservative
- Spring EQ uses HIGHER DTI ratios → Good, stress testing more
- Spring EQ assumes FEWER debts will be paid off → Good, more conservative cash requirement
- Spring EQ uses HIGHER interest rate estimates → Good, conservative assumption
- Mark as "Conservative Approach" in GREEN

**AGGRESSIVE (Higher Risk - CONCERN):**
- Spring EQ excludes debts shown on credit report → RED FLAG, understating obligations
- Spring EQ uses LOWER debt payments than documented → RED FLAG
- Spring EQ calculates LOWER DTI than Turn 1 → RED FLAG, understating risk
- Spring EQ assumes MORE debts paid off than documented → RED FLAG, overstating improvement
- Spring EQ uses LOWER interest rates than reasonable → RED FLAG
- Mark as "Aggressive Assumption" in RED

**NEUTRAL/ACCEPTABLE:**
- Minor differences in credit card minimum payment calculations
- Different but acceptable estimation methods
- Rounding differences
- Mark as "Acceptable Variance" in BLUE

Create a professional HTML report with:

**SECTION 1: EXECUTIVE SUMMARY - DTI COMPARISON**

Side-by-side comparison box:
| Metric | Turn 1 Independent Analysis | Spring EQ Underwriting | Variance | Assessment |
|--------|----------------------------|----------------------|----------|------------|
| Front-End DTI | XX.XX% | XX.XX% | ±X.XX% | Conservative/Neutral/Aggressive |
| Back-End DTI | XX.XX% | XX.XX% | ±X.XX% | Conservative/Neutral/Aggressive |
| Pro Forma DTI | XX.XX% | XX.XX% | ±X.XX% | Conservative/Neutral/Aggressive |
| Total Monthly Debt | $X,XXX | $X,XXX | $XXX | Conservative/Neutral/Aggressive |

**Overall Assessment:** [Does Spring EQ underwriting use conservative, neutral, or aggressive debt assumptions?]

---

**SECTION 2: DETAILED DEBT-BY-DEBT COMPARISON**

| Creditor | Account Type | Turn 1 Payment | Spring EQ Payment | Variance | Turn 1 Rate | Spring EQ Rate | Assessment |
|----------|--------------|----------------|-------------------|----------|-------------|----------------|------------|
| [Name] | Mortgage | $X,XXX | $X,XXX | $XX | X.XX% | X.XX% | Match/Conservative/Aggressive |
| [Name] | Auto | $XXX | $XXX | $XX | X.XX% | X.XX% | Match/Conservative/Aggressive |
| [etc.] | | | | | | | |
| **TOTAL** | | **$X,XXX** | **$X,XXX** | **$XXX** | | | |

---

**SECTION 3: DISCREPANCY ANALYSIS**

For each significant discrepancy:

**Discrepancy #1: [Debt/Account Name]**
- **Turn 1 Analysis:** 
  - Monthly Payment: $[amount]
  - Interest Rate: [X.XX]% ([stated/estimated])
  - Source: [document, date]
  - Methodology: [how calculated]

- **Spring EQ Underwriting:**
  - Monthly Payment: $[amount]
  - Interest Rate: [X.XX]% (if shown)
  - Source: [their document]

- **Variance:** $[difference] ([percentage]%)

- **Root Cause Analysis:**
  - [Why does this difference exist?]
  - [Is one using different source data?]
  - [Is one using different calculation method?]

- **Risk Assessment:** 
  - [Conservative if Spring EQ higher]
  - [Aggressive if Spring EQ lower]
  - [Neutral if acceptable methodology difference]

- **Recommendation:** [Accept/Question/Request Documentation]

---

**SECTION 4: INTEREST RATE COMPARISON**

Compare interest rate assumptions:

| Debt | Turn 1 Rate | Method | Spring EQ Rate | Method | Variance | Assessment |
|------|-------------|--------|----------------|--------|----------|------------|
| [Name] | X.XX% | Stated | X.XX% | Stated | Match | ✓ |
| [Name] | X.XX% | Estimated | X.XX% | Estimated | ±X.XX% | Conservative/Aggressive |

---

**SECTION 5: PAYOFF ASSUMPTIONS**

**Turn 1 Identified Payoffs:**
| Creditor | Payment | Payoff Amount | Source |
|----------|---------|---------------|--------|
| [Name] | $X,XXX | $XXX,XXX | [document] |
| **TOTAL** | **$X,XXX** | **$XXX,XXX** | |

**Spring EQ Identified Payoffs:**
| Creditor | Payment | Payoff Amount | Source |
|----------|---------|---------------|--------|
| [Name] | $X,XXX | $XXX,XXX | [document] |
| **TOTAL** | **$X,XXX** | **$XXX,XXX** | |

**Variance Analysis:**
- Debts Turn 1 says will be paid off but Spring EQ doesn't: [list]
- Debts Spring EQ says will be paid off but Turn 1 doesn't: [list]
- Impact on Pro Forma DTI: [calculate difference]

---

**SECTION 6: DTI CALCULATION RECONCILIATION**

**Front-End DTI:**
| Component | Turn 1 | Spring EQ | Variance |
|-----------|--------|-----------|----------|
| Principal & Interest | $X,XXX | $X,XXX | $XX |
| Property Tax | $XXX | $XXX | $XX |
| Insurance | $XXX | $XXX | $XX |
| HOA/Other | $XXX | $XXX | $XX |
| **Total PITIA** | **$X,XXX** | **$X,XXX** | **$XX** |
| Gross Income | $X,XXX | $X,XXX | $XX |
| **Front-End DTI** | **XX.XX%** | **XX.XX%** | **±X.XX%** |

**Back-End DTI:**
| Component | Turn 1 | Spring EQ | Variance |
|-----------|--------|-----------|----------|
| PITIA | $X,XXX | $X,XXX | $XX |
| Other Debts | $X,XXX | $X,XXX | $XX |
| **Total** | **$X,XXX** | **$X,XXX** | **$XX** |
| Gross Income | $X,XXX | $X,XXX | $XX |
| **Back-End DTI** | **XX.XX%** | **XX.XX%** | **±X.XX%** |

---

**SECTION 7: MISSING OR EXCLUDED DEBTS**

**Debts in Turn 1 but NOT in Spring EQ:**
- [List any debts Turn 1 found that Spring EQ didn't include]
- [Assess if these are legitimate exclusions or errors]

**Debts in Spring EQ but NOT in Turn 1:**
- [List any debts Spring EQ included that Turn 1 didn't find]
- [Assess source and legitimacy]

---

**SECTION 8: OVERALL QUALITY ASSESSMENT**

**Conservative Elements (Positive):**
- [List all areas where Spring EQ is more conservative]

**Aggressive Elements (Concerns):**
- [List all areas where Spring EQ is less conservative]

**Acceptable Variances:**
- [List minor differences that are within reason]

**Net Assessment:**
- Is Spring EQ underwriting conservative, neutral, or aggressive overall?
- What is the net impact on DTI?
- Are there material concerns?

---

**SECTION 9: RECOMMENDATIONS**

1. **Accept As-Is:**
   - [List items that are acceptable]

2. **Request Clarification:**
   - [List items needing explanation]

3. **Request Additional Documentation:**
   - [List items needing more proof]

4. **Override/Adjust:**
   - [List items that should be changed]

5. **Red Flags Requiring Resolution:**
   - [List any major concerns that must be addressed]

---

Use color coding throughout:
- **DARK GREEN** - Conservative approach (Spring EQ higher obligations than Turn 1)
- **LIGHT GREEN** - Match or acceptable variance
- **YELLOW** - Minor discrepancy, needs clarification
- **ORANGE** - Moderate concern requiring attention
- **RED** - Major discrepancy or aggressive assumption
- **BLUE** - Informational/neutral

Return ONLY the complete HTML document (starting with <!DOCTYPE html>), no other text."""
            },
            {
                "role": "user",
                "content": f"""Please reconcile the independent debt analysis with the Spring EQ underwriting worksheet.

**TURN 1 INDEPENDENT DEBT ANALYSIS:**
{turn1_analysis}

**SPRING EQ UNDERWRITING DOCUMENTS:**
{spring_json}

Create a comprehensive reconciliation report comparing debt calculations, DTI ratios, interest rate assumptions, and payoff scenarios."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    reconciliation_html = response.choices[0].message.content
    
    # Save Turn 2 reconciliation report
    output_dir = Path("loan_summary")
    turn2_path = output_dir / "turn2_debt_reconciliation.html"
    
    with open(turn2_path, "w", encoding="utf-8") as f:
        f.write(reconciliation_html)
    
    print(f"\n✓ Turn 2 Debt Reconciliation Report saved to: {turn2_path}")


def main():
    """
    Run the independent debt verification analysis
    """
    
    print("\n" + "="*60)
    print("INDEPENDENT DEBT OBLIGATIONS VERIFICATION")
    print("="*60)
    print("\nThis process will:")
    print("1. Analyze debt obligations from source documents (excluding Spring EQ)")
    print("2. Calculate Front-End and Back-End monthly debt service")
    print("3. Estimate interest rates where not stated")
    print("4. Identify debts to be paid off with loan proceeds")
    print("5. Generate markdown report")
    
    # Independent analysis without Spring EQ worksheet
    turn1_result = turn_1_independent_debt_analysis()
    
    if not turn1_result:
        print("\nError in analysis. Aborting.")
        return
    
    print("\n" + "="*60)
    print("DEBT VERIFICATION COMPLETE")
    print("="*60)
    print("\nGenerated file:")
    print("  - loan_summary/turn1_independent_debt_analysis.md")
    print("\nThis report contains Front-End and Back-End debt service determinations.")


if __name__ == "__main__":
    main()
