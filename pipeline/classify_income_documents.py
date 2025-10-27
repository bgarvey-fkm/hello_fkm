# -*- coding: utf-8 -*-
"""
Income Document Classification Pipeline Step

Classifies which documents in semantic_json are relevant for income verification
based on Freddie Mac guidelines. This should run once per loan before income analysis.

Updates each semantic JSON file with an 'income_verification_relevant' flag.
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Load environment variables
load_dotenv()


def load_freddie_mac_guidelines():
    """
    Load the Freddie Mac income underwriting decision tree.
    
    Returns:
        String containing decision tree for income classification
    """
    guidelines_file = Path("guidelines/income_underwriting_decision_tree.json")
    
    if not guidelines_file.exists():
        return ""
    
    try:
        with open(guidelines_file, 'r', encoding='utf-8') as f:
            decision_tree = json.load(f)
        
        # Format the decision tree into a readable string
        rules_text = "FREDDIE MAC INCOME UNDERWRITING DECISION TREE:\n\n"
        rules_text += f"Title: {decision_tree.get('metadata', {}).get('title', 'Unknown')}\n"
        rules_text += f"Description: {decision_tree.get('metadata', {}).get('description', 'Unknown')}\n"
        rules_text += f"Usage: {decision_tree.get('metadata', {}).get('usage', 'Unknown')}\n\n"
        
        # Convert the structured decision tree to text format
        rules_text += json.dumps(decision_tree, indent=2)
        
        return rules_text
        
    except Exception as e:
        print(f"Warning: Could not load decision tree: {e}")
        return ""


async def classify_income_documents(loan_id, refilter=False):
    """
    Classify ALL semantic JSON files to determine which are relevant for income verification.
    
    Uses Freddie Mac guidelines to determine which documents are relevant.
    Updates each semantic JSON file with 'income_verification_relevant' flag.
    
    Args:
        loan_id: The loan identifier
        refilter: If True, ignore cached flags and re-run LLM filtering
        
    Returns:
        Dict with classification results summary
    """
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        raise FileNotFoundError(f"Semantic JSON directory does not exist: {semantic_dir}")
    
    # Load all documents first
    all_docs = []
    cached_results_available = True
    
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            doc_obj = {
                'file_path': str(json_file),
                'file_id': doc.get('metadata', {}).get('FileId'),
                'file_name': doc.get('metadata', {}).get('FileName'),
                'doc_type': doc.get('semantic_content', {}).get('document_type', 'unknown'),
                'metadata': doc.get('metadata', {}),
                'semantic_content': doc.get('semantic_content', {})
            }
            all_docs.append(doc_obj)
            
            # Check if this document has the cached flag
            if 'income_verification_relevant' not in doc:
                cached_results_available = False
                
        except Exception as e:
            continue
    
    # FAST PATH: Use cached results if available and refilter not requested
    if cached_results_available and not refilter:
        print(f"\n>> Using cached income verification flags (found {len(all_docs)} total documents)")
        income_docs_count = 0
        excluded_docs_count = 0
        
        for json_file in semantic_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
                
                # Check if marked as income verification relevant
                if doc.get('income_verification_relevant', {}).get('is_relevant', False):
                    income_docs_count += 1
                else:
                    excluded_docs_count += 1
                    
            except Exception as e:
                continue
        
        print(f">> [OK] {income_docs_count} documents marked as income-relevant")
        print(f">> [OK] {excluded_docs_count} documents marked as not income-relevant")
        
        return {
            'loan_id': loan_id,
            'total_documents': len(all_docs),
            'income_relevant': income_docs_count,
            'excluded': excluded_docs_count,
            'used_cache': True
        }
    
    # SLOW PATH: Run LLM filtering and cache results
    if refilter:
        print(f"\n>> Re-filtering requested - running LLM classification...")
    else:
        print(f"\n>> No cached results found - running initial LLM classification...")
    
    # Load Freddie Mac guidelines
    guidelines = load_freddie_mac_guidelines()
    if not guidelines:
        raise FileNotFoundError("Freddie Mac guidelines not found - cannot perform intelligent filtering")
    
    # Initialize Azure OpenAI client
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    print(f">> Found {len(all_docs)} total documents")
    print(f">> Filtering based on Freddie Mac income verification guidelines...")
    
    # Create a summary of each document for filtering
    doc_summaries = []
    for doc in all_docs:
        doc_summaries.append({
            'file_id': doc['file_id'],
            'file_name': doc['file_name'],
            'document_type': doc['doc_type'],
            'summary': doc['semantic_content'].get('summary', ''),
            'content_preview': str(doc['semantic_content'])[:500]
        })
    
    # Ask LLM to filter based on guidelines
    filter_prompt = f"""Based on the Freddie Mac income verification guidelines below, review the following list of documents and identify which ones are INCOME VERIFICATION DOCUMENTS (both primary sources AND verification/supporting documents).

{guidelines}

DOCUMENTS TO REVIEW:
{json.dumps(doc_summaries, indent=2)}

CRITICAL FILTERING CRITERIA:

READ THE SEMANTIC CONTENT of each document and determine if it falls into ANY of these categories:

1. PRIMARY INCOME SOURCE DOCUMENTS:
   - Original documents showing income paid/received: paystubs, W-2s, 1099s, tax returns (1040, 1120-S, 1065), Schedule K-1
   - Bank statements showing income deposits
   - Pension/retirement statements (DFAS, PERS, CalPERS, etc.)
   - SSA benefit letters (Social Security, SSDI)
   - VA award letters, VA rating decisions, VA benefit letters (showing disability compensation amounts)
   - Military retirement documents (DFAS retiree account statements)
   - Disability benefit statements (VA, private disability insurance)
   - These show actual income amounts

