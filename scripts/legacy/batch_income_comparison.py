"""
Batch Income Comparison Processor
Generates comparison analysis JSON files for all loans.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Import the comparison agent
sys.path.insert(0, str(Path(__file__).parent / "agents"))
from income_comparison_agent import process_loan_comparison


async def process_loan(loan_id: str, semaphore: asyncio.Semaphore) -> tuple:
    """
    Process a single loan with rate limiting.
    
    Args:
        loan_id: The loan identifier
        semaphore: Semaphore for rate limiting
    
    Returns:
        tuple: (loan_id, success, comparison_data or error_message)
    """
    async with semaphore:
        try:
            comparison = await process_loan_comparison(loan_id)
            if comparison:
                return (loan_id, True, comparison)
            else:
                return (loan_id, False, "Missing required files")
        except Exception as e:
            return (loan_id, False, str(e))


async def main():
    """Main batch processor."""
    
    print("\n" + "="*80)
    print("BATCH INCOME COMPARISON ANALYSIS")
    print("="*80)
    
    # Find all loans with the required files
    base_dir = Path(__file__).parent
    loan_docs_dir = base_dir / "loan_docs"
    
    # Find all loan directories
    loan_dirs = [d for d in loan_docs_dir.iterdir() if d.is_dir() and d.name.startswith("1000")]
    loan_ids = sorted([d.name for d in loan_dirs])
    
    print(f"\nFound {len(loan_ids)} loan directories")
    
    # Filter to loans that have all three required files
    eligible_loans = []
    for loan_id in loan_ids:
        income_analysis_dir = loan_docs_dir / loan_id / "income_analysis"
        if not income_analysis_dir.exists():
            continue
        
        has_consistency = (income_analysis_dir / "consistency_summary_all.json").exists()
        has_form_1003 = (income_analysis_dir / "form_1003_income_timeline.json").exists()
        has_scenario = (income_analysis_dir / "income_scenario.json").exists()
        
        if has_consistency and has_form_1003 and has_scenario:
            eligible_loans.append(loan_id)
    
    print(f"Found {len(eligible_loans)} loans with all required files (consistency + form_1003 + scenario)")
    
    if not eligible_loans:
        print("\n❌ No eligible loans found. Make sure you have run:")
        print("  1. batch_test_refactored_workflow.py (generates consistency_summary_all.json)")
        print("  2. batch_form_1003_tracker.py (generates form_1003_income_timeline.json)")
        print("  3. income_scenario_classifier.py (generates income_scenario.json)")
        return
    
    print(f"\nProcessing {len(eligible_loans)} loans with up to 5 concurrent API calls...")
    print("="*80)
    
    # Create semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(5)
    
    # Process all loans in parallel
    tasks = [process_loan(loan_id, semaphore) for loan_id in eligible_loans]
    results = await asyncio.gather(*tasks)
    
    # Analyze results
    successful = []
    failed = []
    
    for loan_id, success, data in results:
        if success:
            successful.append((loan_id, data))
        else:
            failed.append((loan_id, data))
    
    # Print summary
    print("\n" + "="*80)
    print("BATCH PROCESSING COMPLETE")
    print("="*80)
    print(f"\n✅ Successful: {len(successful)}/{len(eligible_loans)} loans")
    print(f"❌ Failed: {len(failed)}/{len(eligible_loans)} loans")
    
    if failed:
        print("\nFailed loans:")
        for loan_id, error in failed:
            print(f"  - {loan_id}: {error}")
    
    # Save aggregate summary
    if successful:
        print("\n" + "="*80)
        print("SAVING AGGREGATE DATA")
        print("="*80)
        
        # Create list of all comparison data
        all_comparisons = [data for loan_id, data in successful]
        
        # Save to reports directory
        reports_dir = base_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        output_file = reports_dir / "all_loans_income_comparison.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_comparisons, indent=2, fp=f)
        
        print(f"\n✅ Saved aggregate comparison data to: {output_file}")
        print(f"   Contains {len(all_comparisons)} loan comparison records")
        print("\nYou can now load this into a pandas DataFrame with:")
        print(f"   import pandas as pd")
        print(f"   df = pd.read_json('{output_file}')")
        
        # Print some quick stats
        print("\n" + "="*80)
        print("QUICK STATISTICS")
        print("="*80)
        
        # Count by complexity
        complexity_counts = {}
        for comp in all_comparisons:
            complexity = comp.get('complexity_level', 'unknown')
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        print("\nBy Complexity Level:")
        for complexity, count in sorted(complexity_counts.items()):
            print(f"  {complexity}: {count}")
        
        # Count by consistency rating
        consistency_counts = {}
        for comp in all_comparisons:
            rating = comp.get('ai_consistency_rating', 'unknown')
            consistency_counts[rating] = consistency_counts.get(rating, 0) + 1
        
        print("\nBy AI Consistency Rating:")
        for rating, count in sorted(consistency_counts.items()):
            print(f"  {rating}: {count}")
        
        # Average accuracy
        avg_diffs = [abs(comp.get('ai_avg_vs_final_1003_pct', 0)) for comp in all_comparisons]
        median_diffs = [abs(comp.get('ai_median_vs_final_1003_pct', 0)) for comp in all_comparisons]
        
        if avg_diffs:
            print(f"\nAverage Accuracy (AI Avg vs Final 1003):")
            print(f"  Mean absolute error: {sum(avg_diffs)/len(avg_diffs):.2f}%")
            print(f"  Max error: {max(avg_diffs):.2f}%")
        
        if median_diffs:
            print(f"\nMedian Accuracy (AI Median vs Final 1003):")
            print(f"  Mean absolute error: {sum(median_diffs)/len(median_diffs):.2f}%")
            print(f"  Max error: {max(median_diffs):.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
