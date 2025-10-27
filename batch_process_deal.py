# -*- coding: utf-8 -*-
"""
Batch Income Analysis Pipeline

Fetches loans from a Harvest API deal and processes them through the complete pipeline:
1. Get deal data from Harvest API
2. Select N loans from the deal
3. For each loan:
   - Fetch file metadata
   - Download and process with Document Intelligence (raw_json)
   - Create semantic JSON (semantic_json)
   
Usage:
    python batch_process_deal.py --deal-id 2 --num-loans 10
    python batch_process_deal.py --deal-id 2 --num-loans 10 --loan-ids 1000175957,1000176265
    python batch_process_deal.py --deal-id 2 --num-loans 10 --parallel --max-concurrent 5
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
import requests
import urllib3
from dotenv import load_dotenv

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

HARVEST_DEAL_API = "https://harvestapi.firstkeyholdings.net:60000/api/deal/"
HARVEST_TREE_API = "https://harvestapi.firstkeyholdings.net:60000/api/doc_meta_data_tree/"


def fetch_deal_loans(deal_id: int):
    """Fetch all loans from a deal."""
    url = f"{HARVEST_DEAL_API}{deal_id}"
    print(f"\n>> Fetching deal {deal_id} data from Harvest API...")
    
    response = requests.get(url, verify=False)
    
    if response.status_code != 200:
        print(f"ERROR: Error fetching deal: {response.status_code}")
        sys.exit(1)
    
    loans = response.json()
    print(f"SUCCESS: Found {len(loans)} loans in deal {deal_id}")
    
    return loans


def fetch_loan_file_tree(loan_identifier_id: int):
    """Fetch document tree for a loan using its LoanIdentifierId (FileId)."""
    url = f"{HARVEST_TREE_API}{loan_identifier_id}"
    response = requests.get(url, verify=False)
    
    if response.status_code != 200:
        print(f"  WARNING: Could not fetch file tree for LoanIdentifierId {loan_identifier_id}: {response.status_code}")
        return []
    
    return response.json()

def select_loans(all_loans: list, num_loans: int = None, loan_ids: list = None):
    """Select loans to process."""
    
    if loan_ids:
        # Filter by specific loan IDs
        selected = [loan for loan in all_loans if loan['LoanNumber'] in loan_ids]
        print(f"\n>> Selected {len(selected)} specified loans")
    elif num_loans:
        # Take first N loans
        selected = all_loans[:num_loans]
        print(f"\n>> Selected first {len(selected)} loans")
    else:
        # Process all
        selected = all_loans
        print(f"\n>> Processing all {len(selected)} loans")
    
    return selected


async def run_pipeline_step(command: list, description: str):
    """Run a pipeline step (async) using list of args instead of shell."""
    print(f"  >> {description}...")
    
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        print(f"  ERROR: {stderr.decode()}")
        return False
    
    print(f"  SUCCESS: {description} complete")
    return True


async def process_single_loan(loan, deal_id: int, skip_existing: bool = True, loan_index: int = 1, total_loans: int = 1):
    """Process a single loan through the complete pipeline."""
    
    loan_number = loan['LoanNumber']
    loan_identifier_id = loan.get('LoanIdentifierId')
    security_id = loan['SecurityId']
    borrower = loan['Borrower_Name']
    
    print(f"\n{'='*80}")
    print(f">> [{loan_index}/{total_loans}] Processing Loan: {loan_number}")
    print(f"   Borrower: {borrower}")
    print(f"   Security ID: {security_id}")
    print(f"   LoanIdentifierId (FileId): {loan_identifier_id}")
    print(f"{'='*80}")
    
    # Check if loan already processed
    semantic_dir = Path(f"loan_docs/{loan_number}/semantic_json")
    if skip_existing and semantic_dir.exists():
        file_count = len(list(semantic_dir.glob("*.json")))
        if file_count > 0:
            print(f"  ✓ SKIPPING: Loan {loan_number} already processed ({file_count} semantic files exist)")
            return True
        else:
            print(f"  >> semantic_json folder exists but is empty, processing...")
    
    # Step 1: Fetch file tree metadata from API
    print(f"\n  >> Step 1: Fetching document tree from Harvest API...")
    files = fetch_loan_file_tree(loan_identifier_id)
    
    if not files:
        print(f"  WARNING: No files found for loan {loan_number}, skipping...")
        return False
    
    print(f"  SUCCESS: Found {len(files)} files in document tree")
    
    # Step 2: Save file tree as input JSON (process_from_harvest_api.py expects array of file metadata)
    input_dir = Path("loan_files_inputs")
    input_dir.mkdir(exist_ok=True)
    input_file = input_dir / f"loan_{loan_number}_tree.json"
    
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(files, f, indent=2)
    
    print(f"  SUCCESS: Created input file: {input_file} ({len(files)} files)")
    
    # Step 3: Run process_from_harvest_api.py (expects: metadata_json loan_id)
    python_exe = Path('.venv/Scripts/python.exe')
    success = await run_pipeline_step(
        [str(python_exe), 'pipeline/process_from_harvest_api.py', str(input_file), loan_number],
        f"Downloading and processing with Document Intelligence to raw_json/"
    )
    
    if not success:
        return False
    
    # Step 4: Run process_semantic_compression.py
    success = await run_pipeline_step(
        [str(python_exe), 'pipeline/process_semantic_compression.py', loan_number],
        f"Creating semantic JSON to semantic_json/"
    )
    
    return success


async def process_loans_sequential(selected_loans, deal_id, skip_existing):
    """Process loans one at a time (original sequential behavior)."""
    results = []
    for i, loan in enumerate(selected_loans, 1):
        print(f"\n\n>> [{i}/{len(selected_loans)}] Processing {loan['LoanNumber']}...")
        success = await process_single_loan(loan, deal_id, skip_existing, i, len(selected_loans))
        results.append({
            'loan_number': loan['LoanNumber'],
            'borrower': loan['Borrower_Name'],
            'success': success
        })
    return results


async def process_loans_parallel(selected_loans, deal_id, skip_existing, max_concurrent=5):
    """Process loans in parallel with a concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(loan, index):
        async with semaphore:
            success = await process_single_loan(loan, deal_id, skip_existing, index, len(selected_loans))
            return {
                'loan_number': loan['LoanNumber'],
                'borrower': loan['Borrower_Name'],
                'success': success
            }
    
    print(f"\n>> Processing {len(selected_loans)} loans with max {max_concurrent} concurrent")
    tasks = [process_with_limit(loan, i+1) for i, loan in enumerate(selected_loans)]
    results = await asyncio.gather(*tasks)
    return results


