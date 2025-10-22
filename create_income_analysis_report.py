# -*- coding: utf-8 -*-
"""
Create HTML report for income analysis consistency test
"""

import json
import sys
from pathlib import Path

def create_report(loan_id):
    """Create an HTML report from the income analysis consistency test results."""
    
    # Load the summary JSON
    summary_file = Path(f"reports/income_analysis_consistency_{loan_id}.json")
    
    if not summary_file.exists():
        print(f"Error: {summary_file} not found")
        return
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    stats = summary.get('statistics', {})
    
    # Determine variance level
    variance_pct = stats.get('variance_percentage', 0)
    if variance_pct < 1:
        variance_class = 'low'
        consistency_rating = 'HIGH - Results are very consistent'
        interpretation = 'the model is highly consistent in its income calculations'
    elif variance_pct < 5:
        variance_class = 'medium'
        consistency_rating = 'MEDIUM - Some variation in results'
        interpretation = 'the model shows moderate consistency with some variation in methodology'
    else:
        variance_class = 'high'
        consistency_rating = 'LOW - Significant variation in results'
        interpretation = 'the model shows significant variation in how it interprets and calculates income from the same source documents'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='UTF-8'>
    <title>Income Analysis Consistency Test - Loan {summary['loan_id']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        h1 {{ color: #2c3e50; margin-bottom: 5px; }}
        h2 {{ color: #34495e; margin-top: 0; font-size: 18px; font-weight: normal; }}
        .overview {{ background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }}
        .stat-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .stat-label {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
        .variance-low {{ color: #27ae60; }}
        .variance-medium {{ color: #f39c12; }}
        .variance-high {{ color: #e74c3c; }}
        .run-section {{ background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .run-header {{ background-color: #3498db; color: white; padding: 10px 15px; margin: -20px -20px 15px -20px; border-radius: 5px 5px 0 0; font-size: 18px; font-weight: bold; }}
        .methodology {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }}
        .methodology h4 {{ margin-top: 0; color: #2c3e50; }}
        .methodology p {{ margin: 5px 0; line-height: 1.6; }}
        .income-breakdown {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }}
        .income-item {{ background-color: #ecf0f1; padding: 10px; border-radius: 3px; }}
        .income-item label {{ font-size: 12px; color: #7f8c8d; }}
        .income-item value {{ font-size: 16px; font-weight: bold; color: #2c3e50; display: block; }}
        .steps {{ background-color: white; border: 1px solid #ddd; border-radius: 3px; padding: 10px; }}
        .steps ol {{ margin: 0; padding-left: 20px; }}
        .steps li {{ margin: 5px 0; line-height: 1.5; }}
        .confidence-high {{ background-color: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
        .confidence-medium {{ background-color: #f39c12; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
        .confidence-low {{ background-color: #e74c3c; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
        .documents-list {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid: #ffc107; margin: 15px 0; }}
        .documents-list h4 {{ margin-top: 0; color: #856404; }}
        .documents-list ul {{ margin: 5px 0; padding-left: 20px; }}
    </style>
</head>
<body>
    <h1>Income Analysis Consistency Test Report</h1>
    <h2>Loan ID: {summary['loan_id']} | {summary['num_runs']} Test Runs</h2>
    
    <div class='overview'>
        <h3>Test Overview</h3>
        <p><strong>Purpose:</strong> Test AI model consistency in calculating monthly income from paystubs and W2 documents using generally accepted mortgage underwriting standards.</p>
        <p><strong>Documents Analyzed:</strong> {summary['documents_analyzed']} income documents</p>
        <div class='documents-list'>
            <h4>Income Documents Used:</h4>
            <ul>
"""
    
    for doc in summary['income_documents']:
        html += f"                <li><strong>{doc['type'].upper()}</strong>: {doc['file_name']}</li>\n"
    
    html += f"""            </ul>
        </div>
        
        <div class='stats-grid'>
            <div class='stat-box'>
                <div class='stat-value'>${stats['average_income']:,.2f}</div>
                <div class='stat-label'>Average Monthly Income</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value'>${stats['min_income']:,.2f}</div>
                <div class='stat-label'>Minimum (Run Result)</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value'>${stats['max_income']:,.2f}</div>
                <div class='stat-label'>Maximum (Run Result)</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value variance-{variance_class}'>{stats['variance_percentage']:.2f}%</div>
                <div class='stat-label'>Variance (Consistency)</div>
            </div>
        </div>
    </div>
"""
    
    # Add each run's details
    for result in summary['results']:
        if 'error' in result:
            continue
        
        methodology = result['calculation_methodology']
        income_comp = methodology['income_components']
        
        html += f"""    <div class='run-section'>
        <div class='run-header'>Run {result['run_number']} - Monthly Income: ${result['monthly_gross_income']:,.2f} <span class='confidence-{result['confidence_level']}'>{result['confidence_level'].upper()} CONFIDENCE</span></div>
        
        <div class='income-breakdown'>
            <div class='income-item'>
                <label>Base Salary</label>
                <value>${income_comp['base_salary']:,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Overtime</label>
                <value>${income_comp['overtime']:,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Bonus</label>
                <value>${income_comp['bonus']:,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Commission</label>
                <value>${income_comp['commission']:,.2f}</value>
            </div>
        </div>
        
        <div class='methodology'>
            <h4>Pay Frequency: {methodology['pay_frequency']}</h4>
        </div>
        
        <div class='methodology'>
            <h4>Paystubs Analysis</h4>
            <p>{methodology['paystubs_analysis']}</p>
        </div>
        
        <div class='methodology'>
            <h4>W2 Analysis</h4>
            <p>{methodology['w2_analysis']}</p>
        </div>
        
        <div class='methodology'>
            <h4>Reconciliation</h4>
            <p>{methodology['reconciliation']}</p>
        </div>
        
        <div class='methodology'>
            <h4>Calculation Steps</h4>
            <div class='steps'>
                <ol>
"""
        
        for step in methodology['calculation_steps']:
            html += f"                    <li>{step}</li>\n"
        
        html += f"""                </ol>
            </div>
        </div>
        
        <div class='methodology'>
            <h4>Additional Notes</h4>
            <p>{result.get('notes', 'No additional notes')}</p>
        </div>
    </div>
"""
    
    html += f"""    <div class='overview'>
        <h3>Consistency Analysis</h3>
        <p><strong>Variance:</strong> ${stats['variance']:,.2f} ({stats['variance_percentage']:.2f}%)</p>
        <p><strong>Consistency Rating:</strong> <span class='confidence-{variance_class}'>{consistency_rating}</span></p>
        <p><strong>Interpretation:</strong> The AI model produced {summary['num_runs']} different monthly income calculations ranging from ${stats['min_income']:,.2f} to ${stats['max_income']:,.2f}. This variance of {stats['variance_percentage']:.2f}% indicates {interpretation}.</p>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    output_file = Path(f"reports/income_analysis_consistency_report_{loan_id}.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\nHTML report created: {output_file}")
    print(f"\nSummary:")
    print(f"  Average Income: ${stats['average_income']:,.2f}")
    print(f"  Variance: {stats['variance_percentage']:.2f}%")
    print(f"  Consistency: {consistency_rating}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_income_analysis_report.py <loan_id>")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    create_report(loan_id)
