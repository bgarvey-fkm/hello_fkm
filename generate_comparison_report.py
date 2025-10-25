"""
Generate HTML Report from Income Comparison Analysis
Loads all income_comparison_analysis.json files and creates a sortable HTML table.
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


def generate_html_report(df, output_path=None):
    """
    Generate an HTML report from the comparison DataFrame.
    
    Args:
        df: pandas DataFrame with comparison data
        output_path: Path to save HTML file (default: reports/income_comparison_report.html)
    
    Returns:
        Path to the generated HTML file
    """
    
    if df is None or len(df) == 0:
        print("❌ No data to generate report")
        return None
    
    # Set default output path
    if output_path is None:
        base_dir = Path(__file__).parent
        reports_dir = base_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        output_path = reports_dir / "income_comparison_report.html"
    
    # Sort by income_type
    df_sorted = df.sort_values('income_type', ascending=True)
    
    # Format columns for better display
    df_display = df_sorted.copy()
    
    # Round numeric columns to 2 decimal places
    numeric_cols = [
        'ai_avg_income', 'ai_median_income', 'ai_min_income', 'ai_max_income',
        'ai_variance_pct', 'form_1003_initial_income', 'form_1003_final_income',
        'form_1003_net_change', 'ai_avg_vs_final_1003_diff', 'ai_avg_vs_final_1003_pct',
        'ai_median_vs_final_1003_diff', 'ai_median_vs_final_1003_pct',
        'base_salary_component', 'variable_income_component'
    ]
    
    for col in numeric_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].round(2)
    
    # Create HTML with custom styling
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Income Comparison Analysis Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        
        .header p {{
            margin: 5px 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        
        .summary-card .subvalue {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }}
        
        .table-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            cursor: pointer;
            white-space: nowrap;
        }}
        
        th:hover {{
            background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
        }}
        
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover {{
            background-color: #f8f9ff;
        }}
        
        .loan-id {{
            font-weight: 600;
            color: #667eea;
        }}
        
        .positive {{
            color: #10b981;
        }}
        
        .negative {{
            color: #ef4444;
        }}
        
        .rating-high {{
            background-color: #d1fae5;
            color: #065f46;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}
        
        .rating-medium {{
            background-color: #fef3c7;
            color: #92400e;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}
        
        .rating-low {{
            background-color: #fee2e2;
            color: #991b1b;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}
        
        .complexity-simple {{
            color: #10b981;
        }}
        
        .complexity-moderate {{
            color: #f59e0b;
        }}
        
        .complexity-complex {{
            color: #ef4444;
        }}
        
        .best-metric {{
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .notes {{
            max-width: 300px;
            white-space: normal;
            font-size: 0.85em;
            color: #666;
        }}
        
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        
        /* Make table scrollable */
        .table-wrapper {{
            max-height: 800px;
            overflow-y: auto;
        }}
    </style>
    <script>
        function sortTable(columnIndex) {{
            const table = document.getElementById('comparisonTable');
            const tbody = table.getElementsByTagName('tbody')[0];
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            
            const currentOrder = table.getAttribute('data-sort-order-' + columnIndex) || 'asc';
            const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
            table.setAttribute('data-sort-order-' + columnIndex, newOrder);
            
            rows.sort((a, b) => {{
                let aVal = a.cells[columnIndex].textContent.trim();
                let bVal = b.cells[columnIndex].textContent.trim();
                
                // Try to parse as number
                const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return newOrder === 'asc' ? aNum - bNum : bNum - aNum;
                }}
                
                // String comparison
                return newOrder === 'asc' 
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }});
            
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</head>
<body>
    <div class="header">
        <h1>📊 Income Comparison Analysis Report</h1>
        <p>AI-Calculated Income vs Form 1003 Ground Truth</p>
        <p>Generated: {report_date}</p>
        <p>Total Loans: {total_loans}</p>
    </div>
    
    <div class="summary">
        <div class="summary-card">
            <h3>Avg Accuracy (Mean)</h3>
            <div class="value">{mean_accuracy}%</div>
            <div class="subvalue">Mean absolute error</div>
        </div>
        
        <div class="summary-card">
            <h3>Avg Accuracy (Median)</h3>
            <div class="value">{median_accuracy}%</div>
            <div class="subvalue">Mean absolute error</div>
        </div>
        
        <div class="summary-card">
            <h3>High Consistency</h3>
            <div class="value">{high_consistency}</div>
            <div class="subvalue">Loans with &lt;1% variance</div>
        </div>
        
        <div class="summary-card">
            <h3>Median is Better</h3>
            <div class="value">{median_better}</div>
            <div class="subvalue">Times median outperforms mean</div>
        </div>
    </div>
    
    <div class="table-container">
        <h2>Detailed Comparison Data (Sorted by Income Type)</h2>
        <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">
            Click column headers to sort. Hover over rows for highlighting.
        </p>
        <div class="table-wrapper">
            {table_html}
        </div>
    </div>
    
    <div class="footer">
        <p>Income Comparison Analysis • Generated by generate_comparison_report.py</p>
    </div>
</body>
</html>
    """
    
    # Calculate summary statistics
    mean_accuracy = df_sorted['ai_avg_vs_final_1003_pct'].abs().mean()
    median_accuracy = df_sorted['ai_median_vs_final_1003_pct'].abs().mean()
    high_consistency = len(df_sorted[df_sorted['ai_consistency_rating'] == 'HIGH'])
    median_better = len(df_sorted[df_sorted['best_ai_metric'] == 'median'])
    
    # Create custom table HTML with formatting
    table_rows = []
    for _, row in df_display.iterrows():
        # Format consistency rating
        rating_class = f"rating-{row['ai_consistency_rating'].lower()}"
        rating_html = f'<span class="{rating_class}">{row["ai_consistency_rating"]}</span>'
        
        # Format complexity
        complexity_class = f"complexity-{row['complexity_level'].lower()}"
        complexity_html = f'<span class="{complexity_class}">{row["complexity_level"]}</span>'
        
        # Format percentage differences with color
        avg_pct = row['ai_avg_vs_final_1003_pct']
        avg_pct_class = 'positive' if avg_pct >= 0 else 'negative'
        avg_pct_html = f'<span class="{avg_pct_class}">{avg_pct:+.2f}%</span>'
        
        median_pct = row['ai_median_vs_final_1003_pct']
        median_pct_class = 'positive' if median_pct >= 0 else 'negative'
        median_pct_html = f'<span class="{median_pct_class}">{median_pct:+.2f}%</span>'
        
        # Format best metric
        best_metric_html = f'<span class="best-metric">{row["best_ai_metric"]}</span>'
        
        # Format boolean flags
        has_bonus = '✓' if row.get('has_bonus', False) else ''
        has_commission = '✓' if row.get('has_commission', False) else ''
        has_overtime = '✓' if row.get('has_overtime', False) else ''
        
        table_row = f"""
        <tr>
            <td class="loan-id">{row['loan_id']}</td>
            <td>{row['income_type']}</td>
            <td>{complexity_html}</td>
            <td>{row.get('pay_frequency', 'N/A')}</td>
            <td>${row['ai_avg_income']:,.2f}</td>
            <td>${row['ai_median_income']:,.2f}</td>
            <td>{row['ai_variance_pct']:.2f}%</td>
            <td>{rating_html}</td>
            <td>${row['form_1003_final_income']:,.2f}</td>
            <td>{avg_pct_html}</td>
            <td>{median_pct_html}</td>
            <td>{best_metric_html}</td>
            <td>${row.get('base_salary_component', 0):,.2f}</td>
            <td>${row.get('variable_income_component', 0):,.2f}</td>
            <td>{has_bonus}</td>
            <td>{has_commission}</td>
            <td>{has_overtime}</td>
            <td class="notes">{row.get('notes', '')}</td>
        </tr>
        """
        table_rows.append(table_row)
    
    table_html = f"""
    <table id="comparisonTable">
        <thead>
            <tr>
                <th onclick="sortTable(0)">Loan ID ↕</th>
                <th onclick="sortTable(1)">Income Type ↕</th>
                <th onclick="sortTable(2)">Complexity ↕</th>
                <th onclick="sortTable(3)">Pay Freq ↕</th>
                <th onclick="sortTable(4)">AI Avg ↕</th>
                <th onclick="sortTable(5)">AI Median ↕</th>
                <th onclick="sortTable(6)">AI Variance % ↕</th>
                <th onclick="sortTable(7)">Consistency ↕</th>
                <th onclick="sortTable(8)">Final 1003 ↕</th>
                <th onclick="sortTable(9)">Avg vs 1003 % ↕</th>
                <th onclick="sortTable(10)">Median vs 1003 % ↕</th>
                <th onclick="sortTable(11)">Best Metric ↕</th>
                <th onclick="sortTable(12)">Base $ ↕</th>
                <th onclick="sortTable(13)">Variable $ ↕</th>
                <th onclick="sortTable(14)">Bonus ↕</th>
                <th onclick="sortTable(15)">Comm ↕</th>
                <th onclick="sortTable(16)">OT ↕</th>
                <th onclick="sortTable(17)">Notes ↕</th>
            </tr>
        </thead>
        <tbody>
            {''.join(table_rows)}
        </tbody>
    </table>
    """
    
    # Fill in template
    html_content = html_template.format(
        report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_loans=len(df_sorted),
        mean_accuracy=f"{mean_accuracy:.2f}",
        median_accuracy=f"{median_accuracy:.2f}",
        high_consistency=high_consistency,
        median_better=median_better,
        table_html=table_html
    )
    
    # Save HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Generated HTML report: {output_path}")
    print(f"   Total loans: {len(df_sorted)}")
    print(f"   Average accuracy (using AI mean): {mean_accuracy:.2f}%")
    print(f"   Average accuracy (using AI median): {median_accuracy:.2f}%")
    print(f"   High consistency loans: {high_consistency}")
    print(f"   Median outperforms mean: {median_better} times")
    
    return output_path


def main():
    """Main entry point."""
    
    print("\n" + "="*80)
    print("INCOME COMPARISON HTML REPORT GENERATOR")
    print("="*80 + "\n")
    
    # Load all comparison data
    df = load_all_comparisons()
    
    if df is None or len(df) == 0:
        print("\n❌ No comparison data found. Run batch_income_comparison.py first.")
        return
    
    # Generate HTML report
    output_path = generate_html_report(df)
    
    if output_path:
        print("\n" + "="*80)
        print("REPORT GENERATION COMPLETE")
        print("="*80)
        print(f"\nOpen the report in your browser:")
        print(f"  {output_path}")


if __name__ == "__main__":
    main()
