"""
Process Last 4 Loans Through Complete Pipeline
===============================================
Processes loans 1000178625, 1000178635, 1000178636, 1000178638 through:
1. Harvest API download + Document Intelligence OCR
2. Semantic JSON compression
3. Income document classification
4. Form 1003 timeline extraction
5. Employment history generation
6. Income analysis (3 runs)
"""

import subprocess
import sys
from pathlib import Path

LOANS = [
    "1000178625",
    "1000178635",
    "1000178636",
    "1000178638"
]

def run_command(description, command):
    """Run a command and report status."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(command)}")
    print()
    
    result = subprocess.run(command, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"\n⚠️  Command failed with exit code {result.returncode}")
        return False
    
    print(f"\n✅ {description} - COMPLETED")
    return True


def process_loan(loan_id):
    """Process a single loan through the complete pipeline."""
    print(f"\n{'#'*80}")
    print(f"# PROCESSING LOAN {loan_id}")
    print(f"{'#'*80}\n")
    
    metadata_file = f"loan_files_inputs/loan_{loan_id}_tree.json"
    
    # Step 1: Download from Harvest API and run Document Intelligence
    if not run_command(
        f"Step 1/{loan_id}: Download PDFs and run Document Intelligence OCR",
        [sys.executable, "pipeline/process_from_harvest_api.py", metadata_file, loan_id]
    ):
        print(f"\n❌ Failed to process {loan_id} at Step 1 - SKIPPING")
        return False
    
    # Step 2: Convert to semantic JSON
    if not run_command(
        f"Step 2/{loan_id}: Convert to semantic JSON",
        [sys.executable, "pipeline/process_semantic_compression.py", loan_id]
    ):
        print(f"\n❌ Failed to process {loan_id} at Step 2 - SKIPPING")
        return False
    
    # Step 3: Classify income documents
    if not run_command(
        f"Step 3/{loan_id}: Classify income-relevant documents",
        [sys.executable, "pipeline/classify_income_documents.py", loan_id]
    ):
        print(f"\n❌ Failed to process {loan_id} at Step 3 - SKIPPING")
        return False
    
    # Step 4: Generate Form 1003 timeline
    if not run_command(
        f"Step 4/{loan_id}: Extract Form 1003 income timeline",
        [sys.executable, "agents/form_1003_income_tracker.py", loan_id]
    ):
        print(f"\n❌ Failed to process {loan_id} at Step 4 - SKIPPING")
        return False
    
    # Step 5: Generate employment history
    if not run_command(
        f"Step 5/{loan_id}: Generate employment history",
        [sys.executable, "agents/employment_history_agent.py", loan_id]
    ):
        print(f"\n❌ Failed to process {loan_id} at Step 5 - SKIPPING")
        return False
    
    # Step 6: Run income analysis (3 runs)
    if not run_command(
        f"Step 6/{loan_id}: Run income analysis (3 runs)",
        [sys.executable, "agents/income_analysis_agent.py", loan_id, "3"]
    ):
        print(f"\n❌ Failed to process {loan_id} at Step 6 - SKIPPING")
        return False
    
    print(f"\n{'#'*80}")
    print(f"# ✅ LOAN {loan_id} COMPLETED SUCCESSFULLY")
    print(f"{'#'*80}\n")
    return True


def main():
    """Process all 4 loans."""
    print("\n" + "="*80)
    print("BATCH PROCESSING LAST 4 LOANS")
    print("="*80)
    print(f"Loans to process: {', '.join(LOANS)}")
    print("="*80 + "\n")
    
    results = {}
    
    for loan_id in LOANS:
        success = process_loan(loan_id)
        results[loan_id] = success
    
    # Summary
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    
    for loan_id, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{loan_id}: {status}")
    
    successful = sum(1 for s in results.values() if s)
    print(f"\nTotal: {successful}/{len(LOANS)} loans processed successfully")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
