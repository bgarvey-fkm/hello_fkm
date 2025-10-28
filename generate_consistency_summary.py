"""
Generate Consistency Summary
Reads all income_analysis_run*.json files and generates consistency_summary_all.json
with statistics and underwriter decision metrics.

This is a pure calculation script - no LLM calls.
Can be run standalone to regenerate summaries from existing run files.
"""

import json
import sys
from pathlib import Path


def generate_consistency_summary(loan_id: str) -> dict:
    """
    Generate comprehensive consistency summary from all run files.
    
    Args:
        loan_id: The loan identifier
        
    Returns:
        dict: The consistency summary data
    """
    
    summary_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    
    if not summary_dir.exists():
        raise FileNotFoundError(f"Income analysis directory not found: {summary_dir}")
    
    # Find all run files
    all_run_files = sorted(summary_dir.glob("income_analysis_run*.json"), 
                           key=lambda x: int(x.stem.replace("income_analysis_run", "")))
    
    if not all_run_files:
        raise FileNotFoundError(f"No income_analysis_run*.json files found in {summary_dir}")
    
    print(f"\n{'='*80}")
    print(f"Generating Consistency Summary for Loan {loan_id}")
    print(f"{'='*80}")
    print(f"Found {len(all_run_files)} run files")
    
    # Load all results
    all_results = []
    for run_file in all_run_files:
        with open(run_file, 'r', encoding='utf-8') as f:
            all_results.append(json.load(f))
    
    # Extract income values
    all_incomes = [r.get('monthly_gross_income', 0) for r in all_results if 'error' not in r]
    
    if not all_incomes:
        raise ValueError(f"No valid income results found in run files")
    
    # Calculate basic statistics
    all_avg_income = sum(all_incomes) / len(all_incomes)
    all_min_income = min(all_incomes)
    all_max_income = max(all_incomes)
    all_variance = all_max_income - all_min_income
    all_variance_pct = (all_variance / all_avg_income * 100) if all_avg_income > 0 else 0
    
    all_min_idx = all_incomes.index(all_min_income)
    all_max_idx = all_incomes.index(all_max_income)
    
    # Calculate confidence-weighted metrics
    confidence_weights = {'high': 1.0, 'medium': 0.7, 'low': 0.4}
    
    weighted_sum = 0
    weight_total = 0
    high_conf_incomes = []
    confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
    
    for result in all_results:
        if 'error' not in result:
            income = result.get('monthly_gross_income', 0)
            confidence = result.get('confidence_level', 'medium').lower()
            
            # Track confidence distribution
            if confidence in confidence_counts:
                confidence_counts[confidence] += 1
            
            # Calculate weighted sum
            weight = confidence_weights.get(confidence, 0.7)
            weighted_sum += income * weight
            weight_total += weight
            
            # Collect high-confidence incomes
            if confidence == 'high':
                high_conf_incomes.append(income)
    
    # Calculate confidence-weighted average
    confidence_weighted_avg = weighted_sum / weight_total if weight_total > 0 else all_avg_income
    
    # Calculate high-confidence-only average
    high_confidence_avg = sum(high_conf_incomes) / len(high_conf_incomes) if high_conf_incomes else all_avg_income
    
    # Determine overall confidence in result
    high_pct = (confidence_counts['high'] / len(all_results) * 100) if all_results else 0
    if high_pct >= 80:
        confidence_in_result = "high"
        rationale = f"{confidence_counts['high']}/{len(all_results)} runs achieved high confidence with {all_variance_pct:.2f}% variance"
        recommendation = "USE authoritative_income value - high confidence with strong consistency" if all_variance_pct < 1 else "USE authoritative_income value - high confidence but review variance"
    elif high_pct >= 50:
        confidence_in_result = "medium"
        rationale = f"{confidence_counts['high']}/{len(all_results)} runs achieved high confidence; {confidence_counts['medium']} medium, {confidence_counts['low']} low"
        recommendation = "REVIEW authoritative_income value - moderate confidence, consider manual verification"
    else:
        confidence_in_result = "low"
        rationale = f"Only {confidence_counts['high']}/{len(all_results)} runs achieved high confidence; variance {all_variance_pct:.2f}%"
        recommendation = "MANUAL REVIEW REQUIRED - low confidence across runs or high variance detected"
    
    # Get document info from first result
    documents_analyzed = all_results[0].get('documents_analyzed', 0)
    
    # Try to load income documents list from existing summary or reconstruct from results
    income_documents = []
    existing_summary_file = summary_dir / "consistency_summary_all.json"
    if existing_summary_file.exists():
        try:
            with open(existing_summary_file, 'r', encoding='utf-8') as f:
                existing_summary = json.load(f)
                income_documents = existing_summary.get('income_documents', [])
        except:
            pass
    
    # Build comprehensive summary
    all_summary = {
        'loan_id': loan_id,
        'total_runs': len(all_results),
        'run_range': f"1-{len(all_results)}",
        'documents_analyzed': documents_analyzed,
        'income_documents': income_documents,
        'results': all_results,
        'statistics': {
            'average_income': all_avg_income,
            'min_income': all_min_income,
            'max_income': all_max_income,
            'variance': all_variance,
            'variance_percentage': all_variance_pct,
            'min_run_number': all_min_idx + 1,
            'max_run_number': all_max_idx + 1
        },
        'underwriter_decision': {
            'authoritative_income': round(confidence_weighted_avg, 2),
            'confidence_weighted_avg': round(confidence_weighted_avg, 2),
            'high_confidence_only_avg': round(high_confidence_avg, 2),
            'simple_average': round(all_avg_income, 2),
            'confidence_distribution': confidence_counts,
            'confidence_in_result': confidence_in_result,
            'rationale': rationale,
            'recommendation': recommendation
        }
    }
    
    # Save comprehensive summary
    all_summary_file = summary_dir / "consistency_summary_all.json"
    with open(all_summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_summary, f, indent=2)
    
    print(f"\n[OK] Saved: {all_summary_file}")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"CONSISTENCY SUMMARY")
    print(f"{'='*80}")
    print(f"Total Runs: {len(all_results)}")
    print(f"Confidence Distribution: {confidence_counts['high']} high, {confidence_counts['medium']} medium, {confidence_counts['low']} low")
    print(f"\nStatistics:")
    print(f"  Average Income: ${all_avg_income:,.2f}")
    print(f"  Min Income: ${all_min_income:,.2f}")
    print(f"  Max Income: ${all_max_income:,.2f}")
    print(f"  Variance: ${all_variance:,.2f} ({all_variance_pct:.2f}%)")
    
    print(f"\n{'='*80}")
    print(f"UNDERWRITER DECISION")
    print(f"{'='*80}")
    decision = all_summary['underwriter_decision']
    print(f"  Authoritative Income: ${decision['authoritative_income']:,.2f}")
    print(f"  Confidence in Result: {decision['confidence_in_result'].upper()}")
    print(f"  Rationale: {decision['rationale']}")
    print(f"  Recommendation: {decision['recommendation']}")
    print(f"\n  Comparison:")
    print(f"    Simple Average:        ${decision['simple_average']:,.2f}")
    print(f"    Confidence-Weighted:   ${decision['confidence_weighted_avg']:,.2f}")
    print(f"    High-Confidence Only:  ${decision['high_confidence_only_avg']:,.2f}")
    print(f"{'='*80}\n")
    
    return all_summary


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print("Usage: python generate_consistency_summary.py <loan_id>")
        print("Example: python generate_consistency_summary.py 1000178662")
        print("\nThis script reads existing income_analysis_run*.json files")
        print("and generates/updates consistency_summary_all.json")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    try:
        generate_consistency_summary(loan_id)
        print("[OK] Consistency summary generated successfully")
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
