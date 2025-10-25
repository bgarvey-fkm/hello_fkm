# -*- coding: utf-8 -*-
"""
Income Scenario Classifier
Analyzes income documents to classify the employment/income scenario
before performing the actual income calculation.
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


async def classify_income_scenario(loan_id, income_docs):
    """
    Classify the income scenario based on available documents.
    
    Args:
        loan_id: The loan number
        income_docs: List of income document dictionaries
    
    Returns:
        Dictionary with scenario classification
    """
    # Load Azure OpenAI client
    client = AsyncAzureOpenAI(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY")
    )
    
    # Build the prompt
    prompt = f"""You are an income underwriting analyst. Analyze these income documents and classify the employment/income scenario.

INCOME DOCUMENTS:
{json.dumps(income_docs, indent=2)}

YOUR TASK:

Analyze the documents and classify the scenario on these dimensions:

1. EMPLOYMENT STATUS:
   - Same employer throughout (2+ years W-2s from same employer)
   - Recent employer change (W-2s from old employer, paystub from new employer)
   - New to workforce (< 2 years total history)
   - Multiple concurrent jobs

2. INCOME TYPE:
   - Base salary only (no bonus/OT/commission visible)
   - Base + variable income (bonus, OT, commission present in docs)
   - Commissioned sales (majority from commission)
   - Hourly with fluctuating hours