2. EMPLOYMENT & INCOME VERIFICATION DOCUMENTS:
   - VOE (Verification of Employment) - written or verbal
   - Offer letters showing salary/compensation
   - Employment contracts
   - Employer letters confirming income/employment
   - VA Certificate of Eligibility (when it shows benefit amounts or disability ratings)
   - These verify employment status and income details

3. WHO CREATED THE DOCUMENT?
   - INCLUDE: Documents from employers, IRS, SSA, VA, DFAS, pension administrators, banks, HR departments
   - INCLUDE: Employment verification responses (VOE, verbal VOE, offer letters)
   - INCLUDE: Government benefit documents (VA, SSA, military retirement)
   - EXCLUDE: Internal analysis documents created by underwriters/loan officers (worksheets, calculation tools, notes)

4. WHAT TO EXCLUDE:
   - Underwriter worksheets, income calculation spreadsheets
   - Loan officer notes or summaries
   - DTI calculations, pricing grids
   - Internal analysis documents (not from employer/IRS/third party)

**IMPORTANT**: Both PRIMARY SOURCES (paystubs, W-2s, tax returns) AND VERIFICATION DOCUMENTS (VOEs, offer letters) should be INCLUDED as income verification documents.

Based on the semantic content you see, classify each document.

Return a JSON object with this structure:
{{
  "income_verification_documents": [
    {{
      "file_id": <file_id>,
      "reason": "<why this is an income verification document (primary source OR verification document)>"
    }}
  ],
  "excluded_documents": [
    {{
      "file_id": <file_id>,
      "reason": "<why this is NOT an income verification document (e.g., internal worksheet)>"
    }}
  ]
}}"""

    try:
        response = await client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": "You are an expert mortgage underwriter who knows Freddie Mac income verification guidelines."},
                {"role": "user", "content": filter_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        filter_result = json.loads(response.choices[0].message.content)
        
        # Extract the file IDs that should be included and excluded
        included_file_ids = set(doc['file_id'] for doc in filter_result.get('income_verification_documents', []))
        excluded_file_ids = set(doc['file_id'] for doc in filter_result.get('excluded_documents', []))
        
        # Save the flags back to the semantic JSON files (cache for future runs)
        print(f"\n>> Caching classification results to semantic JSON files...")
        for doc in all_docs:
            try:
                json_path = Path(doc['file_path'])
                with open(json_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                # Add income verification flag
                if doc['file_id'] in included_file_ids:
                    reason = next((d['reason'] for d in filter_result['income_verification_documents'] 
                                 if d['file_id'] == doc['file_id']), 'Relevant for income verification')
                    doc_data['income_verification_relevant'] = {
                        'is_relevant': True,
                        'reason': reason,
                        'classified_date': str(Path(__file__).stat().st_mtime)
                    }
                elif doc['file_id'] in excluded_file_ids:
                    reason = next((d['reason'] for d in filter_result['excluded_documents'] 
                                 if d['file_id'] == doc['file_id']), 'Not relevant for income verification')
                    doc_data['income_verification_relevant'] = {
                        'is_relevant': False,
                        'reason': reason,
                        'classified_date': str(Path(__file__).stat().st_mtime)
                    }
                else:
                    # Document wasn't in either list (shouldn't happen, but handle it)
                    doc_data['income_verification_relevant'] = {
                        'is_relevant': False,
                        'reason': 'Not classified by LLM',
                        'classified_date': str(Path(__file__).stat().st_mtime)
                    }
                
                # Write back to file
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(doc_data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                print(f">> Warning: Could not update cache for {doc['file_name']}: {e}")
                continue
        
        print(f">> [OK] Cached {len(included_file_ids)} relevant + {len(excluded_file_ids)} excluded classifications")
        
        await client.close()
        
        return {
            'loan_id': loan_id,
            'total_documents': len(all_docs),
            'income_relevant': len(included_file_ids),
            'excluded': len(excluded_file_ids),
            'used_cache': False
        }
        
    except Exception as e:
        await client.close()
        raise RuntimeError(f"Document filtering failed: {e}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python classify_income_documents.py <loan_id> [--refilter]")
        print("Example: python classify_income_documents.py 1000179167")
        print("         python classify_income_documents.py 1000179167 --refilter")
        print("\nOptions:")
        print("  --refilter    Force re-classification of documents (ignore cache)")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    refilter = '--refilter' in sys.argv
    
    print("\n" + "="*80)
    print(f"INCOME DOCUMENT CLASSIFICATION")
    print(f"Loan ID: {loan_id}")
    if refilter:
        print("Mode: RE-FILTER (ignoring cached classifications)")
    else:
        print("Mode: USE CACHE (if available)")
    print("="*80)
    
    # Run classification
    result = asyncio.run(classify_income_documents(loan_id, refilter))
    
    print("\n" + "="*80)
    print("CLASSIFICATION COMPLETE")
    print("="*80)
    print(f"Total documents: {result['total_documents']}")
    print(f"Income-relevant: {result['income_relevant']}")
    print(f"Excluded: {result['excluded']}")
    print(f"Used cache: {result['used_cache']}")
    print("\n>> Income document classification complete!")
    print(f">> All semantic JSON files updated with 'income_verification_relevant' flags")


if __name__ == "__main__":
    main()
