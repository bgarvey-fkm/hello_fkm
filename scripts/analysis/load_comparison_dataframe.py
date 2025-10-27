"""
Load Income Comparison Results into Pandas DataFrame
Provides easy analysis and visualization of AI accuracy vs Form 1003 ground truth.
"""

import pandas as pd
import json
from pathlib import Path

def load_comparison_dataframe(source='aggregate'):
    """
    Load comparison data into a pandas DataFrame.
    
    Args:
        source: Either 'aggregate' (from reports/all_loans_income_comparison.json)
                or 'individual' (from each loan's income_analysis directory)
    
    Returns:
        pd.DataFrame with all comparison metrics
    """
    
    base_dir = Path(__file__).parent
    
    if source == 'aggregate':
        # Load from aggregate file
        aggregate_file = base_dir / "reports" / "all_loans_income_comparison.json"
        
        if not aggregate_file.exists():
            print(f"❌ Aggregate file not found: {aggregate_file}")
            print("   Run batch_income_comparison.py first to generate this file.")
            return None
        
        df = pd.read_json(aggregate_file)
        print(f"✅ Loaded {len(df)} loans from aggregate file")
        
    else:  # individual
        # Load from individual loan directories
        loan_docs_dir = base_dir / "loan_docs"
        comparison_files = list(loan_docs_dir.glob("*/income_analysis/income_comparison_analysis.json"))
        
        if not comparison_files:
            print("❌ No comparison files found in loan directories")
            print("   Run batch_income_comparison.py first to generate these files.")
            return None
        
        # Load all comparison files
        data = []
        for comp_file in comparison_files:
            with open(comp_file, 'r', encoding='utf-8') as f:
                data.append(json.load(f))
        
        df = pd.DataFrame(data)
        print(f"✅ Loaded {len(df)} loans from individual files")
    
    return df


def print_summary_stats(df):
    """Print summary statistics from the comparison DataFrame."""
    
    if df is None or len(df) == 0:
        print("No data to summarize")
        return
    
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    # Overall counts
    print(f"\nTotal Loans: {len(df)}")
    
    # By complexity
    print("\nBy Complexity Level:")
    print(df['complexity_level'].value_counts().sort_index())
    
    # By consistency rating
    print("\nBy AI Consistency Rating:")
    print(df['ai_consistency_rating'].value_counts().sort_index())
    
    # By income type
    print("\nBy Income Type:")
    print(df['income_type'].value_counts())
    
    # Accuracy metrics
    print("\n" + "-"*80)
    print("ACCURACY METRICS (AI vs Final Form 1003)")
    print("-"*80)
    
    # Mean-based accuracy
    print("\nUsing AI Average (Mean):")
    print(f"  Mean Absolute Error: {df['ai_avg_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  Median Absolute Error: {df['ai_avg_vs_final_1003_pct'].abs().median():.2f}%")
    print(f"  Max Error: {df['ai_avg_vs_final_1003_pct'].abs().max():.2f}%")
    print(f"  Std Dev: {df['ai_avg_vs_final_1003_pct'].std():.2f}%")
    
    # Median-based accuracy
    print("\nUsing AI Median:")
    print(f"  Mean Absolute Error: {df['ai_median_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  Median Absolute Error: {df['ai_median_vs_final_1003_pct'].abs().median():.2f}%")
    print(f"  Max Error: {df['ai_median_vs_final_1003_pct'].abs().max():.2f}%")
    print(f"  Std Dev: {df['ai_median_vs_final_1003_pct'].std():.2f}%")
    
    # Best metric comparison
    print("\nBest AI Metric (Mean vs Median):")
    print(df['best_ai_metric'].value_counts())
    
    # Accuracy by complexity
    print("\n" + "-"*80)
    print("ACCURACY BY COMPLEXITY")
    print("-"*80)
    
    for complexity in df['complexity_level'].unique():
        subset = df[df['complexity_level'] == complexity]
        print(f"\n{complexity.upper()} ({len(subset)} loans):")
        print(f"  AI Avg Error: {subset['ai_avg_vs_final_1003_pct'].abs().mean():.2f}%")
        print(f"  AI Median Error: {subset['ai_median_vs_final_1003_pct'].abs().mean():.2f}%")
        print(f"  AI Variance: {subset['ai_variance_pct'].mean():.2f}%")
    
    # Accuracy by consistency rating
    print("\n" + "-"*80)
    print("ACCURACY BY AI CONSISTENCY RATING")
    print("-"*80)
    
    for rating in ['HIGH', 'MEDIUM', 'LOW']:
        subset = df[df['ai_consistency_rating'] == rating]
        if len(subset) > 0:
            print(f"\n{rating} Consistency ({len(subset)} loans):")
            print(f"  AI Avg Error: {subset['ai_avg_vs_final_1003_pct'].abs().mean():.2f}%")
            print(f"  AI Median Error: {subset['ai_median_vs_final_1003_pct'].abs().mean():.2f}%")
    
    # Variable income analysis
    print("\n" + "-"*80)
    print("VARIABLE INCOME ANALYSIS")
    print("-"*80)
    
    has_variable = df[df['income_type'].str.contains('variable', case=False, na=False)]
    no_variable = df[~df['income_type'].str.contains('variable', case=False, na=False)]
    
    print(f"\nWith Variable Income ({len(has_variable)} loans):")
    print(f"  AI Avg Error: {has_variable['ai_avg_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  AI Median Error: {has_variable['ai_median_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  AI Variance: {has_variable['ai_variance_pct'].mean():.2f}%")
    
    print(f"\nWithout Variable Income ({len(no_variable)} loans):")
    print(f"  AI Avg Error: {no_variable['ai_avg_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  AI Median Error: {no_variable['ai_median_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  AI Variance: {no_variable['ai_variance_pct'].mean():.2f}%")


def main():
    """Main entry point - load and display summary."""
    
    print("\nLoading income comparison data...")
    
    # Try aggregate file first, fall back to individual files
    df = load_comparison_dataframe('aggregate')
    
    if df is None:
        print("\nTrying individual loan files...")
        df = load_comparison_dataframe('individual')
    
    if df is not None:
        print_summary_stats(df)
        
        print("\n" + "="*80)
        print("DataFrame is ready for analysis!")
        print("="*80)
        print("\nYou can now use the DataFrame for further analysis:")
        print("  import pandas as pd")
        print("  from load_comparison_dataframe import load_comparison_dataframe")
        print("  df = load_comparison_dataframe()")
        print("\nAvailable columns:")
        for col in df.columns:
            print(f"  - {col}")
    else:
        print("\n❌ Could not load comparison data")
        print("   Please run batch_income_comparison.py first")


if __name__ == "__main__":
    main()
