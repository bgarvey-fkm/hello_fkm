"""
Generate Income Comparison CSV
===============================
Creates a CSV with loan comparison data from the latest income analysis runs.

Columns:
- loan_id
- income_type (from employment_history.json income_scenario_classification)
- ai_mean (mean of all AI income analysis runs)
- ai_median (median of all AI income analysis runs)
- form_1003_final (final value from form_1003_income_timeline.json)
- median_vs_1003_diff (median - final 1003)
- median_vs_1003_pct (percentage difference)
- high_confidence_count (number of runs with "high" confidence)

Output:
- aggregate_data/income_comparison_latest.csv
"""

import json
import csv
from pathlib import Path
from datetime import datetime
import statistics


def load_json_safe(file_path):
    """Load JSON file safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {file_path}: {e}")
        return None


def get_income_scenario(loan_id):
    """Get income type from employment_history.json."""
    emp_history_file = Path(f"loan_docs/{loan_id}/employment_history/employment_history.json")
    
    if not emp_history_file.exists():
        return "UNKNOWN"
    
    data = load_json_safe(emp_history_file)
    if not data:
        return "UNKNOWN"
    
    scenario = data.get('income_scenario_classification', {})
    return scenario.get('income_type', 'UNKNOWN')


def get_ai_income_values(loan_id):
    """Get all AI income analysis values and confidence levels for a loan from consistency summary."""
    income_analysis_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    
    if not income_analysis_dir.exists():
        return [], 0
    
    # Look for consistency summary files
    summary_files = list(income_analysis_dir.glob("consistency_summary_*.json"))
    
    if not summary_files:
        return [], 0
    
    # Use the most recent summary (usually consistency_summary_runs1-3.json or similar)
    # Sort to get the most comprehensive one
    summary_file = sorted(summary_files)[-1]
    
    data = load_json_safe(summary_file)
    if not data:
        return [], 0
    
    # Extract all run incomes and confidence levels from the summary
    income_values = []
    high_confidence_count = 0
    results = data.get('results', [])
    
    for result in results:
        # Skip results with errors
        if 'error' in result:
            continue
        if 'monthly_gross_income' in result:
            income_values.append(result['monthly_gross_income'])
            # Count high confidence runs
            if result.get('confidence_level', '').lower() == 'high':
                high_confidence_count += 1
    
    return income_values, high_confidence_count


def get_form_1003_final(loan_id):
    """Get final Form 1003 income value."""
    form_1003_file = Path(f"loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.json")
    
    if not form_1003_file.exists():
        return None
    
    data = load_json_safe(form_1003_file)
    if not data:
        return None
    
    # Get the last version (final) from income_by_version
    versions = data.get('income_by_version', [])
    if not versions:
        return None
    
    final_version = versions[-1]
    
    return final_version.get('combined_monthly_income')


def generate_comparison_csv():
    """Generate the comparison CSV."""
    loan_docs_dir = Path("loan_docs")
    
    if not loan_docs_dir.exists():
        print("ERROR: loan_docs directory not found")
        return
    
    # Collect data for all loans
    comparison_data = []
    skipped_no_ai = 0
    skipped_no_1003 = 0
    
    for loan_dir in sorted(loan_docs_dir.iterdir()):
        if not loan_dir.is_dir():
            continue
        
        loan_id = loan_dir.name
        
        # Get income scenario
        income_type = get_income_scenario(loan_id)
        
        # Get AI values and confidence count
        ai_values, high_confidence_count = get_ai_income_values(loan_id)
        if not ai_values:
            skipped_no_ai += 1
            continue  # Skip loans without AI analysis
        
        # Calculate mean and median
        ai_mean = statistics.mean(ai_values)
        ai_median = statistics.median(ai_values)
        
        # Get Form 1003 final value
        form_1003_final = get_form_1003_final(loan_id)
        
        if form_1003_final is None:
            skipped_no_1003 += 1
            print(f"Warning: {loan_id} has AI values but no Form 1003 final")
            continue  # Skip loans without Form 1003 data
        
        # Calculate difference
        median_vs_1003_diff = ai_median - form_1003_final
        median_vs_1003_pct = (median_vs_1003_diff / form_1003_final * 100) if form_1003_final != 0 else 0
        
        comparison_data.append({
            'loan_id': loan_id,
            'income_type': income_type,
            'ai_mean': round(ai_mean, 2),
            'ai_median': round(ai_median, 2),
            'form_1003_final': round(form_1003_final, 2),
            'median_vs_1003_diff': round(median_vs_1003_diff, 2),
            'median_vs_1003_pct': round(median_vs_1003_pct, 2),
            'high_confidence_count': high_confidence_count
        })
    
    print(f"Skipped (no AI): {skipped_no_ai}")
    print(f"Skipped (no 1003): {skipped_no_1003}")
    print(f"Successfully processed: {len(comparison_data)}")
    
    if not comparison_data:
        print("ERROR: No data to write")
        return
    
    # Write CSV
    output_dir = Path("aggregate_data")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "income_comparison_latest.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['loan_id', 'income_type', 'ai_mean', 'ai_median', 'form_1003_final', 
                      'median_vs_1003_diff', 'median_vs_1003_pct', 'high_confidence_count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(comparison_data)
    
    print(f"\n{'='*80}")
    print(f"INCOME COMPARISON CSV GENERATED")
    print(f"{'='*80}")
    print(f"Output file: {output_file}")
    print(f"Total loans: {len(comparison_data)}")
    print(f"{'='*80}\n")
    
    # Print summary statistics
    total_diff = sum(row['median_vs_1003_diff'] for row in comparison_data)
    avg_diff = total_diff / len(comparison_data)
    avg_pct = statistics.mean([row['median_vs_1003_pct'] for row in comparison_data])
    
    print(f"Summary Statistics:")
    print(f"  Average difference: ${avg_diff:,.2f}")
    print(f"  Average percentage: {avg_pct:.2f}%")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    generate_comparison_csv()
