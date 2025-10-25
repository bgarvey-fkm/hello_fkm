"""
Retry the 8 loans that failed in the batch test.
"""

import subprocess
import sys

# The 8 loans that failed
failed_loans = [
    '1000177101',
    '1000177613',
    '1000177906',
    '1000178300',
    '1000178414',
    '1000178442',
    '1000178549',
    '1000178579'
]

print("=" * 80)
print(f"RETRYING {len(failed_loans)} FAILED LOANS")
print("=" * 80)

num_runs = 10
if len(sys.argv) > 1:
    try:
        num_runs = int(sys.argv[1])
    except:
        pass

results = {'successful': [], 'failed': []}

for i, loan_id in enumerate(failed_loans, 1):
    print(f"\n[{i}/{len(failed_loans)}] Processing Loan {loan_id}")
    print("-" * 80)
    
    # Run scenario classifier
    try:
        result = subprocess.run(
            [".venv/Scripts/python.exe", "agents/income_scenario_classifier.py", loan_id],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f"  ✓ Scenario classified")
        else:
            print(f"  ✗ Scenario failed")
            results['failed'].append(loan_id)
            continue
    except Exception as e:
        print(f"  ✗ Scenario failed: {e}")
        results['failed'].append(loan_id)
        continue
    
    # Run income analysis
    try:
        result = subprocess.run(
            [".venv/Scripts/python.exe", "agents/income_analysis_agent.py", loan_id, str(num_runs)],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0 or "CONSISTENCY SUMMARY" in result.stdout:
            print(f"  ✓ Income analysis complete ({num_runs} runs)")
            results['successful'].append(loan_id)
        else:
            print(f"  ✗ Income analysis failed")
            results['failed'].append(loan_id)
    except Exception as e:
        print(f"  ✗ Income analysis failed: {e}")
        results['failed'].append(loan_id)

print("\n" + "=" * 80)
print("RETRY SUMMARY")
print("=" * 80)
print(f"Total: {len(failed_loans)}")
print(f"  ✓ Successful: {len(results['successful'])}")
print(f"  ✗ Failed: {len(results['failed'])}")

if results['successful']:
    print(f"\nSuccessful:")
    for loan_id in results['successful']:
        print(f"  - {loan_id}")

if results['failed']:
    print(f"\nStill Failed:")
    for loan_id in results['failed']:
        print(f"  - {loan_id}")
