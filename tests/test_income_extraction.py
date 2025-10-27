from pathlib import Path
import json

loan_id = '1000177101'
p = Path(f'loan_docs/{loan_id}/income_analysis')
files = list(p.glob('consistency_summary_*.json'))
print(f'Files: {[f.name for f in files]}')

if files:
    data = json.load(open(files[0]))
    print(f'Results count: {len(data.get("results", []))}')
    incomes = [r["monthly_gross_income"] for r in data.get("results", [])]
    print(f'Income values: {incomes}')
