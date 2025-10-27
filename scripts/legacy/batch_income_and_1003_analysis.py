"""
Batch Income and Form 1003 Analysis

Runs income analysis and Form 1003 tracking on multiple loans from a deal.

For each loan:
1. Runs Form 1003 income tracker once (extracts borrower-stated income)
2. Runs income analysis agent N times (default 5) to test AI consistency
3. Generates comparison reports

Usage:
    python batch_income_and_1003_analysis.py --deal-id <id> --num-loans <count> [--income-runs <count>]
    
Examples:
    # Process first 10 loans with 5 income runs each
    python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 10
    
    # Process 20 loans with 3 income runs each
    python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 20 --income-runs 3
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Fix console encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Import the analysis functions
sys.path.insert(0, str(Path(__file__).parent / 'agents'))
from form_1003_income_tracker import identify_1003_files, sort_by_upload_date, extract_income_from_all_1003s, save_analysis as save_1003_analysis, create_html_report as create_1003_html
from income_analysis_agent import run_consistency_test_async


async def process_loan_analysis(loan_number: str, income_runs: int = 5):
    """
    Process a single loan: run Form 1003 tracker and income analysis.
    
    Args:
        loan_number: Loan number to process
        income_runs: Number of income analysis runs (default 5)
    
    Returns:
        dict with success status and results
    """
    
    print(f"\n{'='*80}")
    print(f">> ANALYZING LOAN {loan_number}")
    print(f"{'='*80}\n")
    
    result = {
        'loan_number': loan_number,
        'form_1003_success': False,
        'income_analysis_success': False,
        'form_1003_income': None,
        'ai_income_avg': None,
        'variance': None,
        'error': None
    }
    
    # Check if semantic_json exists
    semantic_dir = Path(f"loan_docs/{loan_number}/semantic_json")
    if not semantic_dir.exists():
        print(f"❌ No semantic_json folder found for loan {loan_number}")
        print(f"   Run batch_process_deal.py first to process this loan\n")
        result['error'] = 'No semantic_json folder'
        return result
    
    try:
        # Step 1: Run Form 1003 income tracker (once)
        print(f"📋 Step 1: Extracting Form 1003 income timeline...")
        
        form_1003_files = identify_1003_files(loan_number)
        
        if form_1003_files:
            sorted_1003 = sort_by_upload_date(form_1003_files)
            analysis_1003 = extract_income_from_all_1003s(loan_number, sorted_1003)
            
            if analysis_1003:
                # Save Form 1003 analysis
                save_1003_analysis(loan_number, analysis_1003)
                create_1003_html(loan_number, analysis_1003)
                
                result['form_1003_success'] = True
                
                # Extract final income from last version
                income_versions = analysis_1003.get('income_by_version', [])
                if income_versions:
                    final_version = income_versions[-1]
                    result['form_1003_income'] = final_version.get('combined_monthly_income', 0)
                    print(f"   ✅ Form 1003 Income: ${result['form_1003_income']:,.2f}/month")
                else:
                    print(f"   ⚠️  Form 1003 found but no income extracted")
        else:
            print(f"   ⚠️  No Form 1003 documents found for loan {loan_number}")
        
        # Step 2: Run income analysis (N times)
        print(f"\n💰 Step 2: Running AI income analysis ({income_runs} runs)...")
        
        # Run the async income analysis
        await run_consistency_test_async(loan_number, income_runs, refilter=False)
        
        result['income_analysis_success'] = True
        
        # Load the comprehensive summary to get average
        summary_file = Path(f"loan_docs/{loan_number}/income_analysis/consistency_summary_all.json")
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                stats = summary.get('statistics', {})
                result['ai_income_avg'] = stats.get('average_income', 0)
                result['variance'] = stats.get('variance_percentage', 0)
                print(f"   ✅ AI Average Income: ${result['ai_income_avg']:,.2f}/month")
                print(f"   📊 Variance: {result['variance']:.2f}%")
        
        # Calculate comparison if we have both
        if result['form_1003_income'] and result['ai_income_avg']:
            diff = result['ai_income_avg'] - result['form_1003_income']
            diff_pct = (diff / result['form_1003_income']) * 100
            print(f"\n📊 COMPARISON:")
            print(f"   Form 1003:  ${result['form_1003_income']:,.2f}")
            print(f"   AI Average: ${result['ai_income_avg']:,.2f}")
            print(f"   Difference: ${diff:,.2f} ({diff_pct:+.2f}%)")
        
        print(f"\n✅ Loan {loan_number} analysis complete!")
        
    except Exception as e:
        print(f"\n❌ Error processing loan {loan_number}: {e}")
        result['error'] = str(e)
    
    return result


async def batch_analyze_loans(deal_id: int, num_loans: int, income_runs: int = 5):
    """
    Process multiple loans in batch.
    
    Args:
        deal_id: Deal ID to process
        num_loans: Number of loans to process
        income_runs: Number of income analysis runs per loan
    """
    
    print(f"\n{'='*80}")
    print(f">> BATCH INCOME & FORM 1003 ANALYSIS")
    print(f"{'='*80}")
    print(f"Deal ID: {deal_id}")
    print(f"Target Loans: {num_loans}")
    print(f"Income Runs per Loan: {income_runs}")
    print(f"{'='*80}\n")
    
    # Load deal data
    deal_file = Path(f"portfolio_data/deal_{deal_id}_data.json")
    if not deal_file.exists():
        print(f"❌ Deal data file not found: {deal_file}")
        print(f"   Run batch_process_deal.py first to fetch deal data")
        return
    
    with open(deal_file, 'r') as f:
        deal_data = json.load(f)
    
    print(f"✅ Loaded {len(deal_data)} loans from deal {deal_id}")
    
    # Get loan numbers (not LoanIdentifierId!)
    selected_loans = deal_data[:num_loans]
    loan_numbers = [loan['LoanNumber'] for loan in selected_loans]
    
    print(f"📋 Selected {len(loan_numbers)} loans to analyze\n")
    
    # Process each loan
    results = []
    for idx, loan_number in enumerate(loan_numbers, 1):
        print(f"\n{'='*80}")
        print(f">> [{idx}/{len(loan_numbers)}] Processing {loan_number}")
        print(f"{'='*80}")
        
        result = await process_loan_analysis(loan_number, income_runs)
        results.append(result)
        
        # Brief pause between loans
        if idx < len(loan_numbers):
            await asyncio.sleep(2)
    
    # Generate summary report
    print(f"\n{'='*80}")
    print(f"📊 BATCH ANALYSIS SUMMARY")
    print(f"{'='*80}\n")
    
    successful_loans = [r for r in results if r['form_1003_success'] or r['income_analysis_success']]
    form_1003_count = len([r for r in results if r['form_1003_success']])
    income_analysis_count = len([r for r in results if r['income_analysis_success']])
    both_count = len([r for r in results if r['form_1003_success'] and r['income_analysis_success']])
    
    print(f"Total Loans Processed: {len(results)}")
    print(f"✅ Form 1003 Extracted: {form_1003_count}")
    print(f"✅ Income Analysis Complete: {income_analysis_count}")
    print(f"✅ Both Completed: {both_count}")
    print(f"❌ Errors: {len([r for r in results if r.get('error')])}")
    
    # Show loans with both analyses
    if both_count > 0:
        print(f"\n{'='*80}")
        print(f"📈 INCOME COMPARISON (Loans with Both Analyses)")
        print(f"{'='*80}\n")
        
        print(f"{'Loan Number':<15} {'Form 1003':<15} {'AI Average':<15} {'Difference':<15} {'% Diff':<10}")
        print("-" * 80)
        
        for r in results:
            if r['form_1003_success'] and r['income_analysis_success']:
                if r['form_1003_income'] and r['ai_income_avg']:
                    diff = r['ai_income_avg'] - r['form_1003_income']
                    diff_pct = (diff / r['form_1003_income']) * 100
                    print(f"{r['loan_number']:<15} ${r['form_1003_income']:>13,.2f} ${r['ai_income_avg']:>13,.2f} ${diff:>13,.2f} {diff_pct:>8.2f}%")
    
    # Save batch results
    output_dir = Path("portfolio_data")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"batch_analysis_deal{deal_id}_{timestamp}.json"
    
    batch_summary = {
        'deal_id': deal_id,
        'analysis_date': datetime.now().isoformat(),
        'num_loans_targeted': num_loans,
        'num_loans_processed': len(results),
        'income_runs_per_loan': income_runs,
        'statistics': {
            'form_1003_extracted': form_1003_count,
            'income_analysis_completed': income_analysis_count,
            'both_completed': both_count,
            'errors': len([r for r in results if r.get('error')])
        },
        'results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(batch_summary, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"💾 Batch results saved to: {output_file}")
    print(f"{'='*80}\n")
    
    print("✅ BATCH ANALYSIS COMPLETE!\n")


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description='Batch Income and Form 1003 Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process first 10 loans with 5 income runs each
  python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 10
  
  # Process 20 loans with 3 income runs each
  python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 20 --income-runs 3
        """
    )
    
    parser.add_argument('--deal-id', type=int, required=True,
                        help='Deal ID to process')
    parser.add_argument('--num-loans', type=int, required=True,
                        help='Number of loans to process')
    parser.add_argument('--income-runs', type=int, default=5,
                        help='Number of income analysis runs per loan (default: 5)')
    
    args = parser.parse_args()
    
    # Run the batch analysis
    asyncio.run(batch_analyze_loans(args.deal_id, args.num_loans, args.income_runs))


if __name__ == "__main__":
    main()
