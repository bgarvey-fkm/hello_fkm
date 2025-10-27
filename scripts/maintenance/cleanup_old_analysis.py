"""
Clean up old income analysis files
===================================
Removes all files from income_analysis directories EXCEPT form_1003_* files.

Keeps:
- form_1003_income_timeline.json
- form_1003_income_timeline.html

Removes:
- income_analysis*.json (old runs)
- income_scenario.json (old workflow)
- consistency_report*.html
- consistency_summary*.json
- income_comparison_analysis.json
- Any other non-form_1003 files

Usage:
    python cleanup_old_analysis.py
"""

from pathlib import Path

def cleanup_old_analysis():
    """Remove old income analysis files, keeping only form_1003_* files."""
    loan_docs_dir = Path("loan_docs")
    
    if not loan_docs_dir.exists():
        print("ERROR: loan_docs directory not found")
        return
    
    total_removed = 0
    loans_processed = 0
    
    for loan_dir in sorted(loan_docs_dir.iterdir()):
        if not loan_dir.is_dir():
            continue
            
        income_analysis_dir = loan_dir / "income_analysis"
        if not income_analysis_dir.exists():
            continue
        
        loans_processed += 1
        
        # Remove all files that don't start with "form_1003"
        for file in income_analysis_dir.glob("*"):
            if file.is_file() and not file.name.startswith("form_1003"):
                print(f"Removing {loan_dir.name}/{file.name}")
                file.unlink()
                total_removed += 1
    
    print(f"\n{'='*80}")
    print(f"CLEANUP COMPLETE")
    print(f"{'='*80}")
    print(f"Loans processed: {loans_processed}")
    print(f"Total files removed: {total_removed}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    cleanup_old_analysis()
