"""
Batch process Form 1003 timelines in parallel using asyncio.
Processes multiple loans concurrently for faster execution.

Usage:
    python batch_process_1003_timelines.py [--max-concurrent N]
    
Example:
    python batch_process_1003_timelines.py --max-concurrent 5
"""

import sys
import asyncio
import argparse
from pathlib import Path
import json
from datetime import datetime
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")


def identify_1003_files(loan_id: str) -> list:
    """Scan semantic_json folder and identify all Form 1003 files."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        return []
    
    form_1003_files = []
    
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            semantic_content = data.get('semantic_content', {})
            document_type = semantic_content.get('document_type', '').lower()
            
            is_1003 = 'form_1003' in document_type or '1003' in document_type
            
            if is_1003:
                metadata = data.get('metadata', {})
                upload_date = metadata.get('FileUploadDate', '')
                
                form_1003_files.append({
                    'file_path': json_file,
                    'file_name': json_file.name,
                    'metadata': metadata,
                    'upload_date': upload_date,
                    'full_data': data
                })
        except Exception:
            continue
    
    return form_1003_files


def sort_by_upload_date(form_1003_files: list) -> list:
    """Sort Form 1003 files by FileUploadDate."""
    return sorted(
        form_1003_files, 
        key=lambda x: x['upload_date'] if x['upload_date'] else '0000-00-00'
    )


async def extract_income_from_all_1003s(loan_id: str, sorted_1003_files: list) -> dict:
    """Extract income from all Form 1003 versions using LLM."""
    
    if not sorted_1003_files:
        return {}
    
    client = AsyncAzureOpenAI(
        api_key=subscription_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )
    
    files_context = []
    for idx, file_info in enumerate(sorted_1003_files, 1):
        files_context.append({
            'version': idx,
            'file_name': file_info['file_name'],
            'upload_date': file_info['upload_date'],
            'semantic_content': file_info['full_data'].get('semantic_content', {})
        })
    
    prompt = f"""You are analyzing Form 1003 (Uniform Residential Loan Application) documents for a mortgage loan.

**LOAN ID:** {loan_id}

I have provided {len(sorted_1003_files)} Form 1003 semantic JSON files, already sorted in chronological order by FileUploadDate.

**YOUR TASK:**

1. **FIRST**: Determine if the borrowers are CONSISTENT across all Form 1003 versions
   - Are the primary borrower and co-borrower the SAME PEOPLE in all versions?
   - Minor name variations are OK (e.g., "BOB MONCRIEF" vs "BOBBY L MONCRIEF" = SAME PERSON)
   - But if a co-borrower is ADDED or REMOVED, or replaced with a different person = INCONSISTENT

2. **SECOND**: For EACH Form 1003 version, extract the monthly income information

**WHAT TO EXTRACT:**

1. Primary Borrower's Monthly Income:
   - Employment income (base salary)
   - Overtime income
   - Bonus income
   - Commission income
   - Self-employment income
   - Retirement/pension income
   - Other income sources
   - **TOTAL monthly income**

2. Co-Borrower's Monthly Income (if present):
   - Same breakdown as above
   - **TOTAL monthly income**

3. **Combined Household Monthly Income**

**FORM 1003 FILES (in chronological order):**

{json.dumps(files_context, indent=2)}

**RESPONSE FORMAT:**

Return a JSON object with this exact structure:

{{
  "loan_id": "{loan_id}",
  "analysis_date": "CURRENT_ISO_TIMESTAMP",
  "total_versions_found": {len(sorted_1003_files)},
  "borrower_consistency": {{
    "is_consistent": true or false,
    "primary_borrower_name": "Normalized name from final version",
    "co_borrower_name": "Normalized name from final version or null",
    "explanation": "Brief explanation of why borrowers are consistent or inconsistent across versions"
  }},
  "income_by_version": [
    {{
      "version_number": 1,
      "file_name": "...",
      "upload_date": "2025-05-20T19:58:12",
      "primary_borrower": {{
        "name": "ANTHONY ROBERT ZIMBICKI",
        "employment_income_base": 9533.33,
        "employment_income_overtime": 0,
        "employment_income_bonus": 9086.00,
        "employment_income_commission": 0,
        "self_employment_income": 0,
        "retirement_income": 0,
        "other_income": 0,
        "total_monthly_income": 18619.33
      }},
      "co_borrower": {{
        "name": null,
        "total_monthly_income": 0
      }},
      "combined_monthly_income": 18619.33
    }}
  ],
  "income_changes": [
    {{
      "from_version": 1,
      "to_version": 2,
      "primary_borrower_change": 0,
      "co_borrower_change": 0,
      "combined_change": 0,
      "description": "No changes" or "Base salary increased from $X to $Y"
    }}
  ],
  "summary": {{
    "initial_combined_income": 18619.33,
    "final_combined_income": 18619.33,
    "net_change": 0,
    "number_of_versions": 3
  }}
}}