async def main():
    parser = argparse.ArgumentParser(description='Batch process loans from Harvest API deal')
    parser.add_argument('--deal-id', type=int, required=True, help='Deal ID to process')
    parser.add_argument('--num-loans', type=int, help='Number of loans to process (default: all)')
    parser.add_argument('--loan-ids', type=str, help='Comma-separated list of specific loan numbers to process')
    parser.add_argument('--skip-existing', action='store_true', default=True, help='Skip loans that already have semantic_json (default: True)')
    parser.add_argument('--reprocess', action='store_true', help='Force reprocess all loans (ignore existing semantic_json)')
    parser.add_argument('--parallel', action='store_true', help='Process loans in parallel instead of sequentially')
    parser.add_argument('--max-concurrent', type=int, default=5, help='Maximum number of concurrent loans to process (default: 5)')
    
    args = parser.parse_args()
    
    # Determine skip_existing based on flags
    skip_existing = args.skip_existing and not args.reprocess
    
    # Parse loan IDs if provided
    loan_ids_list = None
    if args.loan_ids:
        loan_ids_list = [lid.strip() for lid in args.loan_ids.split(',')]
    
    print(f"\n{'='*80}")
    print(f">> BATCH PROCESSING PIPELINE")
    print(f"{'='*80}")
    print(f"Deal ID: {args.deal_id}")
    if loan_ids_list:
        print(f"Target Loans: {', '.join(loan_ids_list)}")
    elif args.num_loans:
        print(f"Target Count: {args.num_loans} loans")
    else:
        print(f"Target Count: ALL loans in deal")
    print(f"Skip Existing: {skip_existing}")
    print(f"Processing Mode: {'PARALLEL' if args.parallel else 'SEQUENTIAL'}")
    if args.parallel:
        print(f"Max Concurrent: {args.max_concurrent}")
    print(f"{'='*80}")
    
    # Step 1: Fetch deal data
    all_loans = fetch_deal_loans(args.deal_id)
    
    # Step 2: Select loans
    selected_loans = select_loans(all_loans, args.num_loans, loan_ids_list)
    
    if not selected_loans:
        print(f"\nERROR: No loans selected for processing")
        sys.exit(1)
    
    # Step 3: Process loans (sequential or parallel)
    print(f"\n{'='*80}")
    print(f">> PROCESSING {len(selected_loans)} LOANS")
    print(f"{'='*80}")
    
    if args.parallel:
        results = await process_loans_parallel(selected_loans, args.deal_id, skip_existing, args.max_concurrent)
    else:
        results = await process_loans_sequential(selected_loans, args.deal_id, skip_existing)
    
    # Step 4: Summary
    print(f"\n\n{'='*80}")
    print(f">> BATCH PROCESSING SUMMARY")
    print(f"{'='*80}")
    print(f"Total Loans: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    
    print(f"\nSUCCESS:")
    for r in results:
        if r['success']:
            print(f"   • {r['loan_number']} - {r['borrower']}")
    
    if any(not r['success'] for r in results):
        print(f"\nFAILED:")
        for r in results:
            if not r['success']:
                print(f"   • {r['loan_number']} - {r['borrower']}")
    
    print(f"\n{'='*80}")
    print(f"SUCCESS: BATCH PROCESSING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
