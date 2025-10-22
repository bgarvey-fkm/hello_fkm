"""
Loan Terms Analysis Agent

Extracts and summarizes loan structure information from semantic JSON files.
Focuses on: first lien details, second lien/HELOC details, rates, LTV/CLTV,
blended rates, and overall loan structure.

Usage:
    python agents/loan_terms_agent.py <loan_id>
    
Example:
    python agents/loan_terms_agent.py 1000182227
"""

import os
import sys
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialize Azure OpenAI client
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


def load_semantic_json(loan_id):
    """Load all semantic JSON files for a loan."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return {}
    
    semantic_docs = {}
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                semantic_docs[json_file.stem] = data
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return semantic_docs


def analyze_loan_terms(loan_id="1000182227"):
    """
    Analyze loan structure and terms from semantic JSON files.
    """
    
    print("=" * 80)
    print(f"Loan Terms Analysis - Loan {loan_id}")
    print("=" * 80)
    print()
    
    # Load semantic data
    print("📁 Loading all semantic JSON files...")
    semantic_docs = load_semantic_json(loan_id)
    
    if not semantic_docs:
        print("❌ No documents found!")
        return None
    
    print(f"✅ Loaded {len(semantic_docs)} documents")
    print()
    print("=" * 80)
    print("🔍 Analyzing loan structure and terms...")
    print("=" * 80)
    print()
    
    # Build comprehensive prompt
    prompt = f"""You are a Senior Mortgage Loan Officer and Product Specialist reviewing a loan structure.

SEMANTIC LOAN DOCUMENTS:
{json.dumps(semantic_docs, indent=2)}

YOUR TASK:
Extract and analyze ALL loan structure details, focusing on BOTH the first lien and the proposed second lien/HELOC. Calculate blended rates and provide comprehensive loan structure analysis.

OUTPUT FORMAT (JSON only, no markdown):
{{
  "loan_number": "...",
  "property_value": 0,
  "borrower_names": ["..."],
  
  "first_lien": {{
    "lender": "...",
    "servicer": "...",
    "loan_type": "Conventional | FHA | VA | USDA | Portfolio",
    "lien_position": "First",
    "original_loan_amount": 0,
    "current_balance": 0,
    "interest_rate": 0,
    "monthly_payment": 0,
    "payment_includes": ["Principal", "Interest", "Taxes", "Insurance", "PMI", "HOA"],
    "loan_term_months": 0,
    "remaining_term_months": 0,
    "origination_date": "...",
    "maturity_date": "...",
    "loan_purpose": "Purchase | Refinance | Cash-out Refinance",
    "amortization_type": "Fixed | ARM | Interest Only | Balloon",
    "escrow_account": "Yes | No",
    "pmi_mip": "Yes | No",
    "pmi_mip_amount": 0,
    "first_lien_ltv": 0,
    "note_rate": 0,
    "apr": 0
  }},
  
  "proposed_second_lien": {{
    "lender": "...",
    "product_type": "HELOC | Second Mortgage | Home Equity Loan",
    "lien_position": "Second",
    "loan_amount": 0,
    "credit_line_amount": 0,
    "interest_rate": 0,
    "apr": 0,
    "monthly_payment": 0,
    "loan_term_months": 0,
    "draw_period_months": 0,
    "repayment_period_months": 0,
    "rate_type": "Fixed | Variable | Adjustable",
    "index": "Prime | SOFR | CMT | etc.",
    "margin": 0,
    "rate_cap": "...",
    "loan_purpose": "Cash-out | Debt Consolidation | Home Improvement | Purchase",
    "closing_costs": 0,
    "fees": {{
        "origination_fee": 0,
        "application_fee": 0,
        "appraisal_fee": 0,
        "title_fees": 0,
        "recording_fees": 0,
        "other_fees": 0,
        "total_fees": 0
    }},
    "proceeds_use": {{
        "debt_payoff": 0,
        "cash_to_borrower": 0,
        "closing_costs": 0,
        "other": 0
    }}
  }},
  
  "combined_loan_structure": {{
    "total_first_lien": 0,
    "total_second_lien": 0,
    "total_debt": 0,
    "property_value": 0,
    "first_lien_ltv": 0,
    "second_lien_ltv": 0,
    "cltv": 0,
    "hcltv": 0
  }},
  
  "blended_rate_analysis": {{
    "first_lien_rate": 0,
    "first_lien_balance": 0,
    "first_lien_monthly_payment": 0,
    "second_lien_rate": 0,
    "second_lien_balance": 0,
    "second_lien_monthly_payment": 0,
    "total_monthly_payment": 0,
    "blended_interest_rate": 0,
    "calculation_method": "Weighted average of interest rates based on loan balances",
    "blended_rate_formula": "(First Rate × First Balance + Second Rate × Second Balance) / Total Balance"
  }},
  
  "payment_analysis": {{
    "first_lien_pi": 0,
    "first_lien_escrow": 0,
    "first_lien_total": 0,
    "second_lien_payment": 0,
    "total_housing_payment": 0,
    "taxes_monthly": 0,
    "insurance_monthly": 0,
    "hoa_monthly": 0,
    "total_pitia": 0
  }},
  
  "subordination_status": {{
    "first_lien_subordination_required": "Yes | No | N/A",
    "subordination_agreement_present": "Yes | No | Pending",
    "first_lien_allows_subordination": "Yes | No | Unknown",
    "subordination_conditions": ["..."]
  }},
  
  "loan_program_details": {{
    "second_lien_program": "...",
    "investor": "...",
    "product_features": ["..."],
    "prepayment_penalty": "Yes | No",
    "balloon_payment": "Yes | No",
    "interest_only_period": "Yes | No"
  }},
  
  "underwriting_calculations": {{
    "max_cltv_allowed": 0,
    "actual_cltv": 0,
    "cltv_within_guidelines": true/false,
    "first_lien_payment_verified": true/false,
    "second_lien_payment_calculated": true/false,
    "total_debt_load": 0,
    "equity_position": 0,
    "equity_percentage": 0
  }},
  
  "loan_strengths": [
    "List positive loan structure factors..."
  ],
  
  "loan_concerns": [
    "List negative loan structure factors or risks..."
  ],
  
  "analyst_summary": "Comprehensive narrative summary of the loan structure, including first and second lien details, blended rate analysis, LTV/CLTV calculations, equity position, payment structure, and overall risk assessment. Include comparison to typical loan structures and highlight any unusual features or concerns."
}}

