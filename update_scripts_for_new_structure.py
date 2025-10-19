"""
Update all Python scripts to use the new loan ID-based folder structure
"""

import re
from pathlib import Path


def update_file_paths_in_script(file_path, loan_id="1000182277"):
    """Update file paths in a Python script to use new structure"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Path replacements
    replacements = [
        # Old path -> New path
        (r'loan_docs_json/', f'loan_docs/{loan_id}/json/'),
        (r'loan_docs_inputs/', f'loan_docs/{loan_id}/base64/'),
        (r'image_files/', f'loan_docs/{loan_id}/images/'),
        (r'"loan_summary/"', f'"reports/"'),
        (r"'loan_summary/'", f"'reports/'"),
        
        # Update report file names to include loan_id
        (r'turn1_independent_income_analysis\.md', f'{loan_id}_income_analysis.md'),
        (r'turn1_independent_debt_analysis\.md', f'{loan_id}_debt_analysis.md'),
        (r'dti_reconciliation_report\.html', f'{loan_id}_dti_reconciliation.html'),
    ]
    
    for old_pattern, new_pattern in replacements:
        content = re.sub(old_pattern, new_pattern, content)
    
    # If content changed, write it back
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    base_path = Path(__file__).parent
    loan_id = "1000182277"
    
    # List of scripts to update
    scripts = [
        "create_underwriting_summary.py",
        "income_verification_2turn.py",
        "debt_verification_2turn.py",
        "dti_reconciliation_agent.py",
        "process_loan_docs.py",
        "pdf_to_png_and_text.py",
    ]
    
    print(f"Updating scripts to use new folder structure for Loan ID: {loan_id}")
    print("="*70)
    
    updated_count = 0
    for script_name in scripts:
        script_path = base_path / script_name
        if script_path.exists():
            if update_file_paths_in_script(script_path, loan_id):
                print(f"✅ Updated: {script_name}")
                updated_count += 1
            else:
                print(f"⏭️  Skipped: {script_name} (no changes needed)")
        else:
            print(f"⚠️  Not found: {script_name}")
    
    print("="*70)
    print(f"Updated {updated_count} scripts\n")
    
    print("NEW PATH STRUCTURE:")
    print(f"  Source PDFs:  loan_docs/{loan_id}/source_pdfs/")
    print(f"  Images:       loan_docs/{loan_id}/images/")
    print(f"  Base64 files: loan_docs/{loan_id}/base64/")
    print(f"  JSON files:   loan_docs/{loan_id}/json/")
    print(f"  Reports:      reports/")
    print("\nREPORT NAMING:")
    print(f"  Income:  reports/{loan_id}_income_analysis.md")
    print(f"  Debt:    reports/{loan_id}_debt_analysis.md")
    print(f"  DTI:     reports/{loan_id}_dti_reconciliation.html")
    
    print("\n⚠️  NEXT STEPS:")
    print("1. Test each updated script")
    print("2. Verify reports are generated in reports/ folder")
    print("3. Once verified, you can delete old folders:")
    print("   - image_files/")
    print("   - loan_docs_inputs/")
    print("   - loan_docs_json/")
    print("   - loan_summary/")


if __name__ == "__main__":
    main()
