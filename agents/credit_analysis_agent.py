"""
Credit Analysis Agent

Extracts and summarizes credit information from semantic JSON files.
Focuses on: credit scores, tradelines, payment history, derogatory events,
credit inquiries, and overall credit profile.

Usage:
    python agents/credit_analysis_agent.py <loan_id>
    
Example:
    python agents/credit_analysis_agent.py 1000182227
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
                doc_type = data.get('document_type', 'unknown')
                # Focus on credit-related documents
                if 'credit' in doc_type.lower() or 'credit' in json_file.stem.lower():
                    semantic_docs[json_file.stem] = data
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return semantic_docs


def analyze_credit(loan_id="1000182227"):
    """
    Analyze credit information from semantic JSON files.
    """
    
    print("=" * 80)
    print(f"Credit Analysis - Loan {loan_id}")
    print("=" * 80)
    print()
    
    # Load semantic data
    print("📁 Loading credit-related semantic JSON files...")
    semantic_docs = load_semantic_json(loan_id)
    
    if not semantic_docs:
        print("❌ No credit documents found!")
        print("   Looking for any semantic JSON with credit data...")
        # Fallback: load all semantic docs
        semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
        for json_file in semantic_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    semantic_docs[json_file.stem] = data
            except Exception as e:
                continue
    
    print(f"✅ Loaded {len(semantic_docs)} documents")
    print()
    print("=" * 80)
    print("🔍 Analyzing credit profile...")
    print("=" * 80)
    print()
    
    # Build comprehensive prompt
    prompt = f"""You are a Senior Credit Analyst reviewing a mortgage loan application.

SEMANTIC LOAN DOCUMENTS:
{json.dumps(semantic_docs, indent=2)}

YOUR TASK:
Extract and summarize ALL credit-related information from the documents. Provide a comprehensive credit analysis.

OUTPUT FORMAT (JSON only, no markdown):
{{
  "loan_number": "...",
  "borrowers": [
    {{
      "name": "...",
      "credit_scores": {{
        "experian": 0,
        "transunion": 0,
        "equifax": 0,
        "lowest_score": 0,
        "middle_score": 0
      }},
      "ssn_last_4": "...",
      "date_of_birth": "..."
    }}
  ],
  "credit_report_summary": {{
    "report_date": "...",
    "report_type": "Tri-merge | Single Bureau (Experian/Equifax/TransUnion)",
    "credit_repository": "...",
    "total_accounts": 0,
    "open_accounts": 0,
    "closed_accounts": 0,
    "revolving_accounts": 0,
    "installment_accounts": 0,
    "mortgage_accounts": 0
  }},
  "tradelines": [
    {{
      "creditor": "...",
      "account_type": "Revolving | Installment | Mortgage | Auto | Student Loan | etc.",
      "account_number_last_4": "...",
      "date_opened": "...",
      "balance": 0,
      "credit_limit": 0,
      "monthly_payment": 0,
      "status": "Open | Closed | Paid",
      "payment_history": "Current | 30 days late | 60 days late | etc.",
      "responsibility": "Individual | Joint | Authorized User | Co-signer"
    }}
  ],
  "payment_history": {{
    "housing_history_12_months": "0x30 (no 30-day lates)",
    "housing_history_24_months": "...",
    "total_delinquencies_24_months": 0,
    "most_recent_delinquency": "...",
    "late_payments_summary": "..."
  }},
  "derogatory_events": [
    {{
      "type": "Bankruptcy Ch7/Ch13 | Foreclosure | Short Sale | Deed in Lieu | Collection | Charge-off | Judgment | Tax Lien",
      "date": "...",
      "amount": 0,
      "status": "Satisfied | Outstanding | Dismissed",
      "details": "..."
    }}
  ],
  "credit_inquiries": {{
    "inquiries_6_months": 0,
    "inquiries_12_months": 0,
    "recent_inquiries": [
      {{
        "date": "...",
        "creditor": "...",
        "type": "Hard | Soft"
      }}
    ]
  }},
  "public_records": [
    {{
      "type": "Judgment | Tax Lien | Bankruptcy",
      "filing_date": "...",
      "amount": 0,
      "status": "...",
      "details": "..."
    }}
  ],
  "collections": [
    {{
      "creditor": "...",
      "original_creditor": "...",
      "date_opened": "...",
      "balance": 0,
      "status": "...",
      "details": "..."
    }}
  ],
  "credit_utilization": {{
    "total_revolving_credit_limit": 0,
    "total_revolving_balance": 0,
    "utilization_percentage": 0,
    "per_account_utilization": [
      {{
        "creditor": "...",
        "limit": 0,
        "balance": 0,
        "utilization": 0
      }}
    ]
  }},
  "credit_strengths": [
    "List positive credit factors..."
  ],
  "credit_concerns": [
    "List negative credit factors or risks..."
  ],
  "underwriting_notes": {{
    "tradeline_count_adequate": true/false,
    "housing_payment_history_acceptable": true/false,
    "recent_delinquencies": true/false,
    "derogatory_events_within_guidelines": true/false,
    "credit_score_trend": "Improving | Stable | Declining",
    "overall_credit_quality": "Excellent | Good | Fair | Poor",
    "recommendation": "Approve | Approve with Conditions | Decline",
    "conditions": ["List any credit-related conditions..."]
  }},
  "analyst_summary": "Comprehensive narrative summary of the borrower's credit profile, highlighting key findings, trends, and risk factors. Include comparison to typical underwriting standards."
}}