IMPORTANT CALCULATIONS:
- First Lien LTV = (First Lien Balance / Property Value) × 100
- Second Lien LTV = (Second Lien Amount / Property Value) × 100
- CLTV = ((First Lien Balance + Second Lien Amount) / Property Value) × 100
- Blended Rate = ((First Rate × First Balance) + (Second Rate × Second Balance)) / (First Balance + Second Balance)

Be thorough and precise. Extract ALL loan structure details found in the documents."""

    # Call LLM
    print("⏳ Analyzing loan structure (this may take 30-45 seconds)...")
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system", 
                "content": "You are a Senior Mortgage Loan Officer and Product Specialist with expertise in residential loan structures, subordinate financing, and loan-to-value calculations. Output only valid JSON with comprehensive loan analysis."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=16000
    )
    
    # Parse response
    loan_analysis = json.loads(response.choices[0].message.content)
    
    # Add metadata
    loan_analysis['_metadata'] = {
        'analysis_date': datetime.now().isoformat(),
        'loan_id': loan_id,
        'documents_analyzed': len(semantic_docs),
        'analyzing_model': deployment,
        'agent': 'loan_terms_agent'
    }
    
    # Save output
    output_dir = Path(f"loan_docs/{loan_id}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"loan_terms_analysis_{loan_id}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(loan_analysis, f, indent=2, ensure_ascii=False)
    
    # Display results
    print()
    print("=" * 80)
    print("✅ LOAN TERMS ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📄 Saved to: {output_path}")
    print()
    
    # Summary
    first_lien = loan_analysis.get('first_lien', {})
    second_lien = loan_analysis.get('proposed_second_lien', {})
    combined = loan_analysis.get('combined_loan_structure', {})
    blended = loan_analysis.get('blended_rate_analysis', {})
    payment = loan_analysis.get('payment_analysis', {})
    
    print("📊 LOAN STRUCTURE SUMMARY:")
    print()
    print("=" * 80)
    print("1️⃣  FIRST LIEN:")
    print("=" * 80)
    print(f"   Lender/Servicer: {first_lien.get('lender', 'N/A')} / {first_lien.get('servicer', 'N/A')}")
    print(f"   Current Balance: ${first_lien.get('current_balance', 0):,.2f}")
    print(f"   Interest Rate: {first_lien.get('interest_rate', 0):.3f}%")
    print(f"   Monthly Payment: ${first_lien.get('monthly_payment', 0):,.2f}")
    print(f"   First Lien LTV: {first_lien.get('first_lien_ltv', combined.get('first_lien_ltv', 0)):.2f}%")
    print(f"   Loan Type: {first_lien.get('loan_type', 'N/A')}")
    print(f"   Amortization: {first_lien.get('amortization_type', 'N/A')}")
    
    print()
    print("=" * 80)
    print("2️⃣  PROPOSED SECOND LIEN / HELOC:")
    print("=" * 80)
    print(f"   Lender: {second_lien.get('lender', 'N/A')}")
    print(f"   Product Type: {second_lien.get('product_type', 'N/A')}")
    print(f"   Loan Amount: ${second_lien.get('loan_amount', 0):,.2f}")
    if second_lien.get('credit_line_amount', 0) > 0:
        print(f"   Credit Line: ${second_lien.get('credit_line_amount', 0):,.2f}")
    print(f"   Interest Rate: {second_lien.get('interest_rate', 0):.3f}%")
    print(f"   APR: {second_lien.get('apr', 0):.3f}%")
    print(f"   Monthly Payment: ${second_lien.get('monthly_payment', 0):,.2f}")
    print(f"   Rate Type: {second_lien.get('rate_type', 'N/A')}")
    print(f"   Loan Purpose: {second_lien.get('loan_purpose', 'N/A')}")
    
    proceeds = second_lien.get('proceeds_use', {})
    if proceeds:
        print(f"\n   💰 Proceeds Use:")
        if proceeds.get('debt_payoff', 0) > 0:
            print(f"      Debt Payoff: ${proceeds.get('debt_payoff', 0):,.2f}")
        if proceeds.get('cash_to_borrower', 0) > 0:
            print(f"      Cash to Borrower: ${proceeds.get('cash_to_borrower', 0):,.2f}")
        if proceeds.get('closing_costs', 0) > 0:
            print(f"      Closing Costs: ${proceeds.get('closing_costs', 0):,.2f}")
    
    print()
    print("=" * 80)
    print("📊 COMBINED STRUCTURE & LTV/CLTV:")
    print("=" * 80)
    print(f"   Property Value: ${combined.get('property_value', 0):,.2f}")
    print(f"   First Lien Balance: ${combined.get('total_first_lien', 0):,.2f}")
    print(f"   Second Lien Amount: ${combined.get('total_second_lien', 0):,.2f}")
    print(f"   Total Debt: ${combined.get('total_debt', 0):,.2f}")
    print()
    print(f"   📐 First Lien LTV: {combined.get('first_lien_ltv', 0):.2f}%")
    print(f"   📐 Second Lien LTV: {combined.get('second_lien_ltv', 0):.2f}%")
    print(f"   📐 CLTV: {combined.get('cltv', 0):.2f}%")
    if combined.get('hcltv', 0) > 0:
        print(f"   📐 HCLTV: {combined.get('hcltv', 0):.2f}%")
    
    print()
    print("=" * 80)
    print("💰 BLENDED RATE ANALYSIS:")
    print("=" * 80)
    print(f"   First Lien: {blended.get('first_lien_rate', 0):.3f}% on ${blended.get('first_lien_balance', 0):,.2f}")
    print(f"   Second Lien: {blended.get('second_lien_rate', 0):.3f}% on ${blended.get('second_lien_balance', 0):,.2f}")
    print(f"   ⭐ Blended Rate: {blended.get('blended_interest_rate', 0):.3f}%")
    print(f"   Total Monthly Payment: ${blended.get('total_monthly_payment', 0):,.2f}")
    
    print()
    print("=" * 80)
    print("🏠 PAYMENT STRUCTURE:")
    print("=" * 80)
    print(f"   First Lien P&I: ${payment.get('first_lien_pi', 0):,.2f}")
    if payment.get('first_lien_escrow', 0) > 0:
        print(f"   First Lien Escrow: ${payment.get('first_lien_escrow', 0):,.2f}")
    print(f"   First Lien Total: ${payment.get('first_lien_total', 0):,.2f}")
    print(f"   Second Lien Payment: ${payment.get('second_lien_payment', 0):,.2f}")
    print(f"   Total Housing Payment: ${payment.get('total_housing_payment', 0):,.2f}")
    if payment.get('total_pitia', 0) > 0:
        print(f"   Total PITIA: ${payment.get('total_pitia', 0):,.2f}")
    
    # Strengths and Concerns
    strengths = loan_analysis.get('loan_strengths', [])
    if strengths:
        print()
        print("=" * 80)
        print(f"✨ LOAN STRUCTURE STRENGTHS ({len(strengths)}):")
        print("=" * 80)
        for strength in strengths:
            print(f"   • {strength}")
    
    concerns = loan_analysis.get('loan_concerns', [])
    if concerns:
        print()
        print("=" * 80)
        print(f"⚠️  LOAN STRUCTURE CONCERNS ({len(concerns)}):")
        print("=" * 80)
        for concern in concerns:
            print(f"   • {concern}")
    
    # Underwriting calcs
    uw_calcs = loan_analysis.get('underwriting_calculations', {})
    if uw_calcs:
        print()
        print("=" * 80)
        print("📋 UNDERWRITING NOTES:")
        print("=" * 80)
        print(f"   Max CLTV Allowed: {uw_calcs.get('max_cltv_allowed', 0):.2f}%")
        print(f"   Actual CLTV: {uw_calcs.get('actual_cltv', 0):.2f}%")
        print(f"   Within Guidelines: {'✅ Yes' if uw_calcs.get('cltv_within_guidelines') else '❌ No'}")
        if uw_calcs.get('equity_position', 0) > 0:
            print(f"   Equity Position: ${uw_calcs.get('equity_position', 0):,.2f} ({uw_calcs.get('equity_percentage', 0):.2f}%)")
    
    print()
    print("=" * 80)
    
    return loan_analysis


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    analyze_loan_terms(loan_id)
