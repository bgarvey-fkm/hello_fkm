"""
Analyze borrower consistency across all Form 1003 timelines.
Shows how many loans have consistent vs inconsistent borrowers,
and how many have income changes between initial and final Form 1003.
"""

import json
from pathlib import Path

def analyze_all_loans():
    """Analyze borrower consistency and income changes for all loans."""
    
    loan_docs_dir = Path("loan_docs")
    
    stats = {
        'total_loans': 0,
        'has_timeline': 0,
        'consistent_borrowers': 0,
        'inconsistent_borrowers': 0,
        'income_changed': 0,
        'income_same': 0,
        'inconsistent_loans': [],
        'income_change_loans': []
    }
    
    loan_dirs = sorted([d for d in loan_docs_dir.iterdir() if d.is_dir()])
    
    print(f"\n{'='*80}")
    print(f"BORROWER CONSISTENCY & INCOME CHANGE ANALYSIS")
    print(f"{'='*80}\n")
    
    for loan_dir in loan_dirs:
        loan_id = loan_dir.name
        stats['total_loans'] += 1
        
        timeline_file = loan_dir / "income_analysis" / "form_1003_income_timeline.json"
        
        if not timeline_file.exists():
            continue
        
        stats['has_timeline'] += 1
        
        try:
            with open(timeline_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check borrower consistency
            borrower_consistency = data.get('borrower_consistency', {})
            is_consistent = borrower_consistency.get('is_consistent')
            
            if is_consistent is None:
                # Old format without borrower_consistency
                continue
            
            if is_consistent:
                stats['consistent_borrowers'] += 1
            else:
                stats['inconsistent_borrowers'] += 1
                stats['inconsistent_loans'].append({
                    'loan_id': loan_id,
                    'explanation': borrower_consistency.get('explanation', 'N/A')
                })
            
            # Check income changes
            summary = data.get('summary', {})
            initial_income = summary.get('initial_combined_income', 0)
            final_income = summary.get('final_combined_income', 0)
            
            if initial_income != final_income:
                stats['income_changed'] += 1
                change_pct = ((final_income - initial_income) / initial_income * 100) if initial_income > 0 else 0
                stats['income_change_loans'].append({
                    'loan_id': loan_id,
                    'initial': initial_income,
                    'final': final_income,
                    'change_pct': change_pct,
                    'is_consistent': is_consistent
                })
            else:
                stats['income_same'] += 1
        
        except Exception as e:
            print(f"  [ERROR] {loan_id}: {e}")
            continue
    
    # Print summary
    print(f"Total Loans: {stats['total_loans']}")
    print(f"Loans with Form 1003 Timeline: {stats['has_timeline']}")
    print(f"Loans with Borrower Consistency Data: {stats['consistent_borrowers'] + stats['inconsistent_borrowers']}")
    
    print(f"\n{'─'*80}")
    print("BORROWER CONSISTENCY")
    print(f"{'─'*80}\n")
    
    total_analyzed = stats['consistent_borrowers'] + stats['inconsistent_borrowers']
    if total_analyzed > 0:
        print(f"✅ Consistent Borrowers: {stats['consistent_borrowers']} ({stats['consistent_borrowers']/total_analyzed*100:.1f}%)")
        print(f"❌ Inconsistent Borrowers: {stats['inconsistent_borrowers']} ({stats['inconsistent_borrowers']/total_analyzed*100:.1f}%)")
    
    if stats['inconsistent_loans']:
        print(f"\nLoans with INCONSISTENT borrowers:")
        for loan in stats['inconsistent_loans']:
            print(f"  • {loan['loan_id']}: {loan['explanation']}")
    
    print(f"\n{'─'*80}")
    print("INCOME CHANGES (Initial vs Final Form 1003)")
    print(f"{'─'*80}\n")
    
    total_income_analyzed = stats['income_changed'] + stats['income_same']
    if total_income_analyzed > 0:
        print(f"📊 Income Changed: {stats['income_changed']} ({stats['income_changed']/total_income_analyzed*100:.1f}%)")
        print(f"📊 Income Same: {stats['income_same']} ({stats['income_same']/total_income_analyzed*100:.1f}%)")
    
    if stats['income_change_loans']:
        print(f"\nLoans with INCOME CHANGES (sorted by change %):")
        sorted_changes = sorted(stats['income_change_loans'], key=lambda x: abs(x['change_pct']), reverse=True)
        for loan in sorted_changes[:20]:  # Top 20
            consistent_mark = "✅" if loan['is_consistent'] else "❌"
            print(f"  {consistent_mark} {loan['loan_id']}: ${loan['initial']:,.2f} → ${loan['final']:,.2f} ({loan['change_pct']:+.1f}%)")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"For histogram accuracy analysis, recommend using:")
    print(f"  • ONLY loans with consistent borrowers: {stats['consistent_borrowers']} loans")
    print(f"  • Filter out inconsistent borrowers: excludes {stats['inconsistent_borrowers']} loans")
    
    print()

if __name__ == "__main__":
    analyze_all_loans()
