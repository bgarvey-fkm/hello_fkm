"""
Generate CSV comparing AI Authoritative Income vs Form 1003 Final Income
For histogram analysis of accuracy.
"""

import json
import csv
from pathlib import Path


def generate_comparison_csv():
    """Generate CSV with authoritative income comparison."""
    
    # Find all loans with both files
    base_dir = Path("loan_docs")
    results = []
    
    for loan_dir in base_dir.iterdir():
        if not loan_dir.is_dir():
            continue
        
        loan_id = loan_dir.name
        summary_file = loan_dir / "income_analysis" / "consistency_summary_all.json"
        form1003_file = loan_dir / "income_analysis" / "form_1003_income_timeline.json"
        
        # Check if both files exist
        if not (summary_file.exists() and form1003_file.exists()):
            continue
        
        # Load files
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        with open(form1003_file, 'r', encoding='utf-8') as f:
            form1003 = json.load(f)
        
        # Extract values
        ai_auth = summary.get('underwriter_decision', {}).get('authoritative_income', 0)
        ai_simple = summary.get('underwriter_decision', {}).get('simple_average', 0)
        ai_high_conf = summary.get('underwriter_decision', {}).get('high_confidence_only_avg', 0)
        confidence_in_result = summary.get('underwriter_decision', {}).get('confidence_in_result', 'unknown')
        confidence_dist = summary.get('underwriter_decision', {}).get('confidence_distribution', {})
        variance_pct = summary.get('statistics', {}).get('variance_percentage', 0)
        total_runs = summary.get('total_runs', 0)
        
        form1003_final = form1003.get('summary', {}).get('final_combined_income', 0)
        
        # Calculate differences
        auth_diff = ai_auth - form1003_final
        auth_diff_pct = (auth_diff / form1003_final * 100) if form1003_final > 0 else 0
        
        simple_diff = ai_simple - form1003_final
        simple_diff_pct = (simple_diff / form1003_final * 100) if form1003_final > 0 else 0
        
        high_conf_diff = ai_high_conf - form1003_final
        high_conf_diff_pct = (high_conf_diff / form1003_final * 100) if form1003_final > 0 else 0
        
        # Determine best metric
        abs_diffs = {
            'authoritative': abs(auth_diff_pct),
            'simple_average': abs(simple_diff_pct),
            'high_confidence': abs(high_conf_diff_pct)
        }
        best_metric = min(abs_diffs, key=abs_diffs.get)
        
        results.append({
            'loan_id': loan_id,
            'total_runs': total_runs,
            'high_conf_runs': confidence_dist.get('high', 0),
            'medium_conf_runs': confidence_dist.get('medium', 0),
            'low_conf_runs': confidence_dist.get('low', 0),
            'confidence_in_result': confidence_in_result,
            'variance_pct': round(variance_pct, 2),
            'ai_authoritative': round(ai_auth, 2),
            'ai_simple_average': round(ai_simple, 2),
            'ai_high_confidence_only': round(ai_high_conf, 2),
            'form_1003_final': round(form1003_final, 2),
            'auth_diff': round(auth_diff, 2),
            'auth_diff_pct': round(auth_diff_pct, 2),
            'simple_diff': round(simple_diff, 2),
            'simple_diff_pct': round(simple_diff_pct, 2),
            'high_conf_diff': round(high_conf_diff, 2),
            'high_conf_diff_pct': round(high_conf_diff_pct, 2),
            'best_metric': best_metric
        })
    
    # Sort by loan_id
    results.sort(key=lambda x: x['loan_id'])
    
    # Write to CSV
    output_file = Path("aggregate_data") / "authoritative_income_comparison.csv"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    print(f"\n[OK] Generated: {output_file}")
    print(f"Total loans: {len(results)}")
    
    # Print summary statistics
    if results:
        auth_diffs = [r['auth_diff_pct'] for r in results]
        avg_diff = sum(auth_diffs) / len(auth_diffs)
        abs_diffs = [abs(d) for d in auth_diffs]
        avg_abs_diff = sum(abs_diffs) / len(abs_diffs)
        
        within_5pct = sum(1 for d in abs_diffs if d <= 5)
        within_10pct = sum(1 for d in abs_diffs if d <= 10)
        
        print(f"\nAuthoritative Income vs Form 1003:")
        print(f"  Average difference: {avg_diff:+.2f}%")
        print(f"  Average absolute difference: {avg_abs_diff:.2f}%")
        print(f"  Within 5%: {within_5pct}/{len(results)} ({within_5pct/len(results)*100:.1f}%)")
        print(f"  Within 10%: {within_10pct}/{len(results)} ({within_10pct/len(results)*100:.1f}%)")
        
        # Count best metrics
        best_counts = {}
        for r in results:
            metric = r['best_metric']
            best_counts[metric] = best_counts.get(metric, 0) + 1
        
        print(f"\nBest Metric Distribution:")
        for metric, count in sorted(best_counts.items()):
            print(f"  {metric}: {count}/{len(results)} ({count/len(results)*100:.1f}%)")
    
    return output_file


if __name__ == "__main__":
    generate_comparison_csv()
