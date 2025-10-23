"""
Extract all Form 1003 instances and their income data from semantic JSON files.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def extract_1003_income(loan_id):
    """Extract Form 1003 instances and income data."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"Error: {semantic_dir} does not exist")
        return
    
    form_1003s = []
    
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            doc_type = doc.get('semantic_content', {}).get('document_type', '').lower()
            
            # Check if it's a Form 1003
            if '1003' in doc_type or 'form_1003' in doc_type or 'urla' in doc_type:
                # Extract income from the standard Form 1003 structure
                semantic = doc.get('semantic_content', {})
                income = None
                income_field = None
                
                # Try to get from section_1_borrower_info.current_employment.monthly_income.total
                section_1 = semantic.get('section_1_borrower_info', {})
                if section_1:
                    current_emp = section_1.get('current_employment', {})
                    if current_emp:
                        monthly_income = current_emp.get('monthly_income', {})
                        if monthly_income and isinstance(monthly_income, dict):
                            income = monthly_income.get('total')
                            if income:
                                income_field = 'section_1_borrower_info.current_employment.monthly_income.total'
                                # Get breakdown too
                                base = monthly_income.get('base', 0)
                                bonus = monthly_income.get('bonus', 0)
                                overtime = monthly_income.get('overtime', 0)
                                income_breakdown = f"Base: ${base:,.2f}, Bonus: ${bonus:,.2f}, OT: ${overtime:,.2f}"
                            else:
                                income_breakdown = None
                
                form_1003s.append({
                    'file_id': doc.get('metadata', {}).get('FileId'),
                    'file_name': doc.get('metadata', {}).get('FileName'),
                    'upload_date': doc.get('metadata', {}).get('FileUploadDate'),
                    'doc_type': doc_type,
                    'income': income,
                    'income_breakdown': income_breakdown if income else None,
                    'income_field': income_field,
                    'summary': semantic.get('summary', 'N/A')[:80] if semantic.get('summary') else 'N/A'
                })
                
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            continue
    
    # Sort by upload date
    form_1003s.sort(key=lambda x: x['upload_date'] if x['upload_date'] else '')
    
    # Display results
    print("\n" + "="*80)
    print(f"FORM 1003 INSTANCES - LOAN {loan_id}")
    print("="*80)
    print(f"\nTotal Form 1003 documents found: {len(form_1003s)}\n")
    
    for i, form in enumerate(form_1003s, 1):
        print(f"{i}. FileID: {form['file_id']}")
        print(f"   Upload Date: {form['upload_date']}")
        print(f"   Document Type: {form['doc_type']}")
        if form['income']:
            print(f"   Total Monthly Income: ${form['income']:,.2f}")
            if form['income_breakdown']:
                print(f"   Breakdown: {form['income_breakdown']}")
        else:
            print(f"   Income: NOT FOUND IN SEMANTIC CONTENT")
        print(f"   File: {form['file_name'][:70]}")
        print()
    
    return form_1003s


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_1003_income.py <loan_id>")
        print("Example: python extract_1003_income.py 1000175957")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    extract_1003_income(loan_id)
