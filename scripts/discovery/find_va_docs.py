"""
Find VA Disability Documents

Searches semantic JSON files for VA disability/compensation documentation.

Usage:
    python find_va_docs.py <loan_id>
"""

import os
import sys
import json
from pathlib import Path


def find_va_documents(loan_id):
    """
    Search for VA disability/compensation documents in semantic JSON files.
    
    Args:
        loan_id: The loan identifier
    """
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"Error: Directory not found: {semantic_dir}")
        return
    
    print(f"\n{'='*80}")
    print(f"SEARCHING FOR VA DISABILITY DOCUMENTS")
    print(f"Loan ID: {loan_id}")
    print(f"{'='*80}\n")
    
    # VA-related keywords to search for
    va_keywords = [
        'va compensation',
        'va disability',
        'veterans affairs',
        'department of veterans',
        'va benefit',
        'disability compensation',
        'service-connected',
        'va award letter',
        'va rating',
        'compensation and pension',
        'va c&p',
        'va payment'
    ]
    
    json_files = list(semantic_dir.glob("*.json"))
    print(f"Searching {len(json_files)} semantic JSON files...\n")
    
    matches = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
            
            # Convert to lowercase for case-insensitive search
            content_lower = content.lower()
            
            # Check if any VA keywords are in the content
            found_keywords = [kw for kw in va_keywords if kw in content_lower]
            
            if found_keywords:
                semantic = data.get('semantic_content', {})
                metadata = data.get('metadata', {})
                classification = data.get('income_verification_relevant', {})
                
                matches.append({
                    'file': json_file.name,
                    'file_id': metadata.get('FileId'),
                    'doc_type': semantic.get('document_type', 'unknown'),
                    'summary': semantic.get('summary', 'No summary'),
                    'keywords_found': found_keywords,
                    'is_relevant': classification.get('is_relevant', False),
                    'classification_reason': classification.get('reason', 'Not classified'),
                    'semantic_content': semantic
                })
        
        except Exception as e:
            continue
    
    if not matches:
        print("❌ No VA-related documents found.\n")
        print("This could mean:")
        print("  - VA disability documentation was not uploaded")
        print("  - Documents are named/described differently")
        print("  - VA income is embedded in other documents (like bank statements)")
        return
    
    print(f"✅ Found {len(matches)} file(s) with VA-related content:\n")
    print("="*80)
    
    for i, match in enumerate(matches, 1):
        print(f"\n📄 Match {i}: {match['file']}")
        print(f"   File ID: {match['file_id']}")
        print(f"   Document Type: {match['doc_type']}")
        print(f"   Summary: {match['summary'][:150]}...")
        print(f"   Keywords Found: {', '.join(match['keywords_found'])}")
        print(f"   Income Relevant: {'✅ YES' if match['is_relevant'] else '❌ NO'}")
        if not match['is_relevant']:
            print(f"   Exclusion Reason: {match['classification_reason'][:150]}")
        
        # Look for specific income amounts in the content
        semantic = match['semantic_content']
        
        # Check for amount fields
        amount_fields = {}
        for key, value in semantic.items():
            if any(amt_word in key.lower() for amt_word in ['amount', 'payment', 'compensation', 'benefit', 'gross', 'net']):
                if value and not isinstance(value, (dict, list)):
                    amount_fields[key] = value
        
        if amount_fields:
            print(f"   Amounts Found:")
            for key, val in amount_fields.items():
                print(f"     - {key}: {val}")
        
        print()
    
    print("="*80)
    print("\nRECOMMENDATIONS:")
    
    excluded = [m for m in matches if not m['is_relevant']]
    if excluded:
        print(f"\n⚠️  {len(excluded)} VA document(s) were EXCLUDED from income analysis:")
        for match in excluded:
            print(f"   - {match['file']}")
            print(f"     Reason: {match['classification_reason'][:100]}")
        
        print("\nTo include these in income analysis:")
        print("1. Review the classification reasons above")
        print("2. If they should be included, update the classification criteria")
        print("3. Re-run: python pipeline/classify_income_documents.py {loan_id} --refilter")
    
    included = [m for m in matches if m['is_relevant']]
    if included:
        print(f"\n✅ {len(included)} VA document(s) are INCLUDED in income analysis")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_va_docs.py <loan_id>")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    find_va_documents(loan_id)
