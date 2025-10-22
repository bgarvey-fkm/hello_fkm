# -*- coding: utf-8 -*-
"""
Income Analysis Agent
Tests model consistency in calculating monthly income from paystubs and W2s
using generally accepted mortgage underwriting standards.
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Load environment variables
load_dotenv()


def load_freddie_mac_guidelines():
    """
    Load the compressed Freddie Mac guidelines for income calculation.
    
    Returns:
        String containing relevant income calculation rules
    """
    guidelines_file = Path("guidelines/freddie_mac_guide_5300_5400_compressed.json")
    
    if not guidelines_file.exists():
        return ""
    
    try:
        with open(guidelines_file, 'r', encoding='utf-8') as f:
            guidelines = json.load(f)
        
        # Format the rules into a readable string
        rules_text = "FREDDIE MAC INCOME CALCULATION GUIDELINES:\n\n"
        for rule in guidelines.get('rules', []):
            rules_text += f"Section {rule['section']} - {rule['topic']}:\n"
            rules_text += f"  {rule['rule']}\n"
            if rule.get('details'):
                for detail in rule['details']:
                    rules_text += f"  • {detail}\n"
            rules_text += "\n"
        
        return rules_text
        
    except Exception as e:
        print(f"Warning: Could not load Freddie Mac guidelines: {e}")
        return ""


async def filter_income_documents_by_guidelines(loan_id):
    """
    Load ALL semantic JSON files and use Freddie Mac guidelines to determine
    which documents are relevant for income verification.
    
    Args:
        loan_id: The loan identifier
        
    Returns:
        List of document objects relevant for income verification
    """
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"Error: Directory {semantic_dir} does not exist")
        return []
    
    # Load Freddie Mac guidelines
    guidelines = load_freddie_mac_guidelines()
    if not guidelines:
        print("Warning: No Freddie Mac guidelines found, falling back to basic filter")
        return load_income_documents_basic(loan_id)
    
    # Initialize Azure OpenAI client
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    print("\n>> Analyzing all documents to determine income verification relevance...")
    
    all_docs = []
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            all_docs.append({
                'file_path': str(json_file),
                'file_id': doc.get('metadata', {}).get('FileId'),
                'file_name': doc.get('metadata', {}).get('FileName'),
                'doc_type': doc.get('semantic_content', {}).get('document_type', 'unknown'),
                'metadata': doc.get('metadata', {}),
                'semantic_content': doc.get('semantic_content', {})
            })
        except Exception as e:
            continue
    
    print(f">> Found {len(all_docs)} total documents")
    print(f">> Filtering based on Freddie Mac income verification guidelines...")
    
    # Create a summary of each document for filtering
    doc_summaries = []
    for doc in all_docs:
        doc_summaries.append({
            'file_id': doc['file_id'],
            'file_name': doc['file_name'],
            'document_type': doc['doc_type'],
            'summary': doc['semantic_content'].get('summary', ''),
            'content_preview': str(doc['semantic_content'])[:500]
        })
    
    # Ask LLM to filter based on guidelines
    filter_prompt = f"""Based on the Freddie Mac income verification guidelines below, review the following list of documents and identify which ones are RELEVANT for verifying a borrower's income.

{guidelines}

DOCUMENTS TO REVIEW:
{json.dumps(doc_summaries, indent=2)}

Return a JSON object with this structure:
{{
  "income_verification_documents": [
    {{
      "file_id": <file_id>,
      "reason": "<why this document is relevant per Freddie Mac guidelines>"
    }}
  ],
  "excluded_documents": [
    {{
      "file_id": <file_id>,
      "reason": "<why this document is NOT relevant for income verification>"
    }}
  ]
}}