3. VARIABLE INCOME HISTORY:
   - No variable income
   - Variable with 2+ year history (same employer)
   - Variable with < 2 year history
   - Variable present but employer changed (old employer had it, new doesn't show it yet)

4. DOCUMENTATION COMPLETENESS:
   - Complete: 2 years W-2s + recent paystub + VOE
   - Adequate: 2 years W-2s + recent paystub (no VOE)
   - Incomplete: Missing some required docs
   - Current employer only: Only recent paystubs, no W-2 history

5. COMPLEXITY LEVEL:
   - Simple: Same employer 2+ years, base salary only
   - Moderate: Same employer, has variable income with history
   - Complex: Employer change OR variable income continuity questions
   - Very Complex: Multiple issues (employer change + variable income + doc gaps)

6. INCOME PATTERN ANALYSIS:
   - Base pay trends (increasing, stable, decreasing)
   - Variable income trends (if present)
   - Pay frequency consistency
   - Any unusual patterns or anomalies

Provide a detailed, objective classification. Do NOT make recommendations or suggest which approach to use.
Simply classify what you observe in the documents.

Return ONLY a JSON object with this structure (no markdown, no code blocks):
{{
  "employment_status": "<same_employer|employer_change|new_to_workforce|multiple_jobs>",
  "employment_details": {{
    "current_employer": "<name from most recent paystub>",
    "current_employer_start_date": "<date if available, or 'unknown'>",
    "prior_employer": "<name from W-2s if different, or null>",
    "employment_gap": "<yes|no|unknown>",
    "total_employment_history_years": <number>
  }},
  "income_type": "<base_only|base_plus_variable|commissioned|hourly_fluctuating>",
  "income_components_present": {{
    "base_salary": <true|false>,
    "bonus": <true|false>,
    "overtime": <true|false>,
    "commission": <true|false>
  }},
  "variable_income_history": "<none|two_plus_years_same_employer|less_than_two_years|employer_changed>",
  "documentation_completeness": "<complete|adequate|incomplete|current_only>",
  "documentation_inventory": {{
    "w2_count": <number>,
    "w2_years": ["<year1>", "<year2>"],
    "w2_employers": ["<employer1>", "<employer2>"],
    "paystub_count": <number>,
    "paystub_employers": ["<employer1>"],
    "voe_present": <true|false>
  }},
  "complexity_level": "<simple|moderate|complex|very_complex>",
  "complexity_factors": [
    "<factor 1>",
    "<factor 2>"
  ],
  "income_pattern_analysis": {{
    "base_pay_trend": "<increasing|stable|decreasing|insufficient_data>",
    "base_pay_observations": "<description of base pay pattern>",
    "variable_income_trend": "<increasing|stable|decreasing|none|insufficient_data>",
    "variable_income_observations": "<description of variable pay pattern>",
    "pay_frequency": "<weekly|bi-weekly|semi-monthly|monthly|varies>",
    "anomalies": [
      "<any unusual observations>"
    ]
  }},
  "observations": [
    "<objective observation 1>",
    "<objective observation 2>"
  ],
  "scenario_summary": "<2-3 sentence objective description of the income situation>"
}}"""

    try:
        # Call Azure OpenAI
        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert income underwriting analyst. Analyze documents objectively and classify the scenario accurately."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=1.0  # gpt-5-mini only supports default temperature
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Add metadata
        result["loan_id"] = loan_id
        result["documents_analyzed"] = len(income_docs)
        
        return result
        
    except Exception as e:
        print(f"Error in scenario classification: {e}")
        return {
            "error": str(e),
            "loan_id": loan_id
        }


async def classify_loan_scenario(loan_id):
    """
    Classify income scenario for a loan.
    
    Args:
        loan_id: The loan number
    """
    print("=" * 80)
    print("INCOME SCENARIO CLASSIFIER")
    print(f"Loan ID: {loan_id}")
    print("=" * 80)
    
    # Load income documents from semantic_json
    loan_docs_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    if not loan_docs_dir.exists():
        print(f"Error: No semantic_json directory found for loan {loan_id}")
        return
    
    # Check if documents have been filtered yet
    has_cached_flags = False
    for doc_file in loan_docs_dir.glob("*.json"):
        try:
            with open(doc_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
                if 'income_verification_relevant' in doc:
                    has_cached_flags = True
                    break
        except:
            continue
    
    # If no cached flags exist, run document filtering FIRST
    if not has_cached_flags:
        print(f"\n>> No income_verification_relevant flags found - filtering documents first...")
        print(f">> Importing document filtering from income_analysis_agent...")
        
        # Import the filtering function
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from income_analysis_agent import filter_income_documents_by_guidelines
        
        # Run the filtering to populate the flags
        try:
            await filter_income_documents_by_guidelines(loan_id, refilter=False)
            print(f">> Document filtering complete - flags cached to semantic JSON files")
        except Exception as e:
            print(f">> ⚠️  Warning: Document filtering failed: {e}")
            print(f">> Falling back to keyword search...")
    
    # Now load income documents using the cached flags
    income_docs = []
    
    for doc_file in loan_docs_dir.glob("*.json"):
        try:
            with open(doc_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
                
                # Check if this document has been classified
                if 'income_verification_relevant' in doc:
                    if doc['income_verification_relevant'].get('is_relevant', False):
                        income_docs.append(doc)
                else:
                    # Fallback to keyword search if filtering failed
                    doc_type = doc.get('metadata', {}).get('DocPredictionType', '')
                    spring_type = doc.get('metadata', {}).get('SpringDocType', '')
                    if any(keyword in doc_type.upper() or keyword in spring_type.upper() 
                           for keyword in ['W2', 'W-2', 'PAYSTUB', 'PAY STUB', 'VOE', 'VERIFICATION OF EMPLOYMENT', '1099']):
                        income_docs.append(doc)
        except:
            continue
    
    if not income_docs:
        print(f"⚠️  Warning: No income documents found after filtering!")
        print(f"Error: No income documents found for loan {loan_id}")
        return
    
    if has_cached_flags:
        print(f"Using cached income document classifications")
    
    print(f"Found {len(income_docs)} income documents\n")
    print("Classifying scenario...")
    
    # Perform classification
    scenario = await classify_income_scenario(loan_id, income_docs)
    
    # Save to income_analysis directory
    income_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    income_dir.mkdir(parents=True, exist_ok=True)
    
    scenario_file = income_dir / "income_scenario.json"
    with open(scenario_file, 'w', encoding='utf-8') as f:
        json.dump(scenario, f, indent=2)
    
    print(f"\n{'=' * 80}")
    print("SCENARIO CLASSIFICATION RESULTS")
    print("=" * 80)
    print(f"Employment Status: {scenario.get('employment_status', 'unknown')}")
    print(f"Income Type: {scenario.get('income_type', 'unknown')}")
    print(f"Variable Income: {scenario.get('variable_income_history', 'unknown')}")
    print(f"Documentation: {scenario.get('documentation_completeness', 'unknown')}")
    print(f"Complexity: {scenario.get('complexity_level', 'unknown')}")
    print(f"\nSummary: {scenario.get('scenario_summary', 'No summary')}")
    
    if scenario.get('observations'):
        print(f"\nObservations:")
        for obs in scenario['observations']:
            print(f"  • {obs}")
    
    if scenario.get('income_pattern_analysis'):
        pattern = scenario['income_pattern_analysis']
        print(f"\nIncome Pattern Analysis:")
        print(f"  Base Pay Trend: {pattern.get('base_pay_trend', 'unknown')}")
        print(f"  Variable Income Trend: {pattern.get('variable_income_trend', 'unknown')}")
        print(f"  Pay Frequency: {pattern.get('pay_frequency', 'unknown')}")
        if pattern.get('anomalies'):
            print(f"  Anomalies: {', '.join(pattern['anomalies'])}")
    
    print(f"\nScenario saved to: {scenario_file}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python income_scenario_classifier.py <loan_id>")
        print("Example: python income_scenario_classifier.py 1000178434")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    await classify_loan_scenario(loan_id)


if __name__ == "__main__":
    asyncio.run(main())
