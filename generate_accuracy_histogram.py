"""
Generate Histogram of AI Median vs Final Form 1003 Accuracy
Shows distribution of errors in 2.5% increments with tails at ±10%+
Refactored to use the income_comparison_latest.csv file
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np


def load_comparison_csv():
    """Load the income comparison CSV file."""
    
    base_dir = Path(__file__).parent
    csv_path = base_dir / "aggregate_data" / "income_comparison_latest.csv"
    
    if not csv_path.exists():
        print(f"\n❌ CSV file not found: {csv_path}")
        print("Run generate_income_comparison_csv.py first to create the CSV.")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(df)} loan comparisons from CSV")
        return df
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return None


def create_single_histogram(ax, errors, title, subtitle=""):
    """
    Create a single histogram on the given axis.
    
    Args:
        ax: Matplotlib axis to plot on
        errors: Array of error percentages
        title: Title for the histogram
        subtitle: Optional subtitle with statistics
    """
    
    # Define bins: -10%-, [-10, -7.5), [-7.5, -5), ..., [7.5, 10), 10%+
    bins = [-np.inf, -10, -7.5, -5, -2.5, 0, 2.5, 5, 7.5, 10, np.inf]
    bin_labels = [
        '<-10%',
        '-10 to\n-7.5%',
        '-7.5 to\n-5%',
        '-5 to\n-2.5%',
        '-2.5 to\n0%',
        '0 to\n2.5%',
        '2.5 to\n5%',
        '5 to\n7.5%',
        '7.5 to\n10%',
        '>10%'
    ]
    
    # Create the histogram data
    hist, bin_edges = np.histogram(errors, bins=bins)
    
    # Create bar chart
    x_positions = np.arange(len(bin_labels))
    colors = []
    for i, label in enumerate(bin_labels):
        if 'to\n0%' in label or '0 to' in label:
            colors.append('#10b981')  # Green for close to zero
        elif '<-10%' in label or '>10%' in label:
            colors.append('#ef4444')  # Red for tails
        elif '-5 to' in label or '5 to' in label:
            colors.append('#f59e0b')  # Orange for moderate
        else:
            colors.append('#3b82f6')  # Blue for others
    
    bars = ax.bar(x_positions, hist, color=colors, alpha=0.8, edgecolor='black', linewidth=1.2)
    
    # Add value labels on top of bars
    max_height = max(hist) if max(hist) > 0 else 1
    for i, (bar, count) in enumerate(zip(bars, hist)):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_height*0.02,
                    str(int(count)), ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # Customize the plot
    ax.set_xlabel('Error Range (AI Median vs Final 1003)', fontsize=9, fontweight='bold')
    ax.set_ylabel('# Loans', fontsize=9, fontweight='bold')
    
    if subtitle:
        ax.set_title(f'{title}\n{subtitle}', fontsize=10, fontweight='bold', pad=10)
    else:
        ax.set_title(title, fontsize=10, fontweight='bold', pad=10)
    
    ax.set_xticks(x_positions)
    ax.set_xticklabels(bin_labels, rotation=45, ha='right', fontsize=7)
    ax.tick_params(axis='y', labelsize=8)
    
    # Add grid for easier reading
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add a vertical line at 0
    ax.axvline(x=4.5, color='black', linestyle='--', linewidth=1.5, alpha=0.5)
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)


def create_histogram(df, output_path=None):
    """
    Create histogram of AI Median vs Final 1003 accuracy.
    Creates 4 subplots: Overall + 3 income types
    
    Args:
        df: DataFrame with comparison data
        output_path: Path to save histogram image
    
    Returns:
        Path to saved image
    """
    
    if df is None or len(df) == 0:
        print("❌ No data to plot")
        return None
    
    # Set default output path
    if output_path is None:
        base_dir = Path(__file__).parent
        reports_dir = base_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        output_path = reports_dir / "accuracy_histogram.png"
    
    # Get the median vs final 1003 percentage differences
    errors_all = df['median_vs_1003_pct'].values
    
    # Create figure with 4 subplots (2x2 grid)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('AI Accuracy Distribution: Median Income vs Final Form 1003\nBy Income Type',
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Plot 1: Overall (top-left)
    ax1 = axes[0, 0]
    subtitle1 = f'n={len(errors_all)} | MAE={np.abs(errors_all).mean():.2f}% | Median AE={np.median(np.abs(errors_all)):.2f}%'
    create_single_histogram(ax1, errors_all, 'ALL INCOME TYPES', subtitle1)
    
    # Get income types
    income_types = df['income_type'].unique()
    print(f"\nIncome types found: {income_types}")
    
    # Sort income types for consistent ordering
    income_type_order = ['base_only', 'base_plus_variable', 'hourly_fluctuating']
    available_types = [t for t in income_type_order if t in income_types]
    
    # Plot 2: First income type (top-right)
    ax2 = axes[0, 1]
    if len(available_types) > 0:
        income_type_1 = available_types[0]
        df_type_1 = df[df['income_type'] == income_type_1]
        errors_1 = df_type_1['median_vs_1003_pct'].values
        subtitle2 = f'n={len(errors_1)} | MAE={np.abs(errors_1).mean():.2f}% | Median AE={np.median(np.abs(errors_1)):.2f}%'
        title_1 = income_type_1.replace('_', ' ').upper()
        create_single_histogram(ax2, errors_1, title_1, subtitle2)
    else:
        ax2.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)
        ax2.set_xticks([])
        ax2.set_yticks([])
    
    # Plot 3: Second income type (bottom-left)
    ax3 = axes[1, 0]
    if len(available_types) > 1:
        income_type_2 = available_types[1]
        df_type_2 = df[df['income_type'] == income_type_2]
        errors_2 = df_type_2['median_vs_1003_pct'].values
        subtitle3 = f'n={len(errors_2)} | MAE={np.abs(errors_2).mean():.2f}% | Median AE={np.median(np.abs(errors_2)):.2f}%'
        title_2 = income_type_2.replace('_', ' ').upper()
        create_single_histogram(ax3, errors_2, title_2, subtitle3)
    else:
        ax3.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)
        ax3.set_xticks([])
        ax3.set_yticks([])
    
    # Plot 4: Third income type (bottom-right)
    ax4 = axes[1, 1]
    if len(available_types) > 2:
        income_type_3 = available_types[2]
        df_type_3 = df[df['income_type'] == income_type_3]
        errors_3 = df_type_3['median_vs_1003_pct'].values
        subtitle4 = f'n={len(errors_3)} | MAE={np.abs(errors_3).mean():.2f}% | Median AE={np.median(np.abs(errors_3)):.2f}%'
        title_3 = income_type_3.replace('_', ' ').upper()
        create_single_histogram(ax4, errors_3, title_3, subtitle4)
    else:
        ax4.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)
        ax4.set_xticks([])
        ax4.set_yticks([])
    
    # Adjust layout to prevent overlap
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    # Save the figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Saved 4-panel histogram to: {output_path}")
    
    # Print statistics for overall
    print("\n" + "="*80)
    print("ACCURACY DISTRIBUTION STATISTICS")
    print("="*80)
    print(f"\nOVERALL - Total Loans: {len(errors_all)}")
    print(f"  Mean Error: {errors_all.mean():.2f}%")
    print(f"  Mean Absolute Error: {np.abs(errors_all).mean():.2f}%")
    print(f"  Median Error: {np.median(errors_all):.2f}%")
    print(f"  Median Absolute Error: {np.median(np.abs(errors_all)):.2f}%")
    print(f"  Std Deviation: {errors_all.std():.2f}%")
    
    # Calculate percentage within certain thresholds
    within_2_5 = np.sum(np.abs(errors_all) <= 2.5)
    within_5 = np.sum(np.abs(errors_all) <= 5.0)
    within_10 = np.sum(np.abs(errors_all) <= 10.0)
    
    print(f"\nAccuracy Thresholds (Overall):")
    print(f"  Within ±2.5%: {within_2_5} loans ({within_2_5/len(errors_all)*100:.1f}%)")
    print(f"  Within ±5.0%: {within_5} loans ({within_5/len(errors_all)*100:.1f}%)")
    print(f"  Within ±10.0%: {within_10} loans ({within_10/len(errors_all)*100:.1f}%)")
    print(f"  Beyond ±10.0%: {len(errors_all) - within_10} loans ({(len(errors_all) - within_10)/len(errors_all)*100:.1f}%)")
    
    # Print stats by income type
    print("\n" + "-"*80)
    print("BY INCOME TYPE")
    print("-"*80)
    for income_type in available_types:
        df_type = df[df['income_type'] == income_type]
        errors_type = df_type['median_vs_1003_pct'].values
        within_5_type = np.sum(np.abs(errors_type) <= 5.0)
        print(f"\n{income_type.replace('_', ' ').upper()} ({len(errors_type)} loans):")
        print(f"  Mean Absolute Error: {np.abs(errors_type).mean():.2f}%")
        print(f"  Median Absolute Error: {np.median(np.abs(errors_type)):.2f}%")
        print(f"  Within ±5%: {within_5_type} ({within_5_type/len(errors_type)*100:.1f}%)")
    
    return output_path


def main():
    """Main entry point."""
    
    print("\n" + "="*80)
    print("AI ACCURACY HISTOGRAM GENERATOR")
    print("="*80 + "\n")
    
    # Load comparison CSV
    df = load_comparison_csv()
    
    if df is None or len(df) == 0:
        print("\n❌ No comparison data found. Run generate_income_comparison_csv.py first.")
        return
    
    # Create histogram
    output_path = create_histogram(df)
    
    if output_path:
        print("\n" + "="*80)
        print("HISTOGRAM GENERATION COMPLETE")
        print("="*80)
        print(f"\nView the histogram:")
        print(f"  {output_path}")
        
        # Also create an HTML page to display the histogram
        html_path = output_path.parent / "accuracy_histogram.html"
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI Accuracy Histogram</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        img {{
            width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 20px;
        }}
        .back-link {{
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }}
        .back-link:hover {{
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 AI Accuracy Distribution</h1>
        <p>Distribution of errors between AI Median calculations and Final Form 1003 values</p>
        <img src="accuracy_histogram.png" alt="Accuracy Histogram">
        <br>
        <a href="income_comparison_report.html" class="back-link">← Back to Full Report</a>
    </div>
</body>
</html>
"""
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nAlso created HTML viewer:")
        print(f"  {html_path}")


if __name__ == "__main__":
    main()
