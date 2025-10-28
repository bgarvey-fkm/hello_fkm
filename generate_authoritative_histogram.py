"""
Generate histogram of AI Authoritative Income accuracy vs Form 1003
Uses 2.5% buckets with tails grouped at +/- 10%
Filters to only include loans with consistent borrowers across all Form 1003 versions
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json


def create_histogram():
    """Create histogram with 2.5% buckets, filtering for consistent borrowers only."""
    
    # Load the CSV
    csv_file = Path("aggregate_data") / "authoritative_income_comparison.csv"
    df = pd.read_csv(csv_file)
    
    print(f"[OK] Loaded {len(df)} loans from CSV")
    
    # Filter for loans with consistent borrowers only
    consistent_loan_ids = []
    for _, row in df.iterrows():
        loan_id = row['loan_id']
        timeline_file = Path(f"loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.json")
        
        if timeline_file.exists():
            try:
                with open(timeline_file, 'r', encoding='utf-8') as f:
                    timeline_data = json.load(f)
                
                borrower_consistency = timeline_data.get('borrower_consistency', {})
                is_consistent = borrower_consistency.get('is_consistent', False)
                
                if is_consistent:
                    consistent_loan_ids.append(loan_id)
            except Exception:
                continue
    
    # Filter dataframe
    df = df[df['loan_id'].isin(consistent_loan_ids)]
    print(f"[OK] Filtered to {len(df)} loans with CONSISTENT borrowers")
    print(f"[INFO] Analyzing loans where borrowers are the same across all Form 1003 versions\n")
    
    # Get the percentage differences
    diffs = df['auth_diff_pct'].values
    
    # Create bins: <-10%, -10 to -7.5, -7.5 to -5, ..., 7.5 to 10, >10%
    bins = []
    labels = []
    
    # Left tail
    bins.append(float('-inf'))
    labels.append('< -10%')
    
    # -10% to +10% in 2.5% increments
    bin_edges = [-10, -7.5, -5, -2.5, 0, 2.5, 5, 7.5, 10]
    for edge in bin_edges:
        bins.append(edge)
    
    # Create labels for middle bins
    for i in range(len(bin_edges) - 1):
        start = bin_edges[i]
        end = bin_edges[i + 1]
        labels.append(f'{start:+.1f}% to {end:+.1f}%')
    
    # Right tail
    bins.append(float('inf'))
    labels.append('> +10%')
    
    # Bin the data
    df['bucket'] = pd.cut(diffs, bins=bins, labels=labels, include_lowest=True)
    
    # Count by bucket
    bucket_counts = df['bucket'].value_counts().sort_index()
    
    # Create the plot
    plt.figure(figsize=(14, 7))
    
    # Create colors (red for negative, green for positive, darker for tails)
    colors = []
    for label in bucket_counts.index:
        if '< -10%' in label:
            colors.append('#8B0000')  # Dark red
        elif '> +10%' in label:
            colors.append('#006400')  # Dark green
        elif '-' in label and 'to' in label:
            colors.append('#FF6B6B')  # Light red
        elif '+' in label and 'to' in label:
            colors.append('#90EE90')  # Light green
        else:
            colors.append('#FFD700')  # Gold for near-zero
    
    # Plot
    bars = plt.bar(range(len(bucket_counts)), bucket_counts.values, color=colors, edgecolor='black', linewidth=0.5)
    
    # Customize
    plt.xlabel('Percentage Difference (AI Authoritative - Form 1003)', fontsize=12, fontweight='bold')
    plt.ylabel('Number of Loans', fontsize=12, fontweight='bold')
    plt.title('AI Authoritative Income Accuracy Distribution\n(Confidence-Weighted Average vs Form 1003 Final Income)\nConsistent Borrowers Only', 
              fontsize=14, fontweight='bold', pad=20)
    plt.xticks(range(len(bucket_counts)), bucket_counts.index, rotation=45, ha='right', fontsize=9)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, bucket_counts.values)):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add summary statistics box
    total = len(diffs)
    within_5 = sum((diffs >= -5) & (diffs <= 5))
    within_10 = sum((diffs >= -10) & (diffs <= 10))
    avg_diff = diffs.mean()
    avg_abs_diff = abs(diffs).mean()
    
    stats_text = f'Total Loans: {total}\n'
    stats_text += f'Within ±5%: {within_5} ({within_5/total*100:.1f}%)\n'
    stats_text += f'Within ±10%: {within_10} ({within_10/total*100:.1f}%)\n'
    stats_text += f'Avg Diff: {avg_diff:+.2f}%\n'
    stats_text += f'Avg |Diff|: {avg_abs_diff:.2f}%'
    
    plt.text(0.02, 0.98, stats_text,
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             fontsize=10,
             fontfamily='monospace')
    
    plt.tight_layout()
    
    # Save
    output_file = Path("reports") / "authoritative_income_histogram.png"
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] Histogram saved: {output_file}")
    
    # Show distribution table
    print(f"\nDistribution Summary:")
    print(f"{'Bucket':<20} {'Count':>6} {'Percent':>8}")
    print("-" * 36)
    for bucket, count in bucket_counts.items():
        pct = count / total * 100
        print(f"{bucket:<20} {count:>6} {pct:>7.1f}%")
    
    plt.show()


if __name__ == "__main__":
    create_histogram()
