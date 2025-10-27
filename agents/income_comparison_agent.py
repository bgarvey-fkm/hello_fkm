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

Your task is to analyze AI-calculated income results (from multiple runs) and compare them against the "ground truth" Form 1003 loan application data.

You will be provided with two JSON documents:
1. consistency_summary_all.json - Contains AI income calculation runs with statistics (may have 3, 10, or other number of runs)
2. form_1003_income_timeline.json - Contains the actual Form 1003 income values (initial and final)

CRITICAL: If there are multiple Form 1003 versions, check if the borrowers on the final Form 1003 are the same as the initial Form 1003.
- If borrowers changed (someone was added or removed), you MUST adjust the AI income comparison to only include income for borrowers who appear on the FINAL Form 1003.
- Look at the borrower names in the initial vs final Form 1003 versions
- If a borrower was removed, exclude their income from the AI totals when comparing to the final Form 1003
- If a borrower was added, note this in the analysis
- The goal is to compare apples-to-apples: AI income for the final borrower set vs Form 1003 income for the final borrower set

Generate a structured comparison analysis in JSON format with the following keys:

{
  "loan_id": "<loan_id>",
  "num_ai_runs": <number of runs in consistency summary>,
  "borrowers_changed": <true/false - did borrowers change between initial and final 1003?>,
  "initial_borrowers": ["<name1>", "<name2>", ...],
  "final_borrowers": ["<name1>", "<name2>", ...],
  "borrowers_removed": ["<names of removed borrowers>"],
  "borrowers_added": ["<names of added borrowers>"],
  "ai_avg_income": <average from all runs>,
  "ai_median_income": <median from all runs>,
  "ai_min_income": <minimum from all runs>,
  "ai_max_income": <maximum from all runs>,
  "ai_variance_pct": <variance percentage from summary>,
  "ai_consistency_rating": "<HIGH if <1%, MEDIUM if 1-5%, LOW if >5%>",
  "ai_avg_income_adjusted": <if borrowers changed, average income for only final borrowers; else same as ai_avg_income>,
  "ai_median_income_adjusted": <if borrowers changed, median income for only final borrowers; else same as ai_median_income>,
  "form_1003_initial_income": <total_monthly_income from first version>,
  "form_1003_final_income": <total_monthly_income from last version>,
  "form_1003_num_versions": <number of 1003 versions>,
  "form_1003_net_change": <net change from initial to final>,
  "ai_avg_vs_final_1003_diff": <ai_avg_income_adjusted - form_1003_final_income>,
  "ai_avg_vs_final_1003_pct": <percentage difference>,
  "ai_median_vs_final_1003_diff": <ai_median_income_adjusted - form_1003_final_income>,
  "ai_median_vs_final_1003_pct": <percentage difference>,
  "best_ai_metric": "<'mean' or 'median' - which is closer to final 1003>",
  "notes": "<brief analysis including: accuracy, any borrower changes, and patterns observed>"
}

IMPORTANT:
- All monetary values should be numbers (not strings)
- All percentages should be numbers (not strings)
- Use null for missing values
- Be precise with calculations
- Round to 2 decimal places where appropriate
"""


async def generate_comparison_analysis(loan_id: str, consistency_data: dict, form_1003_data: dict) -> dict:
    """
    Generate comparison analysis using Azure OpenAI.
    
    Args:
        loan_id: The loan identifier
        consistency_data: The consistency_summary_all.json content
        form_1003_data: The form_1003_income_timeline.json content
    
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

CONSISTENCY SUMMARY (AI runs - check how many runs are actually in the data):
{json.dumps(consistency_data, indent=2)}

FORM 1003 TIMELINE (ground truth - check if borrowers changed between versions):
{json.dumps(form_1003_data, indent=2)}

CRITICAL INSTRUCTIONS:
1. Count the actual number of AI runs in the consistency_summary data (may be 3, 10, or other)
2. Compare the borrower names in the FIRST vs LAST Form 1003 version
3. If borrowers changed, identify who was added/removed
4. If borrowers changed, adjust AI income to only include income for borrowers on the FINAL Form 1003
5. Use the adjusted AI income values when comparing to the final Form 1003 income

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
    
    # Load the required files
    consistency_file = loan_dir / "consistency_summary_all.json"
    form_1003_file = loan_dir / "form_1003_income_timeline.json"
    
    # Check if required files exist
    missing_files = []
    if not consistency_file.exists():
        missing_files.append("consistency_summary_all.json")
    if not form_1003_file.exists():
        missing_files.append("form_1003_income_timeline.json")
    
    if missing_files:
        print(f"⚠️  Loan {loan_id}: Missing files: {', '.join(missing_files)}")
        return None
    
    # Load the data
    with open(consistency_file, 'r', encoding='utf-8') as f:
        consistency_data = json.load(f)
    
    with open(form_1003_file, 'r', encoding='utf-8') as f:
        form_1003_data = json.load(f)
    
    print(f"\n{'='*80}")
    print(f"Processing Loan {loan_id}")
    print(f"{'='*80}")
    
    # Generate comparison analysis
    comparison = await generate_comparison_analysis(loan_id, consistency_data, form_1003_data)
    
    # Save to file
    output_file = output_dir / "income_comparison_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, indent=2, fp=f)
    
    print(f"✅ Saved comparison analysis to: {output_file}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  AI Runs: {comparison.get('num_ai_runs', 0)}")
    print(f"  Borrowers Changed: {comparison.get('borrowers_changed', False)}")
    if comparison.get('borrowers_changed'):
        print(f"  Initial Borrowers: {', '.join(comparison.get('initial_borrowers', []))}")
        print(f"  Final Borrowers: {', '.join(comparison.get('final_borrowers', []))}")
        if comparison.get('borrowers_removed'):
            print(f"  Removed: {', '.join(comparison.get('borrowers_removed', []))}")
        if comparison.get('borrowers_added'):
            print(f"  Added: {', '.join(comparison.get('borrowers_added', []))}")
    print(f"  AI Average: ${comparison.get('ai_avg_income', 0):,.2f}")
    print(f"  AI Median: ${comparison.get('ai_median_income', 0):,.2f}")
    if comparison.get('borrowers_changed'):
        print(f"  AI Average (Adjusted): ${comparison.get('ai_avg_income_adjusted', 0):,.2f}")
        print(f"  AI Median (Adjusted): ${comparison.get('ai_median_income_adjusted', 0):,.2f}")
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