ONLY include documents that are acceptable income verification sources per Freddie Mac guidelines (paystubs, W-2s, tax returns, employment verification, 1099s, pension statements, etc.)."""

    try:
        response = await client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": "You are an expert mortgage underwriter who knows Freddie Mac income verification guidelines."},
                {"role": "user", "content": filter_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        filter_result = json.loads(response.choices[0].message.content)
        
        # Extract the file IDs that should be included
        included_file_ids = set(doc['file_id'] for doc in filter_result.get('income_verification_documents', []))
        
        # Filter the original documents
        income_docs = []
        for doc in all_docs:
            if doc['file_id'] in included_file_ids:
                reason = next((d['reason'] for d in filter_result['income_verification_documents'] if d['file_id'] == doc['file_id']), 'Relevant')
                income_docs.append({
                    'file_id': doc['file_id'],
                    'file_name': doc['file_name'],
                    'document_type': doc['doc_type'],
                    'upload_date': doc['metadata'].get('FileUploadDate'),
                    'semantic_content': doc['semantic_content'],
                    'inclusion_reason': reason
                })
                print(f">> ✓ Included: {doc['file_name'][:60]} - {reason[:80]}")
        
        print(f"\n>> Filtered to {len(income_docs)} income verification documents (from {len(all_docs)} total)")
        
        await client.close()
        return income_docs
        
    except Exception as e:
        print(f"Error during document filtering: {e}")
        print("Falling back to basic filter")
        await client.close()
        return load_income_documents_basic(loan_id)


def load_income_documents_basic(loan_id):
    """
    Basic document filter - fallback when LLM filtering fails.
    Load documents based on simple document_type matching.
    
    Args:
        loan_id: The loan identifier
        
    Returns:
        List of document objects containing paystubs and W2s
    """
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"Error: Directory {semantic_dir} does not exist")
        return []
    
    income_docs = []
    
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
                
            # Check if document_type is paystub, w2, or 1099-r
            doc_type = doc.get('semantic_content', {}).get('document_type', '').lower()
            
            if doc_type in ['paystub', 'w2', 'form_1099-r', 'tax_return', 'employment_verification']:
                income_docs.append({
                    'file_id': doc.get('metadata', {}).get('FileId'),
                    'file_name': doc.get('metadata', {}).get('FileName'),
                    'document_type': doc_type,
                    'upload_date': doc.get('metadata', {}).get('FileUploadDate'),
                    'semantic_content': doc.get('semantic_content', {})
                })
                print(f">> Loaded {doc_type}: {doc.get('metadata', {}).get('FileName')}")
                
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
            continue
    
    return income_docs


async def analyze_income(income_docs, loan_id, run_number=1):
    """
    Use Azure OpenAI to analyze income documents and calculate monthly income
    using generally accepted mortgage underwriting standards.
    
    Args:
        income_docs: List of income document objects
        loan_id: The loan identifier
        run_number: Run number for this analysis
        
    Returns:
        Dict containing income analysis results
    """
    if not income_docs:
        return {"error": "No income documents found"}
    
    # Initialize Azure OpenAI client
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Load Freddie Mac guidelines
    guidelines = load_freddie_mac_guidelines()
    
    # Create prompt with income documents
    prompt = f"""You are a mortgage underwriting income analyst. Analyze the following income documents and calculate the borrower's monthly income using Freddie Mac guidelines.

{guidelines}

INCOME DOCUMENTS:
{json.dumps(income_docs, indent=2)}

INSTRUCTIONS:
1. Review all paystubs, W2 documents, and 1099-R forms provided
2. Apply the Freddie Mac guidelines above for income calculation:
   - For paystubs: Calculate year-to-date average if multiple paystubs available
   - For W2s: Use most recent year's income divided by 12 for monthly amount
   - For 1099-R (pension/retirement): Use gross distribution divided by 12 for monthly amount
   - Consider consistency between paystubs, W2s, and 1099-R forms
   - Account for pay frequency (weekly, bi-weekly, semi-monthly, monthly)
   - Include base pay, overtime, bonuses, commissions (with 2-year average if applicable)
   - Include pension/retirement income from 1099-R forms
   - Follow the specific requirements in the guidelines above (2-year history, continuance, etc.)
