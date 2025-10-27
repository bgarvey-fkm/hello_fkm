"""
Batch Employment History Generator
==================================
Runs employment_history_agent.py in parallel for multiple loans.

Usage:
    python batch_employment_history.py [max_concurrent] [--force]
    
    max_concurrent: Maximum number of loans to process simultaneously (default: 10)
    --force: Regenerate employment histories even if they already exist
    
    By default, skips loans that already have employment_history.json files.

Example:
    python batch_employment_history.py 5           # Skip existing, max 5 concurrent
    python batch_employment_history.py 5 --force   # Regenerate all, max 5 concurrent
"""

import asyncio
import sys
from pathlib import Path
from agents.employment_history_agent import run_employment_history_analysis


async def generate_employment_history_with_semaphore(loan_id, semaphore):
    """
    Run employment history generation for a single loan with semaphore control.
    
    Args:
        loan_id: The loan identifier
        semaphore: asyncio.Semaphore for concurrency control
        
    Returns:
        Tuple of (loan_id, success, error_message)
    """
    async with semaphore:
        try:
            print(f"\n{'='*80}")
            print(f">> Starting employment history generation for loan {loan_id}...")
            print(f"{'='*80}")
            
            await run_employment_history_analysis(loan_id)
            
            print(f"\n{'='*80}")
            print(f">> ✓ Completed employment history for loan {loan_id}")
            print(f"{'='*80}")
            
            return (loan_id, True, None)
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n{'='*80}")
            print(f">> ✗ ERROR in loan {loan_id}: {error_msg}")
            print(f"{'='*80}")
            return (loan_id, False, error_msg)


async def generate_all_employment_histories_parallel(max_concurrent=10, skip_existing=True):
    """
    Generate employment histories for all loans in parallel.
    
    Args:
        max_concurrent: Maximum number of concurrent processes
        skip_existing: If True, skip loans that already have employment_history.json
    """
    # Find all loan directories
    loan_docs_dir = Path("loan_docs")
    if not loan_docs_dir.exists():
        print("ERROR: loan_docs directory not found")
        return
    
    # Get all loan IDs that have semantic_json folders (already classified)
    loan_ids = []
    skipped_count = 0
    for loan_dir in sorted(loan_docs_dir.iterdir()):
        if loan_dir.is_dir() and (loan_dir / "semantic_json").exists():
            # Check if employment history already exists
            if skip_existing and (loan_dir / "employment_history" / "employment_history.json").exists():
                skipped_count += 1
                continue
            loan_ids.append(loan_dir.name)
    
    if not loan_ids:
        print("No loans found with semantic_json folders (run classification first)")
        return
    
    print(f"\n{'='*80}")
    print(f"BATCH EMPLOYMENT HISTORY GENERATION")
    print(f"{'='*80}")
    if skip_existing and skipped_count > 0:
        print(f"Skipped {skipped_count} loans (already have employment history)")
    print(f"Found {len(loan_ids)} loans to process")
    print(f"Max concurrent: {max_concurrent}")
    print(f"{'='*80}\n")
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Create tasks for all loans
    tasks = [
        generate_employment_history_with_semaphore(loan_id, semaphore)
        for loan_id in loan_ids
    ]
    
    # Run all tasks in parallel (with semaphore limiting concurrency)
    results = await asyncio.gather(*tasks)
    
    # Summarize results
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Total loans processed: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed loans:")
        for loan_id, _, error in failed:
            print(f"  - {loan_id}: {error}")
    
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    max_concurrent = 10
    skip_existing = True
    
    for arg in sys.argv[1:]:
        if arg == '--force':
            skip_existing = False
        else:
            try:
                max_concurrent = int(arg)
            except ValueError:
                print(f"ERROR: Invalid max_concurrent value: {arg}")
                print("Usage: python batch_employment_history.py [max_concurrent] [--force]")
                sys.exit(1)
    
    asyncio.run(generate_all_employment_histories_parallel(max_concurrent, skip_existing))


if __name__ == "__main__":
    main()
