"""
Batch test the refactored workflow (scenario classification + decision tree)
for all loans with semantic_json data.
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil

def get_loan_ids():
    """Get all loan IDs that have semantic_json directories."""
    loan_docs_dir = Path("loan_docs")
    loan_ids = []
    
    for loan_dir in loan_docs_dir.iterdir():
        if loan_dir.is_dir():
            semantic_json_dir = loan_dir / "semantic_json"
            if semantic_json_dir.exists() and list(semantic_json_dir.glob("*.json")):
                loan_ids.append(loan_dir.name)
    
    return sorted(loan_ids)

def clear_income_analysis(loan_id):
    """Delete all files in the income_analysis directory for a loan."""
    income_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    if income_dir.exists():
        try:
            shutil.rmtree(income_dir)
            income_dir.mkdir(parents=True)
            print(f"  ✓ Cleared income_analysis directory for {loan_id}")
            return True
        except Exception as e:
            print(f"  ✗ Failed to clear {loan_id}: {e}")
            return False
    else:
        income_dir.mkdir(parents=True)
        print(f"  ✓ Created income_analysis directory for {loan_id}")
        return True

def run_scenario_classifier(loan_id):
    """Run the scenario classifier for a loan."""
    try:
        result = subprocess.run(
            [".venv/Scripts/python.exe", "agents/income_scenario_classifier.py", loan_id],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f"  ✓ Scenario classified for {loan_id}")
            return True
        else:
            print(f"  ✗ Scenario classification failed for {loan_id}")
            print(f"    Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Scenario classification timed out for {loan_id}")
        return False
    except Exception as e:
        print(f"  ✗ Error running scenario classifier for {loan_id}: {e}")
        return False

def run_income_analysis(loan_id, num_runs=10):
    """Run income analysis for a loan."""
    try:
        result = subprocess.run(
            [".venv/Scripts/python.exe", "agents/income_analysis_agent.py", loan_id, str(num_runs)],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0 or "CONSISTENCY SUMMARY" in result.stdout:
            print(f"  ✓ Income analysis complete for {loan_id} ({num_runs} runs)")
            return True
        else:
            print(f"  ✗ Income analysis failed for {loan_id}")
            print(f"    Error: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Income analysis timed out for {loan_id}")
        return False
    except Exception as e:
        print(f"  ✗ Error running income analysis for {loan_id}: {e}")
        return False

def main():
    """Main batch processing function."""
    print("=" * 80)
    print("BATCH TEST: REFACTORED WORKFLOW (SCENARIO + DECISION TREE)")
    print("=" * 80)
    
    # Get command line arguments
    num_runs = 10
    if len(sys.argv) > 1:
        try:
            num_runs = int(sys.argv[1])
        except:
            print(f"Invalid number of runs: {sys.argv[1]}, using default: 10")
    
    print(f"\nNumber of runs per loan: {num_runs}")
    
    # Get all loan IDs
    loan_ids = get_loan_ids()
    print(f"\nFound {len(loan_ids)} loans with semantic_json data")
    
    # Track results
    results = {
        'successful': [],
        'failed_clear': [],
        'failed_scenario': [],
        'failed_analysis': [],
        'no_income_docs': []
    }
    
    # Process each loan
    for i, loan_id in enumerate(loan_ids, 1):
        print(f"\n[{i}/{len(loan_ids)}] Processing Loan {loan_id}")
        print("-" * 80)
        
        # Step 1: Clear old results
        if not clear_income_analysis(loan_id):
            results['failed_clear'].append(loan_id)
            continue
        
        # Step 2: Run scenario classifier
        if not run_scenario_classifier(loan_id):
            # Check if it's because there are no income docs
            scenario_file = Path(f"loan_docs/{loan_id}/income_analysis/income_scenario.json")
            if not scenario_file.exists():
                results['no_income_docs'].append(loan_id)
            else:
                results['failed_scenario'].append(loan_id)
            continue
        
        # Step 3: Run income analysis
        if not run_income_analysis(loan_id, num_runs):
            results['failed_analysis'].append(loan_id)
            continue
        
        results['successful'].append(loan_id)
    
    # Print summary
    print("\n" + "=" * 80)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 80)
    print(f"\nTotal Loans: {len(loan_ids)}")
    print(f"  ✓ Successful: {len(results['successful'])}")
    print(f"  ⚠ No Income Docs: {len(results['no_income_docs'])}")
    print(f"  ✗ Failed Clear: {len(results['failed_clear'])}")
    print(f"  ✗ Failed Scenario: {len(results['failed_scenario'])}")
    print(f"  ✗ Failed Analysis: {len(results['failed_analysis'])}")
    
    if results['successful']:
        print(f"\nSuccessful Loans ({len(results['successful'])}):")
        for loan_id in results['successful']:
            print(f"  - {loan_id}")
    
    if results['no_income_docs']:
        print(f"\nNo Income Documents ({len(results['no_income_docs'])}):")
        for loan_id in results['no_income_docs']:
            print(f"  - {loan_id}")
    
    if results['failed_clear'] or results['failed_scenario'] or results['failed_analysis']:
        print(f"\nFailed Loans:")
        for loan_id in results['failed_clear']:
            print(f"  - {loan_id} (failed to clear)")
        for loan_id in results['failed_scenario']:
            print(f"  - {loan_id} (scenario classification failed)")
        for loan_id in results['failed_analysis']:
            print(f"  - {loan_id} (income analysis failed)")
    
    print("\n" + "=" * 80)
    print(f"Run complete. Check loan_docs/{{loan_id}}/income_analysis/ for results.")
    print("=" * 80)

if __name__ == "__main__":
    main()