**IMPORTANT:**
- **BORROWER CONSISTENCY**: Determine if the same people are borrowing across all versions
  - Minor name spelling variations = SAME PERSON (consistent)
  - Adding/removing/replacing a borrower = DIFFERENT PEOPLE (inconsistent)
- Extract EXACT dollar amounts from the semantic content
- If a field is not present, use 0 or null appropriately
- Monthly income is the key metric - ensure all amounts are monthly (not annual)
- Compare versions and identify any changes in income amounts

Return ONLY valid JSON. No markdown, no explanations."""
    
    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage underwriter. You extract income data from Form 1003 loan applications with perfect accuracy."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=8000
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        raise Exception(f"LLM extraction failed: {e}")


def save_analysis(loan_id: str, analysis: dict):
    """Save the analysis to JSON file."""
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"form_1003_income_timeline.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    return output_file


async def process_single_loan(loan_id: str, semaphore: asyncio.Semaphore) -> dict:
    """Process a single loan with concurrency control."""
    async with semaphore:
        try:
            # Step 1: Identify Form 1003 files
            form_1003_files = identify_1003_files(loan_id)
            
            if not form_1003_files:
                return {
                    'loan_id': loan_id,
                    'status': 'skipped',
                    'reason': 'No Form 1003 files found'
                }
            
            # Step 2: Sort by upload date
            sorted_files = sort_by_upload_date(form_1003_files)
            
            # Step 3: Extract income
            analysis = await extract_income_from_all_1003s(loan_id, sorted_files)
            
            if not analysis:
                return {
                    'loan_id': loan_id,
                    'status': 'error',
                    'reason': 'Failed to extract income'
                }
            
            # Step 4: Save results
            save_analysis(loan_id, analysis)
            
            # Check borrower consistency
            borrower_consistency = analysis.get('borrower_consistency', {})
            is_consistent = borrower_consistency.get('is_consistent', False)
            
            return {
                'loan_id': loan_id,
                'status': 'success',
                'versions': analysis.get('total_versions_found', 0),
                'consistent': is_consistent
            }
            
        except Exception as e:
            return {
                'loan_id': loan_id,
                'status': 'error',
                'reason': str(e)
            }


async def batch_process_all_loans(max_concurrent: int = 5):
    """Process all loans in parallel with concurrency limit."""
    
    loan_docs_dir = Path("loan_docs")
    if not loan_docs_dir.exists():
        print("❌ loan_docs directory not found!")
        return
    
    loan_dirs = sorted([d for d in loan_docs_dir.iterdir() if d.is_dir()])
    loan_ids = [d.name for d in loan_dirs]
    
    print(f"\n{'='*80}")
    print(f"📋 BATCH PROCESSING FORM 1003 TIMELINES (PARALLEL)")
    print(f"{'='*80}")
    print(f"\nTotal Loans: {len(loan_ids)}")
    print(f"Max Concurrent: {max_concurrent}")
    print(f"Model: {deployment}\n")
    
    # Create semaphore to limit concurrent API calls
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Process all loans concurrently
    start_time = datetime.now()
    tasks = [process_single_loan(loan_id, semaphore) for loan_id in loan_ids]
    results = await asyncio.gather(*tasks)
    end_time = datetime.now()
    
    # Analyze results
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    consistent_count = sum(1 for r in results if r.get('consistent', False))
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"⏱️  Duration: {(end_time - start_time).total_seconds():.1f} seconds")
    print(f"✅ Success: {success_count}")
    print(f"⏭️  Skipped: {skipped_count} (no Form 1003 files)")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total: {len(loan_ids)}")
    print(f"\n✅ Consistent Borrowers: {consistent_count}/{success_count}")
    
    # Show errors if any
    if error_count > 0:
        print(f"\n{'─'*80}")
        print("ERRORS:")
        print(f"{'─'*80}")
        for result in results:
            if result['status'] == 'error':
                print(f"  ❌ {result['loan_id']}: {result.get('reason', 'Unknown error')}")
    
    # Show consistent/inconsistent breakdown
    print(f"\n{'─'*80}")
    print("BORROWER CONSISTENCY:")
    print(f"{'─'*80}")
    for result in results:
        if result['status'] == 'success':
            mark = "✅" if result.get('consistent', False) else "❌"
            print(f"  {mark} {result['loan_id']} ({result.get('versions', 0)} versions)")
    
    print()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Batch process Form 1003 timelines in parallel')
    parser.add_argument('--max-concurrent', type=int, default=5, 
                       help='Maximum number of concurrent API calls (default: 5)')
    
    args = parser.parse_args()
    
    await batch_process_all_loans(max_concurrent=args.max_concurrent)


if __name__ == "__main__":
    asyncio.run(main())
