"""
Generate Aggregate CSV from Income Comparison Data
Loads all income_comparison_analysis.json files and saves to CSV for easy analysis.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime


def load_all_comparisons():
    """
    Load all income_comparison_analysis.json files from loan directories.
    
    Returns:
        pd.DataFrame with all comparison data
    """
    
    base_dir = Path(__file__).parent
    loan_docs_dir = base_dir / "loan_docs"
    
    # Find all income_comparison_analysis.json files
    comparison_files = list(loan_docs_dir.glob("*/income_analysis/income_comparison_analysis.json"))
    
    print(f"Found {len(comparison_files)} income comparison files")
    
    if not comparison_files:
        print("\n❌ No comparison files found!")
        print("   Run batch_income_comparison.py first to generate these files.")
        return None
    
    # Load all comparison data
    data = []
    for comp_file in comparison_files:
        try:
            with open(comp_file, 'r', encoding='utf-8') as f:
                comparison = json.load(f)
                data.append(comparison)
        except Exception as e:
            print(f"⚠️  Error loading {comp_file}: {e}")
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    print(f"✅ Loaded {len(df)} loan comparisons into DataFrame")
    
    return df


def save_to_csv(df, output_dir=None):
    """
    Save DataFrame to CSV file.
    
    Args:
        df: DataFrame to save
        output_dir: Directory to save CSV (default: aggregate_data/)
    
    Returns:
        Path to saved CSV file
    """
    
    if df is None or len(df) == 0:
        print("❌ No data to save")
        return None
    
    # Set default output directory
    if output_dir is None:
        base_dir = Path(__file__).parent
        output_dir = base_dir / "aggregate_data"
    
    # Create directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"income_comparison_data_{timestamp}.csv"
    
    # Also save a "latest" version without timestamp
    csv_latest_path = output_dir / "income_comparison_data_latest.csv"
    
    # Sort by loan_id before saving
    df_sorted = df.sort_values('loan_id', ascending=True)
    
    # Save to CSV
    df_sorted.to_csv(csv_path, index=False, encoding='utf-8')
    df_sorted.to_csv(csv_latest_path, index=False, encoding='utf-8')
    
    print(f"\n✅ Saved CSV files:")
    print(f"   Timestamped: {csv_path}")
    print(f"   Latest: {csv_latest_path}")
    
    # Also save as JSON for easy reloading
    json_path = output_dir / "income_comparison_data_latest.json"
    df_sorted.to_json(json_path, orient='records', indent=2)
    print(f"   JSON: {json_path}")
    
    return csv_latest_path


def print_summary(df):
    """Print summary statistics."""
    
    if df is None or len(df) == 0:
        return
    
    print("\n" + "="*80)
    print("DATA SUMMARY")
    print("="*80)
    
    print(f"\nTotal Loans: {len(df)}")
    
    # By income type
    print("\nBy Income Type:")
    print(df['income_type'].value_counts().to_string())
    
    # By complexity
    print("\nBy Complexity Level:")
    print(df['complexity_level'].value_counts().to_string())
    
    # By consistency rating
    print("\nBy AI Consistency Rating:")
    print(df['ai_consistency_rating'].value_counts().to_string())
    
    # Accuracy statistics
    print("\n" + "-"*80)
    print("ACCURACY STATISTICS")
    print("-"*80)
    
    print("\nAI Average vs Final 1003:")
    print(f"  Mean Absolute Error: {df['ai_avg_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  Median Absolute Error: {df['ai_avg_vs_final_1003_pct'].abs().median():.2f}%")
    print(f"  Std Deviation: {df['ai_avg_vs_final_1003_pct'].std():.2f}%")
    
    print("\nAI Median vs Final 1003:")
    print(f"  Mean Absolute Error: {df['ai_median_vs_final_1003_pct'].abs().mean():.2f}%")
    print(f"  Median Absolute Error: {df['ai_median_vs_final_1003_pct'].abs().median():.2f}%")
    print(f"  Std Deviation: {df['ai_median_vs_final_1003_pct'].std():.2f}%")
    
    # Best metric count
    print("\nBest AI Metric:")
    print(df['best_ai_metric'].value_counts().to_string())
    
    # Available columns
    print("\n" + "-"*80)
    print("AVAILABLE COLUMNS")
    print("-"*80)
    print("\nDataFrame contains the following columns:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")


def main():
    """Main entry point."""
    
    print("\n" + "="*80)
    print("AGGREGATE DATA GENERATOR - Income Comparison CSV")
    print("="*80 + "\n")
    
    # Load all comparison data
    df = load_all_comparisons()
    
    if df is None or len(df) == 0:
        print("\n❌ No comparison data found. Run batch_income_comparison.py first.")
        return
    
    # Save to CSV
    csv_path = save_to_csv(df)
    
    if csv_path:
        # Print summary
        print_summary(df)
        
        print("\n" + "="*80)
        print("CSV GENERATION COMPLETE")
        print("="*80)
        print(f"\nYou can now load the data without running the model:")
        print(f"\n  import pandas as pd")
        print(f"  df = pd.read_csv('aggregate_data/income_comparison_data_latest.csv')")
        print(f"\nOr in Excel/Google Sheets, open:")
        print(f"  {csv_path}")


if __name__ == "__main__":
    main()