Be thorough and precise. Extract ALL credit details found in the documents."""

    # Call LLM
    print("⏳ Analyzing credit data (this may take 30-45 seconds)...")
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system", 
                "content": "You are a Senior Credit Analyst with expertise in mortgage underwriting. Output only valid JSON with comprehensive credit analysis."
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
    credit_analysis = json.loads(response.choices[0].message.content)
    
    # Add metadata
    credit_analysis['_metadata'] = {
        'analysis_date': datetime.now().isoformat(),
        'loan_id': loan_id,
        'documents_analyzed': len(semantic_docs),
        'analyzing_model': deployment,
        'agent': 'credit_analysis_agent'
    }
    
    # Save output
    output_dir = Path(f"loan_docs/{loan_id}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"credit_analysis_{loan_id}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(credit_analysis, f, indent=2, ensure_ascii=False)
    
    # Display results
    print()
    print("=" * 80)
    print("✅ CREDIT ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📄 Saved to: {output_path}")
    print()
    
    # Summary
    borrowers = credit_analysis.get('borrowers', [])
    print("📊 CREDIT SUMMARY:")
    for borrower in borrowers:
        name = borrower.get('name', 'Unknown')
        scores = borrower.get('credit_scores', {})
        print(f"\n   👤 {name}")
        print(f"      FICO: {scores.get('lowest_score', 'N/A')} (lowest) | {scores.get('middle_score', 'N/A')} (middle)")
        if scores.get('experian'):
            print(f"      Experian: {scores.get('experian')}")
        if scores.get('transunion'):
            print(f"      TransUnion: {scores.get('transunion')}")
        if scores.get('equifax'):
            print(f"      Equifax: {scores.get('equifax')}")
    
    report_summary = credit_analysis.get('credit_report_summary', {})
    print(f"\n   📋 Report Type: {report_summary.get('report_type', 'N/A')}")
    print(f"   📅 Report Date: {report_summary.get('report_date', 'N/A')}")
    print(f"   📊 Total Accounts: {report_summary.get('total_accounts', 0)}")
    print(f"   ✅ Open Accounts: {report_summary.get('open_accounts', 0)}")
    
    payment_history = credit_analysis.get('payment_history', {})
    print(f"\n   🏠 Housing History (12mo): {payment_history.get('housing_history_12_months', 'N/A')}")
    print(f"   ⚠️  Total Delinquencies (24mo): {payment_history.get('total_delinquencies_24_months', 0)}")
    
    derogatory = credit_analysis.get('derogatory_events', [])
    if derogatory:
        print(f"\n   🚨 Derogatory Events: {len(derogatory)}")
        for event in derogatory[:3]:  # Show first 3
            print(f"      - {event.get('type', 'Unknown')}: {event.get('date', 'N/A')} ({event.get('status', 'N/A')})")
    
    utilization = credit_analysis.get('credit_utilization', {})
    if utilization.get('utilization_percentage'):
        print(f"\n   💳 Credit Utilization: {utilization.get('utilization_percentage', 0):.1f}%")
    
    uw_notes = credit_analysis.get('underwriting_notes', {})
    print(f"\n   📝 Overall Credit Quality: {uw_notes.get('overall_credit_quality', 'N/A')}")
    print(f"   ✅ Recommendation: {uw_notes.get('recommendation', 'N/A')}")
    
    # Strengths and Concerns
    strengths = credit_analysis.get('credit_strengths', [])
    if strengths:
        print(f"\n   ✨ Credit Strengths ({len(strengths)}):")
        for strength in strengths[:3]:
            print(f"      • {strength}")
    
    concerns = credit_analysis.get('credit_concerns', [])
    if concerns:
        print(f"\n   ⚠️  Credit Concerns ({len(concerns)}):")
        for concern in concerns[:3]:
            print(f"      • {concern}")
    
    print()
    print("=" * 80)
    
    return credit_analysis


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    analyze_credit(loan_id)
