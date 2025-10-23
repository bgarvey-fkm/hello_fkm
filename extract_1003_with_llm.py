"""
Extract Form 1003 income data using LLM to read the full semantic JSON.
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()


async def extract_1003_income_with_llm(loan_id):
    """Extract Form 1003 instances and use LLM to find income data."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"Error: {semantic_dir} does not exist")
        return
    
    # Find all Form 1003 documents
    form_1003_files = []
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            doc_type = doc.get('semantic_content', {}).get('document_type', '').lower()
            
            if '1003' in doc_type or 'form_1003' in doc_type or 'urla' in doc_type:
                form_1003_files.append({
                    'file_path': json_file,
                    'file_id': doc.get('metadata', {}).get('FileId'),
                    'file_name': doc.get('metadata', {}).get('FileName'),
                    'upload_date': doc.get('metadata', {}).get('FileUploadDate'),
                    'full_doc': doc
                })
        except Exception as e:
            continue
    
    # Sort by upload date
    form_1003_files.sort(key=lambda x: x['upload_date'] if x['upload_date'] else '')
    
    print("\n" + "="*80)
    print(f"FORM 1003 INCOME EXTRACTION - LOAN {loan_id}")
    print("="*80)
    print(f"\nTotal Form 1003 documents found: {len(form_1003_files)}\n")
    
    # Initialize Azure OpenAI client
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Process each Form 1003
    for i, form in enumerate(form_1003_files, 1):
        print(f"{i}. FileID: {form['file_id']}")
        print(f"   Upload Date: {form['upload_date']}")
        print(f"   File: {form['file_name'][:70]}")
        
        # Ask LLM to extract income from the full document
        prompt = f"""Review this Form 1003 (Uniform Residential Loan Application) semantic JSON and extract the borrower's monthly income information.

FORM 1003 SEMANTIC JSON:
{json.dumps(form['full_doc'], indent=2)}

Please analyze the document and provide:
1. The total monthly income reported by the borrower
2. A breakdown of income components (base salary, bonus, overtime, commission, other)
3. The borrower's employer name and employment start date
4. Any other income sources reported

Return a JSON object with this structure:
{{
  "found_income": true/false,
  "total_monthly_income": <number or null>,
  "income_breakdown": {{
    "base_salary": <number or null>,
    "bonus": <number or null>,
    "overtime": <number or null>,
    "commission": <number or null>,
    "other": <number or null>
  }},
  "employer_info": {{
    "name": "<employer name or null>",
    "start_date": "<employment start date or null>",
    "position": "<job title or null>"
  }},
  "other_income_sources": [<list of other income sources if any>],
  "notes": "<any relevant notes about the income information>"
}}"""

        try:
            response = await client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                messages=[
                    {"role": "system", "content": "You are an expert at extracting data from Form 1003 loan applications."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if result.get('found_income'):
                print(f"   ✓ INCOME FOUND")
                print(f"   Total Monthly Income: ${result['total_monthly_income']:,.2f}")
                
                breakdown = result.get('income_breakdown', {})
                if any(breakdown.values()):
                    print(f"   Breakdown:")
                    if breakdown.get('base_salary'):
                        print(f"     - Base Salary: ${breakdown['base_salary']:,.2f}")
                    if breakdown.get('bonus'):
                        print(f"     - Bonus: ${breakdown['bonus']:,.2f}")
                    if breakdown.get('overtime'):
                        print(f"     - Overtime: ${breakdown['overtime']:,.2f}")
                    if breakdown.get('commission'):
                        print(f"     - Commission: ${breakdown['commission']:,.2f}")
                    if breakdown.get('other'):
                        print(f"     - Other: ${breakdown['other']:,.2f}")
                
                employer = result.get('employer_info', {})
                if employer.get('name'):
                    print(f"   Employer: {employer['name']}")
                    if employer.get('position'):
                        print(f"   Position: {employer['position']}")
                    if employer.get('start_date'):
                        print(f"   Employment Start: {employer['start_date']}")
                
                if result.get('other_income_sources'):
                    print(f"   Other Income Sources: {len(result['other_income_sources'])}")
                    for source in result['other_income_sources']:
                        print(f"     - {source}")
                
                if result.get('notes'):
                    print(f"   Notes: {result['notes']}")
            else:
                print(f"   ✗ NO INCOME FOUND")
                if result.get('notes'):
                    print(f"   Notes: {result['notes']}")
            
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
        
        print()
    
    await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_1003_with_llm.py <loan_id>")
        print("Example: python extract_1003_with_llm.py 1000176265")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    asyncio.run(extract_1003_income_with_llm(loan_id))
