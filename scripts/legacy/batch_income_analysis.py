"""
Batch Income Analysis Pipeline

Processes multiple loans through the complete pipeline:
1. Fetch and process documents (Harvest API → Document Intelligence → Semantic JSON)
2. Run income analysis N times per loan (consistency testing)
3. Run Form 1003 income tracker (stated income evolution)
4. Aggregate all results into a master JSON report

Usage:
    python batch_income_analysis.py --deal-id 2 --num-loans 5 --income-runs 5

Example:
    python batch_income_analysis.py --deal-id 2 --num-loans 5 --income-runs 5
"""

import json
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import time


def run_command(command, description):
    """Run a shell command and return success status."""
    print(f"\n{'='*80}")
    print(f"🔧 {description}")
    print(f"{'='*80}")
    print(f"Command: {command}\n")
    
    # Use PowerShell for UNC path support
    result = subprocess.run(
        ["powershell.exe", "-Command", command],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )
    
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
        return True
    else:
        print(f"❌ {description} - FAILED")
        print(f"Error: {result.stderr}")
        return False


def load_json_file(filepath):
    """Load JSON file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Batch Income Analysis Pipeline')
    parser.add_argument('--deal-id', type=int, required=True, help='Deal ID to process')
    parser.add_argument('--num-loans', type=int, default=5, help='Number of loans to process')
    parser.add_argument('--income-runs', type=int, default=5, help='Number of income analysis runs per loan')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("📊 BATCH INCOME ANALYSIS PIPELINE")
    print("="*80)
    print(f"Deal ID: {args.deal_id}")
    print(f"Number of Loans: {args.num_loans}")
    print(f"Income Analysis Runs per Loan: {args.income_runs}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Master results object
    master_results = {
        "pipeline_run": {
            "deal_id": args.deal_id,
            "num_loans": args.num_loans,
            "income_runs_per_loan": args.income_runs,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": None
        },
        "loans": []
    }
    
    # STEP 1: Batch process loans through the pipeline
    print("\n" + "="*80)
    print("STEP 1: BATCH PROCESSING LOANS")
    print("="*80)
    
    cmd = f".\\.venv\\Scripts\\python.exe batch_process_deal.py --deal-id {args.deal_id} --num-loans {args.num_loans}"
    success = run_command(cmd, f"Processing {args.num_loans} loans from deal {args.deal_id}")
    
    if not success:
        print("\n❌ Pipeline processing failed. Aborting.")
        return
    
    # Load the deal data to get loan IDs
    deal_file = Path(f"portfolio_data/deal_{args.deal_id}_data.json")
    if not deal_file.exists():
        print(f"\n❌ Deal data file not found: {deal_file}")
        return
    
    with open(deal_file, 'r', encoding='utf-8') as f:
        deal_data = json.load(f)
    
    loan_ids = [loan['LoanNumber'] for loan in deal_data[:args.num_loans]]
    
    print(f"\n✅ Loaded {len(loan_ids)} loan IDs:")
    for idx, loan_id in enumerate(loan_ids, 1):
        borrower_name = deal_data[idx-1].get('Borrower_Name', 'Unknown Unknown')
        print(f"  {idx}. Loan {loan_id} - {borrower_name}")
    
    # STEP 2: Process each loan through income analysis
    print("\n" + "="*80)
    print("STEP 2: INCOME ANALYSIS FOR EACH LOAN")
    print("="*80)
    
    for idx, loan_id in enumerate(loan_ids, 1):
        borrower_info = deal_data[idx-1]
        borrower_name = borrower_info.get('Borrower_Name', 'Unknown Unknown')
        
        print(f"\n{'='*80}")
        print(f"📋 LOAN {idx}/{len(loan_ids)}: {loan_id} - {borrower_name}")
        print(f"{'='*80}")
        
        loan_result = {
            "loan_id": loan_id,
            "borrower_name": borrower_name,
            "loan_amount": borrower_info.get('LoanAmount'),
            "property_address": f"{borrower_info.get('Property_Address', '')} {borrower_info.get('Property_City', '')} {borrower_info.get('Property_State', '')}".strip(),
            "income_analysis": None,
            "form_1003_tracker": None,
            "processing_errors": []
        }
        
        # Run income analysis N times
        print(f"\n🔄 Running income analysis {args.income_runs}x for loan {loan_id}...")
        cmd = f".\\.venv\\Scripts\\python.exe agents\\income_analysis_agent.py {loan_id} {args.income_runs}"
        success = run_command(cmd, f"Income Analysis {args.income_runs}x - Loan {loan_id}")
        
        if success:
            # Load the consistency report
            consistency_file = Path(f"reports/income_analysis_consistency_{loan_id}.json")
            if consistency_file.exists():
                loan_result["income_analysis"] = load_json_file(consistency_file)
                print(f"  ✅ Loaded income analysis results")
            else:
                loan_result["processing_errors"].append("Income analysis JSON not found")
        else:
            loan_result["processing_errors"].append("Income analysis failed")
        
        # Run Form 1003 income tracker
        print(f"\n📄 Running Form 1003 income tracker for loan {loan_id}...")
        cmd = f".\\.venv\\Scripts\\python.exe agents\\form_1003_income_tracker.py {loan_id}"
        success = run_command(cmd, f"Form 1003 Income Tracker - Loan {loan_id}")
        
        if success:
            # Find the most recent 1003 tracker file for this loan
            reports_dir = Path("reports")
            tracker_files = list(reports_dir.glob(f"form_1003_income_tracker_{loan_id}_*.json"))
            if tracker_files:
                latest_tracker = max(tracker_files, key=lambda p: p.stat().st_mtime)
                loan_result["form_1003_tracker"] = load_json_file(latest_tracker)
                print(f"  ✅ Loaded Form 1003 tracker results")
            else:
                loan_result["processing_errors"].append("Form 1003 tracker JSON not found")
        else:
            loan_result["processing_errors"].append("Form 1003 tracker failed")
        
        master_results["loans"].append(loan_result)
        
        print(f"\n✅ Completed processing for loan {loan_id}")
    
    # Calculate duration
    end_time = time.time()
    master_results["pipeline_run"]["duration_seconds"] = round(end_time - start_time, 2)
    
    # STEP 3: Save master results
    print("\n" + "="*80)
    print("STEP 3: SAVING MASTER RESULTS")
    print("="*80)
    
    output_file = Path(f"reports/batch_income_analysis_deal{args.deal_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_results, f, indent=2)
    
    print(f"\n✅ Master results saved to: {output_file}")
    
    # STEP 4: Print summary
    print("\n" + "="*80)
    print("📊 BATCH ANALYSIS SUMMARY")
    print("="*80)
    print(f"\nTotal Loans Processed: {len(loan_ids)}")
    print(f"Total Duration: {master_results['pipeline_run']['duration_seconds']:.2f} seconds")
    print(f"\nPer-Loan Results:")
    
    for loan in master_results["loans"]:
        print(f"\n  📋 Loan {loan['loan_id']} - {loan['borrower_name']}")
        
        if loan["income_analysis"]:
            ia = loan["income_analysis"]
            print(f"    💰 Income Analysis:")
            print(f"       Average: ${ia.get('average_income', 0):,.2f}")
            print(f"       Variance: {ia.get('variance_percentage', 0):.2f}%")
            print(f"       Consistency: {ia.get('consistency_rating', 'N/A')}")
        else:
            print(f"    ⚠️  Income Analysis: Failed")
        
        if loan["form_1003_tracker"]:
            ft = loan["form_1003_tracker"]
            versions = ft.get('total_versions_found', 0)
            print(f"    📄 Form 1003 Tracker:")
            print(f"       Versions Found: {versions}")
            if ft.get('summary'):
                initial = ft['summary'].get('initial_combined_income', 0)
                final = ft['summary'].get('final_combined_income', 0)
                print(f"       Initial Income: ${initial:,.2f}")
                print(f"       Final Income: ${final:,.2f}")
        else:
            print(f"    ⚠️  Form 1003 Tracker: Failed")
        
        if loan["processing_errors"]:
            print(f"    ❌ Errors: {', '.join(loan['processing_errors'])}")
    
    print("\n" + "="*80)
    print("✅ BATCH ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nMaster Results: {output_file}")
    print(f"Duration: {master_results['pipeline_run']['duration_seconds']:.2f} seconds")


if __name__ == "__main__":
    main()