3. Calculate total monthly gross income
4. Provide detailed methodology showing how you arrived at the calculation and which Freddie Mac rules you followed

Return ONLY a JSON object with this structure (no markdown, no code blocks):
{{
  "monthly_gross_income": <number>,
  "calculation_methodology": {{
    "paystubs_analysis": "<detailed explanation of paystub calculations>",
    "w2_analysis": "<detailed explanation of W2 calculations>",
    "reconciliation": "<how paystubs and W2s reconcile or any discrepancies>",
    "income_components": {{
      "base_salary": <number>,
      "overtime": <number>,
      "bonus": <number>,
      "commission": <number>,
      "other": <number>
    }},
    "pay_frequency": "<weekly|bi-weekly|semi-monthly|monthly>",
    "calculation_steps": [
      "<step 1>",
      "<step 2>",
      "..."
    ]
  }},
  "confidence_level": "<high|medium|low>",
  "notes": "<any additional notes or concerns>"
}}"""

    print("\n" + "="*80)
    print(f"INCOME ANALYSIS RUN {run_number} - LOAN {loan_id}")
    print("="*80)
    print(f"Analyzing {len(income_docs)} income documents...")
    
    try:
        response = await client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage underwriter specializing in income analysis. You follow Fannie Mae and Freddie Mac guidelines for income calculation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        print(f"\n>> RUN {run_number} COMPLETE - Monthly Gross Income: ${result.get('monthly_gross_income', 0):,.2f}")
        
        return result
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return {"error": str(e)}


def save_analysis(result, loan_id, run_number=1):
    """Save the income analysis result to a JSON file."""
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"income_analysis_{loan_id}_run{run_number}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    print(f">> Run {run_number} saved to: {output_file}")
    return output_file


def create_html_report(loan_id):
    """Create HTML report from the consistency test results."""
    summary_file = Path(f"reports/income_analysis_consistency_{loan_id}.json")
    
    if not summary_file.exists():
        print(f"Error: {summary_file} not found")
        return
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    stats = summary.get('statistics', {})
    if not stats:
        print("No statistics available")
        return
    
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
    
    # Group results by income amount to identify distinct methodologies
    income_groups = {}
    for result in summary['results']:
        if 'error' not in result:
            income = result['monthly_gross_income']
            if income not in income_groups:
                income_groups[income] = []
            income_groups[income].append(result)
    
    # Sort groups by frequency (most common first)
    sorted_income_groups = sorted(income_groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Get highest and lowest runs
    max_run_num = stats.get('max_run_number', 1)
    min_run_num = stats.get('min_run_number', 1)
    max_run = summary['results'][max_run_num - 1]
    min_run = summary['results'][min_run_num - 1]
    
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
        .run-header.max {{ background-color: #27ae60; }}
        .run-header.min {{ background-color: #e74c3c; }}
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
        .documents-list {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 15px 0; }}
        .documents-list h4 {{ margin-top: 0; color: #856404; }}
        .documents-list ul {{ margin: 5px 0; padding-left: 20px; }}
        .all-runs {{ background-color: #e8f4f8; padding: 10px; border-radius: 5px; margin: 15px 0; }}
        .all-runs table {{ width: 100%; border-collapse: collapse; }}
        .all-runs th {{ background-color: #3498db; color: white; padding: 8px; text-align: left; }}
        .all-runs td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .all-runs tr:hover {{ background-color: white; }}
    </style>
</head>
<body>
    <h1>Income Analysis Consistency Test Report</h1>
    <h2>Loan ID: {summary['loan_id']} | {summary['num_runs']} Test Runs (Async)</h2>
    
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
                <div class='stat-label'>Minimum (Run {min_run_num})</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value'>${stats['max_income']:,.2f}</div>
                <div class='stat-label'>Maximum (Run {max_run_num})</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value variance-{variance_class}'>{stats['variance_percentage']:.2f}%</div>
                <div class='stat-label'>Variance (Consistency)</div>
            </div>
        </div>
        
        <div class='all-runs'>
            <h4>All Run Results</h4>
            <table>
                <tr>
                    <th>Run #</th>
                    <th>Monthly Income</th>
                    <th>Confidence</th>
                    <th>Pay Frequency</th>
                </tr>
"""
    
    for result in summary['results']:
        if 'error' not in result:
            html += f"""                <tr>
                    <td>Run {result['run_number']}</td>
                    <td>${result['monthly_gross_income']:,.2f}</td>
                    <td><span class='confidence-{result['confidence_level']}'>{result['confidence_level'].upper()}</span></td>
                    <td>{result['calculation_methodology']['pay_frequency']}</td>
                </tr>
"""
    
    html += """            </table>
        </div>
    </div>
"""
    
    # Add section describing each distinct methodology
    html += f"""    <div class='overview'>
        <h3>Distinct Calculation Methodologies</h3>
        <p>The model produced <strong>{len(sorted_income_groups)} different income calculations</strong> across {summary['num_runs']} runs. Below are the methodologies ordered by frequency:</p>
    </div>
"""
    
    # Add detailed analysis for each distinct methodology (ordered by frequency)
    for method_num, (income, runs) in enumerate(sorted_income_groups, 1):
        frequency = len(runs)
        frequency_pct = (frequency / summary['num_runs']) * 100
        run_numbers = [r['run_number'] for r in runs]
        run_numbers_str = ", ".join([f"#{n}" for n in run_numbers])
        
        # Use the first run with this income as the representative example
        representative_run = runs[0]
        methodology = representative_run['calculation_methodology']
        income_comp = methodology['income_components']
        
        # Determine header color based on frequency rank
        if method_num == 1:
            header_class = "max"  # Green for most frequent
            frequency_label = "MOST FREQUENT"
        elif method_num == len(sorted_income_groups):
            header_class = "min"  # Red for least frequent
            frequency_label = "LEAST FREQUENT"
        else:
            header_class = ""
            frequency_label = f"METHOD {method_num}"
        
        html += f"""    <div class='run-section'>
        <div class='run-header {header_class}'>Method {method_num}: ${income:,.2f} - {frequency_label} ({frequency}/{summary['num_runs']} runs = {frequency_pct:.1f}%)</div>
        <p><strong>Occurred in runs:</strong> {run_numbers_str}</p>
        
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
            <p>{representative_run.get('notes', 'No additional notes')}</p>
        </div>
    </div>
"""
    
    # Add detailed analysis for highest and lowest runs (if different from methodologies already shown)
    html += """    <div class='overview'>
        <h3>Extreme Results Detail</h3>
        <p>Below are the specific runs that produced the highest and lowest income calculations:</p>
    </div>
"""
    
    for run_data, run_label, header_class in [(max_run, f"HIGHEST INCOME - Run {max_run_num}", "max"), 
                                                (min_run, f"LOWEST INCOME - Run {min_run_num}", "min")]:
        methodology = run_data['calculation_methodology']
        income_comp = methodology['income_components']
        
        html += f"""    <div class='run-section'>
        <div class='run-header {header_class}'>{run_label} - ${run_data['monthly_gross_income']:,.2f} <span class='confidence-{run_data['confidence_level']}'>{run_data['confidence_level'].upper()} CONFIDENCE</span></div>
        
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
            <p>{run_data.get('notes', 'No additional notes')}</p>
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
    
    print(f"\n>> HTML report created: {output_file}")
    print(f"\nSummary:")
    print(f"  Average Income: ${stats['average_income']:,.2f}")
    print(f"  Variance: {stats['variance_percentage']:.2f}%")
    print(f"  Consistency: {consistency_rating}")


def run_consistency_test(loan_id, num_runs=3):
    """
    Run the income analysis multiple times to test consistency.
    
    Args:
        loan_id: The loan identifier
        num_runs: Number of times to run the analysis
    """
    asyncio.run(run_consistency_test_async(loan_id, num_runs))


async def run_consistency_test_async(loan_id, num_runs=3):
    """
    Run the income analysis multiple times asynchronously to test consistency.
    
    Args:
        loan_id: The loan identifier
        num_runs: Number of times to run the analysis
    """
    print("\n" + "="*80)
    print(f"INCOME ANALYSIS CONSISTENCY TEST (ASYNC)")
    print(f"Loan ID: {loan_id}")
    print(f"\nNumber of Runs: {num_runs}")
    print("="*80)
    
    # Load income documents once using intelligent filtering
    income_docs = await filter_income_documents_by_guidelines(loan_id)
    
    if not income_docs:
        print("\nNo paystub or W2 documents found!")
        return
    
    print(f"\nFound {len(income_docs)} income documents:")
    for doc in income_docs:
        print(f"  - {doc['document_type'].upper()}: {doc['file_name']}")
    
    print(f"\n>> Starting {num_runs} parallel analyses...")
    
    # Run analysis multiple times in parallel
    tasks = []
    for i in range(1, num_runs + 1):
        tasks.append(analyze_income(income_docs, loan_id, run_number=i))
    
    results = await asyncio.gather(*tasks)
    
    # Save individual results
    for i, result in enumerate(results, 1):
        result['run_number'] = i
        result['loan_id'] = loan_id
        result['documents_analyzed'] = len(income_docs)
        save_analysis(result, loan_id, run_number=i)
    
    # Summary of consistency
    print("\n" + "="*80)
    print("CONSISTENCY SUMMARY")
    print("="*80)
    
    incomes = [r.get('monthly_gross_income', 0) for r in results if 'error' not in r]
    
    if incomes:
        print(f"\nMonthly Gross Income Results:")
        for i, income in enumerate(incomes, 1):
            confidence = results[i-1].get('confidence_level', 'unknown')
            print(f"  Run {i}: ${income:,.2f} ({confidence} confidence)")
        
        avg_income = sum(incomes) / len(incomes)
        min_income = min(incomes)
        max_income = max(incomes)
        variance = max_income - min_income
        variance_pct = (variance / avg_income * 100) if avg_income > 0 else 0
        
        print(f"\nStatistics:")
        print(f"  Average: ${avg_income:,.2f}")
        print(f"  Min: ${min_income:,.2f}")
        print(f"  Max: ${max_income:,.2f}")
        print(f"  Variance: ${variance:,.2f} ({variance_pct:.2f}%)")
        print(f"  Consistency: {'HIGH' if variance_pct < 1 else 'MEDIUM' if variance_pct < 5 else 'LOW'}")
        
        # Identify highest and lowest runs
        min_idx = incomes.index(min_income)
        max_idx = incomes.index(max_income)
        
        print(f"\n  Highest Income: Run {max_idx + 1} - ${max_income:,.2f}")
        print(f"  Lowest Income: Run {min_idx + 1} - ${min_income:,.2f}")
    
    # Save summary
    summary = {
        'loan_id': loan_id,
        'num_runs': num_runs,
        'documents_analyzed': len(income_docs),
        'income_documents': [{'type': d['document_type'], 'file_name': d['file_name']} for d in income_docs],
        'results': results,
        'statistics': {
            'average_income': avg_income,
            'min_income': min_income,
            'max_income': max_income,
            'variance': variance,
            'variance_percentage': variance_pct,
            'min_run_number': min_idx + 1,
            'max_run_number': max_idx + 1
        } if incomes else None
    }
    
    summary_file = Path("reports") / f"income_analysis_consistency_{loan_id}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n>> Summary saved to: {summary_file}")
    print(f"\n>> Creating HTML report...")
    
    # Create HTML report automatically
    create_html_report(loan_id)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python income_analysis_agent.py <loan_id> [num_runs]")
        print("Example: python income_analysis_agent.py 1000179167 3")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    num_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    run_consistency_test(loan_id, num_runs)
