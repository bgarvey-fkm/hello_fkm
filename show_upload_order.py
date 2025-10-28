"""Show chronological upload order of income-relevant documents for a loan."""
import json
import sys
from pathlib import Path

loan_id = sys.argv[1] if len(sys.argv) > 1 else "1000178442"
semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")

relevant_docs = []

for json_file in semantic_dir.glob("*.json"):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        is_relevant = data.get('income_verification_relevant', {}).get('is_relevant')
        
        if is_relevant:
            metadata = data.get('metadata', {})
            semantic = data.get('semantic_content', {})
            
            relevant_docs.append({
                'file': json_file.name,
                'upload_date': metadata.get('FileUploadDate', 'N/A'),
                'doc_type': semantic.get('document_type', 'unknown'),
                'summary': semantic.get('summary', '')[:80]
            })
    except Exception as e:
        continue

# Sort by upload date
relevant_docs.sort(key=lambda x: x['upload_date'])

print(f"\n{'='*100}")
print(f"INCOME-RELEVANT DOCUMENTS FOR LOAN {loan_id} - CHRONOLOGICAL UPLOAD ORDER")
print(f"{'='*100}\n")

for i, doc in enumerate(relevant_docs, 1):
    print(f"{i}. {doc['upload_date']}")
    print(f"   Type: {doc['doc_type']}")
    print(f"   Summary: {doc['summary']}")
    print(f"   File: {doc['file']}")
    print()

print(f"Total: {len(relevant_docs)} income-relevant documents")
