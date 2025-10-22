"""
Income Evaluation Agent

Analyzes borrower employment history and income from semantic JSON files.
Extracts income sources, amounts, documentation, stability, and DTI contribution.

Usage:
    python agents/income_evaluation_agent.py <loan_id>

Example:
    python agents/income_evaluation_agent.py 1000182005
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")


def load_semantic_json_files(loan_id: str) -> list[dict]:
    """Load all semantic JSON files for the loan."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return []
    
    json_files = list(semantic_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No semantic JSON files found in {semantic_dir}")
        return []
    
    print(f"\n📂 Loading {len(json_files)} semantic JSON files...")
    
    documents = []
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Include filename for reference
                data['source_filename'] = json_file.name
                documents.append(data)
                print(f"   ✓ {json_file.name}")
        except Exception as e:
            print(f"   ✗ Error loading {json_file.name}: {e}")
    
    return documents


def analyze_income_with_llm(loan_id: str, semantic_docs: list[dict]) -> dict:
    """Use LLM to extract comprehensive income analysis from semantic documents."""
    
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
    
    system_prompt = """You are an expert mortgage underwriter specializing in income analysis and verification.

Your task is to analyze borrower employment history and income from mortgage loan documents.

Extract and analyze:

1. EMPLOYMENT HISTORY (for each borrower and co-borrower):
   - Current employer name and address
   - Position/job title
   - Employment type (full-time, part-time, self-employed, contract, seasonal)
   - Hire date and tenure (years/months)
   - Business ownership percentage (if applicable)
   - Employment status (active, retired, unemployed)
   - Previous employers (if documented)

2. INCOME SOURCES (categorize each income stream):
   - W-2 Salary: Base salary from employment
   - Hourly + Overtime: Hourly wages with overtime earnings
   - Salary + Bonus: Base salary with annual/quarterly bonuses
   - Salary + Commission: Base salary with commission earnings
   - Commission Only: 100% commission-based income
   - Self-Employment: Business income (sole prop, partnership, S-corp, C-corp)
   - Rental Income: Investment property cash flow
   - Social Security: Retirement or disability benefits
   - Pension/Retirement: Pension, 401k distributions, IRA distributions
   - Investment Income: Interest, dividends, capital gains
   - Alimony/Child Support: Court-ordered payments received
   - Military Pay: Active duty, reserves, VA benefits
   - Disability Income: Short-term or long-term disability
   - Other Income: Any other documented income sources

3. INCOME AMOUNTS (for each source):
   - Monthly gross income
   - Annual income
   - Year-to-date (YTD) earnings
   - Historical income (prior years if available)
   - Income trends (increasing, stable, declining)

4. INCOME DOCUMENTATION:
   - Paystubs: Number of paystubs, date range, YTD figures
   - W-2 Forms: Tax years provided
   - Tax Returns: Years provided (1040, Schedule C, K-1, etc.)
   - Verification of Employment (VOE): Date, employer confirmation
   - Bank Statements: Showing deposits, direct deposits
   - Award Letters: Social Security, pension, disability
   - 1099 Forms: 1099-MISC, 1099-NEC, 1099-R, 1099-INT, 1099-DIV
   - Profit & Loss Statements: For self-employed
   - Business Tax Returns: For self-employed
   - Rental Agreements: Lease documents for rental income
   - Court Orders: Alimony/child support documentation

5. INCOME STABILITY & CONTINUANCE:
   - Length of time in current position
   - Length of time in industry/field
   - Income variability (consistent vs. fluctuating)
   - Seasonal income patterns
   - Likelihood of continuance (3+ years)
   - Employment gaps or changes
   - Commission/bonus history and reliability

6. INCOME CALCULATION FOR DTI:
   - Total monthly qualifying income (all borrowers combined)
   - Income excluded from qualification (why?)
   - Variable income averaging methodology
   - Self-employment income calculation
   - Rental income calculation (75% of gross rents)
   - Other income adjustments

7. INCOME STRENGTHS:
   - Stable employment with long tenure
   - Multiple income sources (diversification)
   - Increasing income trend
   - Well-documented income
   - Strong VOE confirmation
   - Professional/technical position
   - Low income variability

8. INCOME CONCERNS:
   - Recent job change or short tenure
   - Declining income trend
   - High income variability
   - Limited documentation
   - Self-employment with declining profits
   - Commission income without 2-year history
   - Rental income with high vacancy
   - Seasonal income without continuance
   - Employment gaps
   - Pending retirement
   - Income not likely to continue

Return a detailed JSON object with all findings."""

    user_prompt = f"""Analyze the employment history and income for loan {loan_id}.

Review all semantic documents and extract comprehensive income information.

Semantic Documents:
{json.dumps(semantic_docs, indent=2)}

Return a JSON object with this structure:
{{
  "loan_id": "{loan_id}",
  "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
  "borrowers": [
    {{
      "borrower_name": "string",
      "borrower_type": "Primary Borrower|Co-Borrower",
      "current_employment": {{
        "employer_name": "string",
        "employer_address": "string",
        "position": "string",
        "employment_type": "Full-Time|Part-Time|Self-Employed|Contract|Seasonal|Retired|Unemployed",
        "hire_date": "YYYY-MM-DD or string",
        "tenure_years": number,
        "tenure_months": number,
        "business_ownership_percent": number or null,
        "employment_status": "Active|Retired|Unemployed",
        "industry": "string"
      }},
      "previous_employment": [
        {{
          "employer_name": "string",
          "position": "string",
          "start_date": "string",
          "end_date": "string",
          "tenure_years": number
        }}
      ],
      "income_sources": [
        {{
          "income_type": "W-2 Salary|Hourly + Overtime|Salary + Bonus|Salary + Commission|Commission Only|Self-Employment|Rental Income|Social Security|Pension/Retirement|Investment Income|Alimony/Child Support|Military Pay|Disability Income|Other",
          "description": "string",
          "monthly_amount": number,
          "annual_amount": number,
          "ytd_amount": number or null,
          "prior_year_amounts": [
            {{"year": number, "amount": number}}
          ],
          "income_trend": "Increasing|Stable|Declining|Variable",
          "is_qualifying": boolean,
          "exclusion_reason": "string or null"
        }}
      ],
      "total_monthly_income": number,
      "total_annual_income": number
    }}
  ],
  "combined_qualifying_income": {{
    "total_monthly_gross": number,
    "base_salary_wages": number,
    "overtime": number,
    "bonus": number,
    "commission": number,
    "self_employment": number,
    "rental_income": number,
    "social_security": number,
    "pension_retirement": number,
    "investment_income": number,
    "other_income": number
  }},
  "income_documentation": {{
    "paystubs": {{
      "provided": boolean,
      "count": number,
      "date_range": "string",
      "ytd_available": boolean
    }},
    "w2_forms": {{
      "provided": boolean,
      "tax_years": [number]
    }},
    "tax_returns": {{
      "provided": boolean,
      "years": [number],
      "forms_provided": ["1040", "Schedule C", "Schedule E", "K-1", etc.]
    }},
    "voe_voi": {{
      "provided": boolean,
      "verification_date": "string or null",
      "method": "Verbal|Written|Third-Party|None"
    }},
    "bank_statements": {{
      "provided": boolean,
      "months": number,
      "shows_deposits": boolean
    }},
    "award_letters": {{
      "provided": boolean,
      "types": ["Social Security", "Pension", "Disability", etc.]
    }},
    "form_1099": {{
      "provided": boolean,
      "types": ["1099-MISC", "1099-NEC", "1099-R", etc.]
    }},
    "profit_loss_statements": {{
      "provided": boolean,
      "periods": ["string"]
    }},
    "business_tax_returns": {{
      "provided": boolean,
      "years": [number],
      "entity_type": "Sole Prop|Partnership|S-Corp|C-Corp|None"
    }},
    "rental_agreements": {{
      "provided": boolean,
      "properties": number
    }},
    "other_documentation": ["string"]
  }},
  "income_stability_assessment": {{
    "employment_stability": "Excellent|Good|Fair|Poor",
    "income_consistency": "Very Consistent|Consistent|Variable|Highly Variable",
    "income_trend": "Strongly Increasing|Increasing|Stable|Declining|Strongly Declining",
    "continuance_likelihood": "Very Likely|Likely|Uncertain|Unlikely",
    "documentation_quality": "Excellent|Good|Adequate|Insufficient",
    "overall_income_strength": "Strong|Moderate|Weak"
  }},
  "income_strengths": [
    "string (specific positive findings)"
  ],
  "income_concerns": [
    "string (specific concerns or risks)"
  ],
  "underwriting_notes": {{
    "total_qualifying_income": number,
    "income_averaging_applied": boolean,
    "self_employment_adjustments": "string or null",
    "rental_income_calculation": "string or null",
    "variable_income_treatment": "string or null",
    "income_documentation_notes": "string",
    "employment_verification_status": "Verified|Pending|Not Verified",
    "income_continuance_assessment": "string"
  }},
  "recommendation": "Acceptable|Acceptable with Conditions|Unacceptable",
  "recommendation_details": "string (detailed explanation)"
}}"""

    print(f"\n🤖 Analyzing income with Azure OpenAI ({AZURE_OPENAI_DEPLOYMENT})...")
    
    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=16000
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Add metadata
        analysis['metadata'] = {
            'agent': 'income_evaluation_agent',
            'version': '1.0',
            'model': AZURE_OPENAI_DEPLOYMENT,
            'analysis_timestamp': datetime.now().isoformat(),
            'semantic_files_analyzed': len(semantic_docs)
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error during LLM analysis: {e}")
        raise


def save_analysis_report(loan_id: str, analysis: dict) -> str:
    """Save the income analysis report as JSON."""
    reports_dir = Path(f"loan_docs/{loan_id}/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"income_analysis_{loan_id}_{timestamp}.json"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, indent=2, fp=f)
    
    return str(report_path)


def display_income_summary(analysis: dict):
    """Display formatted income analysis summary."""
    print("\n" + "="*80)
    print(f"💼 INCOME ANALYSIS REPORT - Loan {analysis['loan_id']}")
    print("="*80)
    
    # Borrower Employment & Income
    for borrower in analysis.get('borrowers', []):
        print(f"\n{'='*80}")
        print(f"👤 {borrower.get('borrower_name', 'Unknown')} ({borrower.get('borrower_type', 'Unknown')})")
        print(f"{'='*80}")
        
        # Current Employment
        current_emp = borrower.get('current_employment', {})
        if current_emp:
            print(f"\n📋 CURRENT EMPLOYMENT:")
            print(f"   Employer: {current_emp.get('employer_name', 'N/A')}")
            print(f"   Position: {current_emp.get('position', 'N/A')}")
            print(f"   Type: {current_emp.get('employment_type', 'N/A')}")
            print(f"   Status: {current_emp.get('employment_status', 'N/A')}")
            print(f"   Industry: {current_emp.get('industry', 'N/A')}")
            
            tenure_years = current_emp.get('tenure_years', 0)
            tenure_months = current_emp.get('tenure_months', 0)
            print(f"   Tenure: {tenure_years} years, {tenure_months} months")
            
            if current_emp.get('hire_date'):
                print(f"   Hire Date: {current_emp['hire_date']}")
            
            if current_emp.get('business_ownership_percent'):
                print(f"   Ownership: {current_emp['business_ownership_percent']}%")
        
        # Previous Employment
        prev_emp = borrower.get('previous_employment', [])
        if prev_emp:
            print(f"\n📝 PREVIOUS EMPLOYMENT ({len(prev_emp)}):")
            for i, emp in enumerate(prev_emp[:3], 1):  # Show up to 3
                print(f"   {i}. {emp.get('employer_name', 'N/A')} - {emp.get('position', 'N/A')}")
                print(f"      {emp.get('start_date', 'N/A')} to {emp.get('end_date', 'N/A')} ({emp.get('tenure_years', 0)} years)")
        
        # Income Sources
        income_sources = borrower.get('income_sources', [])
        if income_sources:
            print(f"\n💰 INCOME SOURCES ({len(income_sources)}):")
            for source in income_sources:
                income_type = source.get('income_type', 'Unknown')
                monthly = source.get('monthly_amount') or 0
                annual = source.get('annual_amount') or 0
                qualifying = "✓ Qualifying" if source.get('is_qualifying') else "✗ Not Qualifying"
                
                print(f"\n   • {income_type}")
                print(f"     Description: {source.get('description', 'N/A')}")
                print(f"     Monthly: ${monthly:,.2f}")
                print(f"     Annual: ${annual:,.2f}")
                
                ytd = source.get('ytd_amount')
                if ytd:
                    print(f"     YTD: ${ytd:,.2f}")
                
                print(f"     Trend: {source.get('income_trend', 'N/A')}")
                print(f"     Status: {qualifying}")
                
                if source.get('exclusion_reason'):
                    print(f"     Reason: {source['exclusion_reason']}")
                
                # Prior year amounts
                prior_years = source.get('prior_year_amounts', [])
                if prior_years:
                    print(f"     Prior Years:")
                    for year_data in prior_years:
                        year_amount = year_data.get('amount') or 0
                        print(f"       {year_data.get('year')}: ${year_amount:,.2f}")
        
        # Borrower Total Income
        monthly_total = borrower.get('total_monthly_income', 0)
        annual_total = borrower.get('total_annual_income', 0)
        print(f"\n   💵 TOTAL INCOME:")
        print(f"      Monthly: ${monthly_total:,.2f}")
        print(f"      Annual: ${annual_total:,.2f}")
    
    # Combined Qualifying Income
    print(f"\n{'='*80}")
    print(f"💼 COMBINED QUALIFYING INCOME (All Borrowers)")
    print(f"{'='*80}")
    
    combined = analysis.get('combined_qualifying_income', {})
    total_monthly = combined.get('total_monthly_gross', 0)
    
    print(f"\n   Total Monthly Gross: ${total_monthly:,.2f}")
    print(f"   Annual: ${total_monthly * 12:,.2f}")
    
    print(f"\n   BREAKDOWN:")
    breakdown_items = [
        ('Base Salary/Wages', combined.get('base_salary_wages', 0)),
        ('Overtime', combined.get('overtime', 0)),
        ('Bonus', combined.get('bonus', 0)),
        ('Commission', combined.get('commission', 0)),
        ('Self-Employment', combined.get('self_employment', 0)),
        ('Rental Income', combined.get('rental_income', 0)),
        ('Social Security', combined.get('social_security', 0)),
        ('Pension/Retirement', combined.get('pension_retirement', 0)),
        ('Investment Income', combined.get('investment_income', 0)),
        ('Other Income', combined.get('other_income', 0))
    ]
    
    for label, amount in breakdown_items:
        if amount > 0:
            percentage = (amount / total_monthly * 100) if total_monthly > 0 else 0
            print(f"   • {label}: ${amount:,.2f} ({percentage:.1f}%)")
    
    # Income Documentation
    print(f"\n{'='*80}")
    print(f"📄 INCOME DOCUMENTATION")
    print(f"{'='*80}")
    
    docs = analysis.get('income_documentation', {})
    
    doc_items = [
        ('Paystubs', docs.get('paystubs', {})),
        ('W-2 Forms', docs.get('w2_forms', {})),
        ('Tax Returns', docs.get('tax_returns', {})),
        ('VOE/VOI', docs.get('voe_voi', {})),
        ('Bank Statements', docs.get('bank_statements', {})),
        ('Award Letters', docs.get('award_letters', {})),
        ('Form 1099', docs.get('form_1099', {})),
        ('P&L Statements', docs.get('profit_loss_statements', {})),
        ('Business Tax Returns', docs.get('business_tax_returns', {})),
        ('Rental Agreements', docs.get('rental_agreements', {}))
    ]
    
    for doc_name, doc_data in doc_items:
        if isinstance(doc_data, dict) and doc_data.get('provided'):
            status = "✓ Provided"
            details = []
            
            if 'count' in doc_data:
                details.append(f"{doc_data['count']} items")
            if 'date_range' in doc_data and doc_data['date_range']:
                details.append(doc_data['date_range'])
            if 'tax_years' in doc_data:
                details.append(f"Years: {', '.join(map(str, doc_data['tax_years']))}")
            if 'years' in doc_data:
                details.append(f"Years: {', '.join(map(str, doc_data['years']))}")
            if 'months' in doc_data:
                details.append(f"{doc_data['months']} months")
            if 'forms_provided' in doc_data:
                details.append(f"Forms: {', '.join(doc_data['forms_provided'])}")
            if 'types' in doc_data:
                details.append(f"Types: {', '.join(doc_data['types'])}")
            if 'method' in doc_data and doc_data['method'] != 'None':
                details.append(f"Method: {doc_data['method']}")
            if 'verification_date' in doc_data and doc_data['verification_date']:
                details.append(f"Date: {doc_data['verification_date']}")
            
            detail_str = " | ".join(details) if details else ""
            print(f"   {status} {doc_name}")
            if detail_str:
                print(f"      {detail_str}")
        else:
            print(f"   ✗ Not Provided: {doc_name}")
    
    # Other Documentation
    other_docs = docs.get('other_documentation', [])
    if other_docs:
        print(f"\n   OTHER DOCUMENTATION:")
        for doc in other_docs:
            print(f"   • {doc}")
    
    # Income Stability Assessment
    print(f"\n{'='*80}")
    print(f"📊 INCOME STABILITY ASSESSMENT")
    print(f"{'='*80}")
    
    stability = analysis.get('income_stability_assessment', {})
    
    assessments = [
        ('Employment Stability', stability.get('employment_stability')),
        ('Income Consistency', stability.get('income_consistency')),
        ('Income Trend', stability.get('income_trend')),
        ('Continuance Likelihood', stability.get('continuance_likelihood')),
        ('Documentation Quality', stability.get('documentation_quality')),
        ('Overall Income Strength', stability.get('overall_income_strength'))
    ]
    
    for label, value in assessments:
        if value:
            print(f"   • {label}: {value}")
    
    # Income Strengths
    strengths = analysis.get('income_strengths', [])
    if strengths:
        print(f"\n✅ INCOME STRENGTHS ({len(strengths)}):")
        for i, strength in enumerate(strengths, 1):
            print(f"   {i}. {strength}")
    
    # Income Concerns
    concerns = analysis.get('income_concerns', [])
    if concerns:
        print(f"\n⚠️  INCOME CONCERNS ({len(concerns)}):")
        for i, concern in enumerate(concerns, 1):
            print(f"   {i}. {concern}")
    
    # Underwriting Notes
    print(f"\n{'='*80}")
    print(f"📋 UNDERWRITING NOTES")
    print(f"{'='*80}")
    
    uw_notes = analysis.get('underwriting_notes', {})
    
    qualifying_income = uw_notes.get('total_qualifying_income', 0)
    print(f"\n   Total Qualifying Income: ${qualifying_income:,.2f}/month")
    
    if uw_notes.get('income_averaging_applied'):
        print(f"   Income Averaging: Applied")
    
    if uw_notes.get('self_employment_adjustments'):
        print(f"   Self-Employment Adjustments: {uw_notes['self_employment_adjustments']}")
    
    if uw_notes.get('rental_income_calculation'):
        print(f"   Rental Income Calculation: {uw_notes['rental_income_calculation']}")
    
    if uw_notes.get('variable_income_treatment'):
        print(f"   Variable Income Treatment: {uw_notes['variable_income_treatment']}")
    
    if uw_notes.get('income_documentation_notes'):
        print(f"   Documentation Notes: {uw_notes['income_documentation_notes']}")
    
    verification_status = uw_notes.get('employment_verification_status', 'Unknown')
    print(f"   Employment Verification: {verification_status}")
    
    if uw_notes.get('income_continuance_assessment'):
        print(f"   Income Continuance: {uw_notes['income_continuance_assessment']}")
    
    # Recommendation
    print(f"\n{'='*80}")
    print(f"🎯 RECOMMENDATION")
    print(f"{'='*80}")
    
    recommendation = analysis.get('recommendation', 'Unknown')
    recommendation_details = analysis.get('recommendation_details', 'N/A')
    
    print(f"\n   Status: {recommendation}")
    print(f"   Details: {recommendation_details}")
    
    print(f"\n{'='*80}")


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python agents/income_evaluation_agent.py <loan_id>")
        print("Example: python agents/income_evaluation_agent.py 1000182005")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    print(f"\n🚀 Starting Income Evaluation Agent for Loan {loan_id}")
    print("="*80)
    
    # Load semantic JSON files
    semantic_docs = load_semantic_json_files(loan_id)
    
    if not semantic_docs:
        print("❌ No semantic documents found. Exiting.")
        sys.exit(1)
    
    print(f"\n✓ Loaded {len(semantic_docs)} semantic documents")
    
    # Analyze income with LLM
    try:
        analysis = analyze_income_with_llm(loan_id, semantic_docs)
        print("✓ Income analysis completed")
    except Exception as e:
        print(f"❌ Failed to analyze income: {e}")
        sys.exit(1)
    
    # Save analysis report
    try:
        report_path = save_analysis_report(loan_id, analysis)
        print(f"✓ Analysis saved to: {report_path}")
    except Exception as e:
        print(f"❌ Failed to save analysis: {e}")
        sys.exit(1)
    
    # Display summary
    display_income_summary(analysis)
    
    print(f"\n✅ Income evaluation completed successfully!")
    print(f"📊 Report saved to: {report_path}\n")


if __name__ == "__main__":
    main()
