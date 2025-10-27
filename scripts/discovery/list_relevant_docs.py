import os
import json
import sys

# Get loan_id from command line or use default
loan_id = sys.argv[1] if len(sys.argv) > 1 else "1000177371"
semantic_dir = f"loan_docs/{loan_id}/semantic_json"

files = [f for f in os.listdir(semantic_dir) if f.endswith('.json')]
print(f"DEBUG: Found {len(files)} total JSON files")
relevant = []

for f in files:
    with open(os.path.join(semantic_dir, f), 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            semantic = data.get('semantic_content', {})
            # income_verification_relevant is at the ROOT level, not inside semantic_content
            classification = data.get('income_verification_relevant', {})
            is_relevant = classification.get('is_relevant')
            if is_relevant == True:
                print(f"DEBUG: Found relevant doc: {f}")
                relevant.append({
                    'file': f,
                    'type': semantic.get('document_type'),
                    'date': semantic.get('document_date'),
                    'reason': classification.get('reason', ''),
                    'data': semantic
                })
        except Exception as e:
            print(f"ERROR reading {f}: {e}")

print(f"\n{'='*80}")
print(f"INCOME-RELEVANT DOCUMENTS FOR LOAN {loan_id}")
print(f"{'='*80}\n")
print(f"Found {len(relevant)} income-relevant documents:\n")

for doc in sorted(relevant, key=lambda x: x['date'] or ''):
    print(f"📄 {doc['file']}")
    print(f"   Type: {doc['type']}")
    print(f"   Date: {doc['date']}")
    print(f"   Reason: {doc['reason']}")
    
    # Extract key information
    data = doc['data']
    
    # Look for employer info
    if 'employer' in str(data).lower():
        for key, value in data.items():
            if 'employer' in key.lower() and value:
                print(f"   {key}: {value}")
    
    # Look for income amounts
    if 'income' in str(data).lower() or 'salary' in str(data).lower() or 'wage' in str(data).lower():
        for key, value in data.items():
            if any(term in key.lower() for term in ['income', 'salary', 'wage', 'gross', 'pay']):
                if value and not isinstance(value, dict) and not isinstance(value, list):
                    print(f"   {key}: {value}")
    
    print()

print(f"\n{'='*80}")
print("DETAILED ANALYSIS")
print(f"{'='*80}\n")

# Analyze the documents
employers = set()
dates = []
doc_types = {}

for doc in relevant:
    data = doc['data']
    doc_type = doc['type']
    
    if doc_type not in doc_types:
        doc_types[doc_type] = 0
    doc_types[doc_type] += 1
    
    if doc['date']:
        dates.append(doc['date'])
    
    # Extract employer names from content
    content = json.dumps(data).lower()
    if 'care' in content and 'iv' in content:
        employers.add('Care IV / Care4 (variations)')

print(f"Document Types:")
for dt, count in doc_types.items():
    print(f"  - {dt}: {count}")

if dates:
    print(f"\nDate Range:")
    print(f"  Earliest: {min(dates)}")
    print(f"  Latest: {max(dates)}")

if employers:
    print(f"\nEmployers Mentioned:")
    for emp in employers:
        print(f"  - {emp}")
