"""
Income Comparison Agent
Compares AI-calculated income (10 runs) against Form 1003 "ground truth" values.
Generates structured JSON output for each loan for later DataFrame aggregation.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import statistics

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Azure OpenAI configuration
subscription_key = os.getenv("AZURE_OPENAI_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")

# System prompt for the comparison analysis
COMPARISON_SYSTEM_PROMPT = """You are an expert mortgage underwriting analyst specializing in income calculation accuracy assessment.

Your task is to analyze AI-calculated income results (from 10 runs) and compare them against the "ground truth" Form 1003 loan application data.

You will be provided with three JSON documents:
1. consistency_summary_all.json - Contains 10 AI income calculation runs with statistics
2. form_1003_income_timeline.json - Contains the actual Form 1003 income values (initial and final)
3. income_scenario.json - Contains the income scenario classification and complexity

Generate a structured comparison analysis in JSON format with the following keys:

{
  "loan_id": "<loan_id>",
  "income_type": "<from scenario: income_type field>",
  "complexity_level": "<from scenario: complexity_level field>",
  "pay_frequency": "<from scenario: pay_frequency field>",
  "ai_avg_income": <average from 10 runs>,
  "ai_median_income": <median from 10 runs>,
  "ai_min_income": <minimum from 10 runs>,
  "ai_max_income": <maximum from 10 runs>,
  "ai_variance_pct": <variance percentage from summary>,
  "ai_consistency_rating": "<HIGH if <1%, MEDIUM if 1-5%, LOW if >5%>",
  "form_1003_initial_income": <total_monthly_income from first version>,
  "form_1003_final_income": <total_monthly_income from last version>,
  "form_1003_num_versions": <number of 1003 versions>,
  "form_1003_net_change": <net change from initial to final>,
  "ai_avg_vs_final_1003_diff": <ai_avg_income - form_1003_final_income>,
  "ai_avg_vs_final_1003_pct": <percentage difference>,
  "ai_median_vs_final_1003_diff": <ai_median_income - form_1003_final_income>,
  "ai_median_vs_final_1003_pct": <percentage difference>,
  "best_ai_metric": "<'mean' or 'median' - which is closer to final 1003>",
  "base_salary_component": <average base salary across runs, or from scenario>,
  "variable_income_component": <average variable income across runs>,
  "has_bonus": <true/false from scenario>,
  "has_commission": <true/false from scenario>,
  "has_overtime": <true/false from scenario>,
  "notes": "<brief 1-2 sentence analysis of accuracy and any patterns>"
}

IMPORTANT:
- All monetary values should be numbers (not strings)
- All percentages should be numbers (not strings)
- Use null for missing values
- Be precise with calculations
- Round to 2 decimal places where appropriate
"""


async def generate_comparison_analysis(loan_id: str, consistency_data: dict, form_1003_data: dict, scenario_data: dict) -> dict:
    """
    Generate comparison analysis using Azure OpenAI.
    
    Args:
        loan_id: The loan identifier
        consistency_data: The consistency_summary_all.json content
        form_1003_data: The form_1003_income_timeline.json content
        scenario_data: The income_scenario.json content
    
    Returns:
        dict: The comparison analysis JSON object
    """
    
    client = AsyncAzureOpenAI(
        api_key=subscription_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )
    
    # Prepare the user prompt
    user_prompt = f"""Analyze the following loan income data and generate the comparison JSON:

LOAN ID: {loan_id}

CONSISTENCY SUMMARY (10 AI runs):
{json.dumps(consistency_data, indent=2)}

FORM 1003 TIMELINE (ground truth):
{json.dumps(form_1003_data, indent=2)}

INCOME SCENARIO:
{json.dumps(scenario_data, indent=2)}

Generate the comparison analysis JSON now."""

    try:
        response = await client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        return result_json
        
    except Exception as e:
        print(f"Error generating comparison for loan {loan_id}: {e}")
        raise


async def process_loan_comparison(loan_id: str, output_dir: Path = None) -> dict:
    """
    Process a single loan and generate comparison analysis.
    
    Args:
        loan_id: The loan identifier
        output_dir: Optional output directory (defaults to loan_docs/{loan_id}/income_analysis/)
    
    Returns:
        dict: The comparison analysis
    """
    
    # Set up paths
    base_dir = Path(__file__).parent.parent
    loan_dir = base_dir / "loan_docs" / loan_id / "income_analysis"
    
    if output_dir is None:
        output_dir = loan_dir
    
    # Load the three required files
    consistency_file = loan_dir / "consistency_summary_all.json"
    form_1003_file = loan_dir / "form_1003_income_timeline.json"
    scenario_file = loan_dir / "income_scenario.json"
    
    # Check if all files exist
    missing_files = []
    if not consistency_file.exists():
        missing_files.append("consistency_summary_all.json")
    if not form_1003_file.exists():
        missing_files.append("form_1003_income_timeline.json")
    if not scenario_file.exists():
        missing_files.append("income_scenario.json")
    
    if missing_files:
        print(f"⚠️  Loan {loan_id}: Missing files: {', '.join(missing_files)}")
        return None
    
    # Load the data
    with open(consistency_file, 'r', encoding='utf-8') as f:
        consistency_data = json.load(f)
    
    with open(form_1003_file, 'r', encoding='utf-8') as f:
        form_1003_data = json.load(f)
    
    with open(scenario_file, 'r', encoding='utf-8') as f:
        scenario_data = json.load(f)
    
    print(f"\n{'='*80}")
    print(f"Processing Loan {loan_id}")
    print(f"{'='*80}")
    
    # Generate comparison analysis
    comparison = await generate_comparison_analysis(loan_id, consistency_data, form_1003_data, scenario_data)
    
    # Save to file
    output_file = output_dir / "income_comparison_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, indent=2, fp=f)
    
    print(f"✅ Saved comparison analysis to: {output_file}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Income Type: {comparison.get('income_type', 'N/A')}")
    print(f"  Complexity: {comparison.get('complexity_level', 'N/A')}")
    print(f"  AI Average: ${comparison.get('ai_avg_income', 0):,.2f}")
    print(f"  AI Median: ${comparison.get('ai_median_income', 0):,.2f}")
    print(f"  AI Variance: {comparison.get('ai_variance_pct', 0):.2f}%")
    print(f"  Final 1003: ${comparison.get('form_1003_final_income', 0):,.2f}")
    print(f"  AI Avg vs Final: {comparison.get('ai_avg_vs_final_1003_pct', 0):+.2f}%")
    print(f"  AI Median vs Final: {comparison.get('ai_median_vs_final_1003_pct', 0):+.2f}%")
    print(f"  Best Metric: {comparison.get('best_ai_metric', 'N/A')}")
    
    return comparison


async def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print("Usage: python income_comparison_agent.py <loan_id>")
        print("Example: python income_comparison_agent.py 1000175957")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    try:
        result = await process_loan_comparison(loan_id)
        
        if result:
            print(f"\n{'='*80}")
            print("COMPARISON ANALYSIS COMPLETE")
            print(f"{'='*80}")
        else:
            print(f"\n❌ Failed to process loan {loan_id}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
