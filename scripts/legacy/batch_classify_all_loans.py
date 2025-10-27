# -*- coding: utf-8 -*-
"""
Batch Income Document Classification

Re-classifies income documents for ALL loans in parallel using the --refilter flag.
"""

import asyncio
import sys
from pathlib import Path
from pipeline.classify_income_documents import classify_income_documents


async def classify_all_loans_parallel(max_concurrent=10):
    """
    Classify income documents for all loans in parallel.
    
    Args:
        max_concurrent: Maximum number of loans to process concurrently
    """
    # Find all loan directories
    loan_docs_dir = Path("loan_docs")
    
    if not loan_docs_dir.exists():
        print("Error: loan_docs directory not found")
        sys.exit(1)
    
    # Get all loan IDs (directories that contain semantic_json folder)
    loan_ids = []
    for loan_dir in sorted(loan_docs_dir.iterdir()):
        if loan_dir.is_dir() and (loan_dir / "semantic_json").exists():
            loan_ids.append(loan_dir.name)
    
    if not loan_ids:
        print("No loans found with semantic_json folders")
        sys.exit(1)
    
    print("\n" + "="*80)
    print(f"BATCH INCOME DOCUMENT CLASSIFICATION")
    print("="*80)
    print(f"Found {len(loan_ids)} loans to process")
    print(f"Mode: RE-FILTER (forcing re-classification)")
    print(f"Max concurrent: {max_concurrent}")
    print("="*80 + "\n")
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def classify_with_semaphore(loan_id):
        """Classify a single loan with concurrency control."""
        async with semaphore:
            try:
                print(f"\n>> Starting classification for loan {loan_id}...")
                result = await classify_income_documents(loan_id, refilter=True)
                print(f">> ✓ Loan {loan_id} complete: {result['income_relevant']} income-relevant docs")
                return (loan_id, result, None)
            except Exception as e:
                print(f">> ✗ Loan {loan_id} FAILED: {e}")
                return (loan_id, None, str(e))
    
    # Process all loans in parallel
    tasks = [classify_with_semaphore(loan_id) for loan_id in loan_ids]
    results = await asyncio.gather(*tasks)
    
    # Summary
    print("\n" + "="*80)
    print("BATCH CLASSIFICATION COMPLETE")
    print("="*80)
    
    successful = [r for r in results if r[1] is not None]
    failed = [r for r in results if r[2] is not None]
    
    print(f"\nTotal loans processed: {len(loan_ids)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        total_docs = sum(r[1]['total_documents'] for r in successful)
        total_relevant = sum(r[1]['income_relevant'] for r in successful)
        total_excluded = sum(r[1]['excluded'] for r in successful)
        
        print(f"\nAggregate Statistics:")
        print(f"  Total documents: {total_docs:,}")
        print(f"  Income-relevant: {total_relevant:,}")
        print(f"  Excluded: {total_excluded:,}")
        print(f"  Relevance rate: {100*total_relevant/total_docs:.1f}%")
    
    if failed:
        print(f"\nFailed loans:")
        for loan_id, _, error in failed:
            print(f"  - {loan_id}: {error}")
    
    print("\n" + "="*80)


def main():
    """Main entry point."""
    max_concurrent = 10  # Adjust based on API rate limits
    
    if len(sys.argv) > 1:
        try:
            max_concurrent = int(sys.argv[1])
        except ValueError:
            print("Usage: python batch_classify_all_loans.py [max_concurrent]")
            print("Example: python batch_classify_all_loans.py 5")
            sys.exit(1)
    
    asyncio.run(classify_all_loans_parallel(max_concurrent))


if __name__ == "__main__":
    main()
