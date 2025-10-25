"""
Batch run form_1003_income_tracker on all loans in parallel.
"""

import subprocess
import sys
from pathlib import Path
import asyncio
import concurrent.futures

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

async def process_loan(loan_id: str, semaphore: asyncio.Semaphore) -> dict:
    """Process a single loan with rate limiting."""
    async with semaphore:
        print(f"\n🔄 Processing Loan {loan_id}")
        
        try:
            # Run the tracker as a subprocess
            process = await asyncio.create_subprocess_exec(
                ".venv/Scripts/python.exe", 
                "agents/form_1003_income_tracker.py", 
                loan_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=180
            )
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            stderr_text = stderr.decode('utf-8', errors='ignore')
            
            if process.returncode == 0:
                if "No Form 1003 documents found" in stdout_text:
                    print(f"  ⚠️ {loan_id}: No Form 1003 documents found")
                    return {'loan_id': loan_id, 'status': 'no_1003'}
                else:
                    print(f"  ✅ {loan_id}: Complete")
                    return {'loan_id': loan_id, 'status': 'success'}
            else:
                print(f"  ❌ {loan_id}: Failed")
                if stderr_text:
                    print(f"     Error: {stderr_text[:200]}")
                return {'loan_id': loan_id, 'status': 'failed', 'error': stderr_text[:200]}
        
        except asyncio.TimeoutError:
            print(f"  ⏱️ {loan_id}: Timed out")
            return {'loan_id': loan_id, 'status': 'timeout'}
        except Exception as e:
            print(f"  ❌ {loan_id}: Error - {str(e)[:100]}")
            return {'loan_id': loan_id, 'status': 'error', 'error': str(e)[:100]}

async def main():
    """Main batch processing function."""
    print("=" * 80)
    print("BATCH FORM 1003 INCOME TRACKER (ASYNC)")
    print("=" * 80)
    
    loan_ids = get_loan_ids()
    print(f"\nFound {len(loan_ids)} loans with semantic_json data")
    print(f"Running up to 5 loans in parallel...\n")
    
    # Semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(5)
    
    # Process all loans concurrently
    tasks = [process_loan(loan_id, semaphore) for loan_id in loan_ids]
    results_list = await asyncio.gather(*tasks)
    
    # Organize results
    results = {
        'successful': [],
        'no_1003': [],
        'failed': [],
        'timeout': [],
        'error': []
    }
    
    for result in results_list:
        status = result['status']
        loan_id = result['loan_id']
        
        if status == 'success':
            results['successful'].append(loan_id)
        elif status == 'no_1003':
            results['no_1003'].append(loan_id)
        elif status == 'timeout':
            results['timeout'].append(loan_id)
        elif status in ['failed', 'error']:
            results['failed'].append(loan_id)
    
    # Print summary
    print("\n" + "=" * 80)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 80)
    print(f"\nTotal Loans: {len(loan_ids)}")
    print(f"  ✅ Successful: {len(results['successful'])}")
    print(f"  ⚠️ No Form 1003: {len(results['no_1003'])}")
    print(f"  ⏱️ Timeout: {len(results['timeout'])}")
    print(f"  ❌ Failed: {len(results['failed'])}")
    
    if results['successful']:
        print(f"\nSuccessful Loans ({len(results['successful'])}):")
        for loan_id in results['successful']:
            print(f"  - {loan_id}")
    
    if results['no_1003']:
        print(f"\nNo Form 1003 Found ({len(results['no_1003'])}):")
        for loan_id in results['no_1003']:
            print(f"  - {loan_id}")
    
    if results['timeout']:
        print(f"\nTimed Out ({len(results['timeout'])}):")
        for loan_id in results['timeout']:
            print(f"  - {loan_id}")
    
    if results['failed']:
        print(f"\nFailed Loans ({len(results['failed'])}):")
        for loan_id in results['failed']:
            print(f"  - {loan_id}")
    
    print("\n" + "=" * 80)
    print("Run complete. Check loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.* for results.")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
