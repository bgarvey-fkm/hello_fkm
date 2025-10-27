"""Quick analysis of confidence counts in CSV."""
import pandas as pd

df = pd.read_csv('aggregate_data/income_comparison_latest.csv')

print('='*80)
print('HIGH CONFIDENCE COUNT ANALYSIS')
print('='*80)
print('\nDistribution of high_confidence_count:')
print(df['high_confidence_count'].value_counts().sort_index())

print(f'\nAverage high confidence count: {df["high_confidence_count"].mean():.2f}')
print(f'Loans with all 3 high confidence: {(df["high_confidence_count"] == 3).sum()} ({(df["high_confidence_count"] == 3).sum() / len(df) * 100:.1f}%)')
print(f'Loans with 2+ high confidence: {(df["high_confidence_count"] >= 2).sum()} ({(df["high_confidence_count"] >= 2).sum() / len(df) * 100:.1f}%)')
print(f'Loans with 0 high confidence: {(df["high_confidence_count"] == 0).sum()} ({(df["high_confidence_count"] == 0).sum() / len(df) * 100:.1f}%)')

print('\n' + '='*80)
print('CONFIDENCE vs VARIANCE CORRELATION')
print('='*80)

# Group by confidence count and look at average absolute variance
grouped = df.groupby('high_confidence_count').agg({
    'median_vs_1003_pct': ['mean', 'std', lambda x: abs(x).mean()],
    'loan_id': 'count'
}).round(2)

grouped.columns = ['Avg Variance %', 'Std Dev %', 'Avg Abs Variance %', 'Loan Count']
print(grouped)

print('\n' + '='*80)
print('LOANS WITH 0 HIGH CONFIDENCE (Potential Issues)')
print('='*80)
zero_conf = df[df['high_confidence_count'] == 0][['loan_id', 'income_type', 'median_vs_1003_pct', 'high_confidence_count']]
print(zero_conf.to_string(index=False))
