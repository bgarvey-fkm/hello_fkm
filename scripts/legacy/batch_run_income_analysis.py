"""
Batch Income Analysis Runner
=============================
Runs income_analysis_agent.py for multiple loans in parallel.

Usage:
    python batch_run_income_analysis.py [num_runs] [max_concurrent]
    
    num_runs: Number of analysis runs per loan (default: 3)
    max_concurrent: Maximum number of loans to process simultaneously (default: 3)

Example:
    python batch_run_income_analysis.py 3 3
"""

import asyncio
import subprocess
import sys
from pathlib import Path


async def run_income_analysis_for_loan(loan_id, num_runs, semaphore):
    """
    Run income analysis for a single loan with semaphore control.
    
    Args:
        loan_id: The loan identifier
        num_runs: Number of analysis runs to perform
        semaphore: asyncio.Semaphore for concurrency control
        
    Returns:
        True if successful, False otherwise
    """
    async with semaphore:
        try:
            print(f"\n{'='*80}")
            print(f">> Starting income analysis for loan {loan_id} ({num_runs} runs)...")
            print(f"{'='*80}\n")
            
            process = await asyncio.create_subprocess_exec(
                ".venv/Scripts/python.exe", 
                "agents/income_analysis_agent.py", 
                loan_id, 
                str(num_runs),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"\n{'='*80}")
                print(f">> ✓ Completed income analysis for loan {loan_id}")
                print(f"{'='*80}")
                return True
            else:
                print(f"\n{'='*80}")
                print(f">> ✗ ERROR in loan {loan_id}")
                print(f"{'='*80}")
                if stderr:
                    print(f"Error: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"\n{'='*80}")
            print(f">> ✗ EXCEPTION in loan {loan_id}: {e}")
            print(f"{'='*80}")
            return False


async def analyze_all_loans(num_runs=3, max_concurrent=3):
    """
    Analyze income for all loans in parallel.
    
    Args:
        num_runs: Number of analysis runs per loan
        max_concurrent: Maximum number of concurrent processes
    """
    # Find all loan directories
    loan_docs_dir = Path("loan_docs")
    if not loan_docs_dir.exists():
        print("ERROR: loan_docs directory not found")
        return
    
    # Get all loan IDs that have prerequisites
    loan_ids = []
    missing_prereq = 0
    
    for loan_dir in sorted(loan_docs_dir.iterdir()):
        if not loan_dir.is_dir():
            continue
            
        # Check prerequisites
        has_employment = (loan_dir / "employment_history" / "employment_history.json").exists()
        has_1003 = (loan_dir / "income_analysis" / "form_1003_income_timeline.json").exists()
        
        if has_employment and has_1003:
            loan_ids.append(loan_dir.name)
        else:
            missing_prereq += 1
    
    if not loan_ids:
        print("ERROR: No loans found with required prerequisites")
        print("\nRequired files:")
        print("  - employment_history/employment_history.json")
        print("  - income_analysis/form_1003_income_timeline.json")
        return
    
    print(f"\n{'='*80}")
    print(f"BATCH INCOME ANALYSIS")
    print(f"{'='*80}")
    if missing_prereq > 0:
        print(f"Skipped {missing_prereq} loans (missing prerequisites)")
    print(f"Found {len(loan_ids)} loans to process")
    print(f"Runs per loan: {num_runs}")
    print(f"Max concurrent: {max_concurrent}")
    print(f"{'='*80}\n")
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Create tasks for all loans
    tasks = [
        run_income_analysis_for_loan(loan_id, num_runs, semaphore)
        for loan_id in loan_ids
    ]
    
    # Run all tasks in parallel (with semaphore limiting concurrency)
    results = await asyncio.gather(*tasks)
    
    # Summarize results
    successful = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)
    
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Total loans processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    num_runs = 3
    max_concurrent = 3
    
    if len(sys.argv) > 1:
        try:
            num_runs = int(sys.argv[1])
        except ValueError:
            print(f"ERROR: Invalid num_runs value: {sys.argv[1]}")
            print("Usage: python batch_run_income_analysis.py [num_runs] [max_concurrent]")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            max_concurrent = int(sys.argv[2])
        except ValueError:
            print(f"ERROR: Invalid max_concurrent value: {sys.argv[2]}")
            print("Usage: python batch_run_income_analysis.py [num_runs] [max_concurrent]")
            sys.exit(1)
    
    asyncio.run(analyze_all_loans(num_runs, max_concurrent))


if __name__ == "__main__":
    main()
