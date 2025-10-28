# -*- coding: utf-8 -*-
"""
Income Analysis Agent
Tests model consistency in calculating monthly income from paystubs and W2s
using generally accepted mortgage underwriting standards.
"""

import json
import sys
import io
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables
load_dotenv()


def load_employment_history(loan_id):
    """
    Load the employment history report if available.
    
    Args:
        loan_id: The loan identifier
        
    Returns:
        String containing employment history markdown, or empty string if not found
    """
    employment_history_file = Path(f"loan_docs/{loan_id}/employment_history/employment_history.md")
    
    if employment_history_file.exists():
        try:
            with open(employment_history_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not load employment history: {e}")
            return ""
    else:
        print(f"Note: No employment history found for loan {loan_id}. Run employment_history_agent.py first for better results.")
        return ""


def load_freddie_mac_guidelines():
    """
    Load the Freddie Mac income underwriting decision tree and edge cases.
    
    Returns:
        String containing decision tree and edge cases for income calculation
    """
    guidelines_file = Path("guidelines/income_underwriting_decision_tree.json")
    edge_cases_file = Path("guidelines/income_edge_cases_and_clarifications.json")
    
    rules_text = ""
    
    # Load main decision tree
    if guidelines_file.exists():
        try:
            with open(guidelines_file, 'r', encoding='utf-8') as f:
                decision_tree = json.load(f)
            
            # Format the decision tree into a readable string
            rules_text += "FREDDIE MAC INCOME UNDERWRITING DECISION TREE:\n\n"
            rules_text += f"Title: {decision_tree.get('metadata', {}).get('title', 'Unknown')}\n"
            rules_text += f"Description: {decision_tree.get('metadata', {}).get('description', 'Unknown')}\n"
            rules_text += f"Usage: {decision_tree.get('metadata', {}).get('usage', 'Unknown')}\n\n"
            
            # Convert the structured decision tree to text format
            rules_text += json.dumps(decision_tree, indent=2)
            rules_text += "\n\n"
            
        except Exception as e:
            print(f"Warning: Could not load decision tree: {e}")
    
    # Load edge cases and clarifications
    if edge_cases_file.exists():
        try:
            with open(edge_cases_file, 'r', encoding='utf-8') as f:
                edge_cases = json.load(f)
            
            rules_text += "="*80 + "\n"
            rules_text += "INCOME UNDERWRITING EDGE CASES AND CLARIFICATIONS\n"
            rules_text += "="*80 + "\n\n"
            rules_text += f"Title: {edge_cases.get('metadata', {}).get('title', 'Unknown')}\n"
            rules_text += f"Description: {edge_cases.get('metadata', {}).get('description', 'Unknown')}\n"
            rules_text += f"Version: {edge_cases.get('metadata', {}).get('version', 'Unknown')}\n"
            rules_text += f"Last Updated: {edge_cases.get('metadata', {}).get('last_updated', 'Unknown')}\n\n"
            rules_text += "IMPORTANT: These edge cases supplement the decision tree above. Use them to handle\n"
            rules_text += "scenarios not explicitly covered in the main decision tree.\n\n"
            
            # Convert edge cases to text format
            rules_text += json.dumps(edge_cases, indent=2)
            
        except Exception as e:
            print(f"Warning: Could not load edge cases: {e}")
    
    return rules_text


def load_income_documents(loan_id):
    """
    Load semantic JSON files that have been pre-classified as income-relevant.
    
    IMPORTANT: Documents must be pre-classified first using:
        python pipeline/classify_income_documents.py <loan_id>
    
    This function only loads documents already marked with 'income_verification_relevant' flag.
    If no documents are found with this flag, you need to run the classification pipeline step first.
    
    Args:
        loan_id: The loan identifier
        
    Returns:
        List of document objects relevant for income verification
        
    Raises:
        FileNotFoundError: If semantic_json directory doesn't exist
        RuntimeError: If no classified documents are found (need to run classification first)
    """
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        raise FileNotFoundError(f"Semantic JSON directory does not exist: {semantic_dir}")
    
    print(f"\n>> Loading pre-classified income documents for loan {loan_id}...")
    
    income_docs = []
    total_docs = 0
    unclassified_docs = 0
    
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            total_docs += 1
            
            # Check if this document has been classified
            if 'income_verification_relevant' not in doc:
                unclassified_docs += 1
                continue
            
            # Check if marked as income verification relevant
            if doc.get('income_verification_relevant', {}).get('is_relevant', False):
                doc_obj = {
                    'file_id': doc.get('metadata', {}).get('FileId'),
                    'file_name': doc.get('metadata', {}).get('FileName'),
                    'document_type': doc.get('semantic_content', {}).get('document_type', 'unknown'),
                    'upload_date': doc.get('metadata', {}).get('FileUploadDate'),
                    'semantic_content': doc.get('semantic_content', {}),
                    'inclusion_reason': doc['income_verification_relevant'].get('reason', 'Previously classified')
                }
                income_docs.append(doc_obj)
                
        except Exception as e:
            continue
    
    if unclassified_docs > 0:
        print(f"\n>> WARNING: Found {unclassified_docs} unclassified documents out of {total_docs} total")
        print(f">> Run classification first: python pipeline/classify_income_documents.py {loan_id}")
        raise RuntimeError(f"Documents not classified. Run: python pipeline/classify_income_documents.py {loan_id}")
    
    if not income_docs:
        print(f"\n>> ERROR: No income-relevant documents found for loan {loan_id}")
        print(f">> Total documents: {total_docs}")
        print(f">> Run classification first: python pipeline/classify_income_documents.py {loan_id}")
        raise RuntimeError(f"No income documents found. Run: python pipeline/classify_income_documents.py {loan_id}")
    
    print(f">> Loaded {len(income_docs)} income-relevant documents (from {total_docs} total)")
    
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
    
    # Load employment history if available
    employment_history = load_employment_history(loan_id)
    employment_context = ""
    if employment_history:
        employment_context = f"""
{'='*80}
EMPLOYMENT HISTORY REPORT
{'='*80}

(This report provides a comprehensive timeline of the borrower's employment based on
all income verification documents. Use it to understand employment continuity, status
changes, employer name variations, income sources, and scenario classification.)

{employment_history}

{'='*80}
"""
    
    # Create prompt with income documents
    prompt = f"""You are a mortgage underwriting income analyst. Analyze the following income documents and calculate the borrower's monthly income using Freddie Mac guidelines.

{guidelines}
{employment_context}

INCOME DOCUMENTS:
{json.dumps(income_docs, indent=2)}

CRITICAL INSTRUCTIONS:

1. Follow the Freddie Mac Income Underwriting Decision Tree provided above
   - Start at the ROOT node and traverse based on the borrower's situation
   - Answer each decision node's question based on the documents provided
   - Continue until you reach a CALCULATE or REJECT outcome
   - Apply the exact formula specified in the leaf node

2. Calculate qualifying monthly gross income using ONLY the documents provided - you have complete information

3. STRICT EVIDENCE REQUIREMENT:
   - If the decision tree requires specific documentation (e.g., "two-year history"), you MUST see that documentation in the provided files
   - If documentation is insufficient per the decision tree requirements → exclude that income component (set to $0)
   - DO NOT propose conditional/provisional income "subject to" obtaining additional documents
   - DO NOT say income is "pending verification" - either it meets requirements (include it) or it doesn't (exclude it)

4. Your monthly_gross_income is the FINAL qualifying amount based on applying the decision tree to available evidence

5. In your response, document the decision path you followed through the tree (e.g., "ROOT → EMPLOYED_ROOT → EMPLOYED_HISTORY → EARNINGS_TYPE → BASE_NON_FLUCTUATING_CALC")

Return ONLY a JSON object with this structure (no markdown, no code blocks):
{{
  "monthly_gross_income": <number>,
  "calculation_methodology": {{
    "decision_path": "<node path through decision tree>",
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
    ],
    "freddie_mac_compliance": {{
      "base_income_rule_applied": "<which decision tree node/outcome>",
      "variable_income_treatment": "<included with 2yr avg | excluded - insufficient history>",
      "documentation_gaps": "<list any income sources visible but not usable due to lack of required documentation>"
    }}
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
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"income_analysis_run{run_number}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    print(f">> Run {run_number} saved to: {output_file}")
    return output_file


def create_html_report(loan_id, run_suffix="all"):
    """Create HTML report from the consistency test results.
    
    Args:
        loan_id: The loan identifier
        run_suffix: Suffix for the filename (e.g., "runs1-5", "all")
    """
    summary_file = Path(f"loan_docs/{loan_id}/income_analysis/consistency_summary_{run_suffix}.json")
    
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
    <h2>Loan ID: {summary['loan_id']} | {summary.get('num_runs', summary.get('total_runs', 0))} Test Runs (Async)</h2>
    
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
    num_runs = summary.get('num_runs', summary.get('total_runs', 0))
    html += f"""    <div class='overview'>
        <h3>Distinct Calculation Methodologies</h3>
        <p>The model produced <strong>{len(sorted_income_groups)} different income calculations</strong> across {num_runs} runs. Below are the methodologies ordered by frequency:</p>
    </div>
"""
    
    # Add detailed analysis for each distinct methodology (ordered by frequency)
    for method_num, (income, runs) in enumerate(sorted_income_groups, 1):
        frequency = len(runs)
        frequency_pct = (frequency / num_runs) * 100
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
        <div class='run-header {header_class}'>Method {method_num}: ${income:,.2f} - {frequency_label} ({frequency}/{num_runs} runs = {frequency_pct:.1f}%)</div>
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
        methodology = run_data.get('calculation_methodology', {})
        income_comp = methodology.get('income_components', {
            'base_salary': 0,
            'overtime': 0,
            'bonus': 0,
            'commission': 0,
            'other': 0
        })
        
        html += f"""    <div class='run-section'>
        <div class='run-header {header_class}'>{run_label} - ${run_data.get('monthly_gross_income', 0):,.2f} <span class='confidence-{run_data.get('confidence_level', 'unknown')}'>{run_data.get('confidence_level', 'UNKNOWN').upper()} CONFIDENCE</span></div>
        
        <div class='income-breakdown'>
            <div class='income-item'>
                <label>Base Salary</label>
                <value>${income_comp.get('base_salary', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Overtime</label>
                <value>${income_comp.get('overtime', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Bonus</label>
                <value>${income_comp.get('bonus', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Commission</label>
                <value>${income_comp.get('commission', 0):,.2f}</value>
            </div>
        </div>
        
        <div class='methodology'>
            <h4>Pay Frequency: {methodology.get('pay_frequency', 'Unknown')}</h4>
        </div>
        
        <div class='methodology'>
            <h4>Paystubs Analysis</h4>
            <p>{methodology.get('paystubs_analysis', 'N/A')}</p>
        </div>
        
        <div class='methodology'>
            <h4>W2 Analysis</h4>
            <p>{methodology.get('w2_analysis', 'N/A')}</p>
        </div>
        
        <div class='methodology'>
            <h4>Reconciliation</h4>
            <p>{methodology.get('reconciliation', 'N/A')}</p>
        </div>
        
        <div class='methodology'>
            <h4>Calculation Steps</h4>
            <div class='steps'>
                <ol>
"""
        
        for step in methodology.get('calculation_steps', []):
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
        <p><strong>Interpretation:</strong> The AI model produced {num_runs} different monthly income calculations ranging from ${stats['min_income']:,.2f} to ${stats['max_income']:,.2f}. This variance of {stats['variance_percentage']:.2f}% indicates {interpretation}.</p>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    output_file = Path(f"loan_docs/{loan_id}/income_analysis/consistency_report_{run_suffix}.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f">> HTML report created: {output_file}")
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
    
    # Check for existing run files and determine starting run number
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    existing_runs = 0
    if output_dir.exists():
        existing_files = list(output_dir.glob("income_analysis_run*.json"))
        print(f"DEBUG: Found {len(existing_files)} existing files in {output_dir}")
        if existing_files:
            # Extract run numbers from filenames
            run_numbers = []
            for f in existing_files:
                try:
                    # Extract number from "income_analysis_run{N}.json"
                    num = int(f.stem.replace("income_analysis_run", ""))
                    run_numbers.append(num)
                    print(f"DEBUG: Extracted run number {num} from {f.name}")
                except ValueError as e:
                    print(f"DEBUG: Could not extract number from {f.name}: {e}")
                    continue
            if run_numbers:
                existing_runs = max(run_numbers)
                print(f"Found {len(run_numbers)} existing run(s) - starting from run {existing_runs + 1}")
    else:
        print(f"DEBUG: Output directory does not exist: {output_dir}")
    
    # Load income documents (must be pre-classified by pipeline step)
    income_docs = load_income_documents(loan_id)
    
    if not income_docs:
        print("\nNo paystub or W2 documents found!")
        return
    
    print(f"\nFound {len(income_docs)} income documents:")
    for doc in income_docs:
        print(f"  - {doc['document_type'].upper()}: {doc['file_name']}")
    
    print(f"\n>> Starting {num_runs} parallel analyses...")
    
    # Run analysis multiple times in parallel with auto-incremented run numbers
    tasks = []
    for i in range(1, num_runs + 1):
        actual_run_number = existing_runs + i
        tasks.append(analyze_income(income_docs, loan_id, run_number=actual_run_number))
    
    results = await asyncio.gather(*tasks)
    
    # Save individual results
    for i, result in enumerate(results, 1):
        actual_run_number = existing_runs + i
        result['run_number'] = actual_run_number
        result['loan_id'] = loan_id
        result['documents_analyzed'] = len(income_docs)
        save_analysis(result, loan_id, run_number=actual_run_number)
    
    # Summary of consistency
    print("\n" + "="*80)
    print("CONSISTENCY SUMMARY")
    print("="*80)
    
    incomes = [r.get('monthly_gross_income', 0) for r in results if 'error' not in r]
    
    if incomes:
        print(f"\nMonthly Gross Income Results (Runs {existing_runs + 1}-{existing_runs + num_runs}):")
        for i, income in enumerate(incomes, 1):
            actual_run_number = existing_runs + i
            confidence = results[i-1].get('confidence_level', 'unknown')
            print(f"  Run {actual_run_number}: ${income:,.2f} ({confidence} confidence)")
        
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
    
    # Save summary for this batch
    summary = {
        'loan_id': loan_id,
        'num_runs': num_runs,
        'run_range': f"{existing_runs + 1}-{existing_runs + num_runs}",
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
    
    summary_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    # Save batch-specific summary
    batch_summary_file = summary_dir / f"consistency_summary_runs{existing_runs + 1}-{existing_runs + num_runs}.json"
    with open(batch_summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n>> Batch summary saved to: {batch_summary_file}")
    
    # Create batch-specific HTML report
    print(f"\n>> Creating batch HTML report...")
    create_html_report(loan_id, f"runs{existing_runs + 1}-{existing_runs + num_runs}")
    
    # Now create comprehensive "ALL" summary using all run files
    print(f"\n>> Creating comprehensive summary from all runs...")
    all_run_files = sorted(summary_dir.glob("income_analysis_run*.json"), 
                           key=lambda x: int(x.stem.replace("income_analysis_run", "")))
    
    if all_run_files:
        all_results = []
        for run_file in all_run_files:
            with open(run_file, 'r', encoding='utf-8') as f:
                all_results.append(json.load(f))
        
        # Calculate statistics across all runs
        all_incomes = [r.get('monthly_gross_income', 0) for r in all_results if 'error' not in r]
        
        if all_incomes:
            all_avg_income = sum(all_incomes) / len(all_incomes)
            all_min_income = min(all_incomes)
            all_max_income = max(all_incomes)
            all_variance = all_max_income - all_min_income
            all_variance_pct = (all_variance / all_avg_income * 100) if all_avg_income > 0 else 0
            
            all_min_idx = all_incomes.index(all_min_income)
            all_max_idx = all_incomes.index(all_max_income)
            
            # Calculate confidence-weighted metrics
            confidence_weights = {'high': 1.0, 'medium': 0.7, 'low': 0.4}
            
            weighted_sum = 0
            weight_total = 0
            high_conf_incomes = []
            confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
            
            for result in all_results:
                if 'error' not in result:
                    income = result.get('monthly_gross_income', 0)
                    confidence = result.get('confidence_level', 'medium').lower()
                    
                    # Track confidence distribution
                    if confidence in confidence_counts:
                        confidence_counts[confidence] += 1
                    
                    # Calculate weighted sum
                    weight = confidence_weights.get(confidence, 0.7)
                    weighted_sum += income * weight
                    weight_total += weight
                    
                    # Collect high-confidence incomes
                    if confidence == 'high':
                        high_conf_incomes.append(income)
            
            # Calculate confidence-weighted average
            confidence_weighted_avg = weighted_sum / weight_total if weight_total > 0 else all_avg_income
            
            # Calculate high-confidence-only average
            high_confidence_avg = sum(high_conf_incomes) / len(high_conf_incomes) if high_conf_incomes else all_avg_income
            
            # Determine overall confidence in result
            high_pct = (confidence_counts['high'] / len(all_results) * 100) if all_results else 0
            if high_pct >= 80:
                confidence_in_result = "high"
                rationale = f"{confidence_counts['high']}/{len(all_results)} runs achieved high confidence with {all_variance_pct:.2f}% variance"
                recommendation = "USE authoritative_income value - high confidence with strong consistency" if all_variance_pct < 1 else "USE authoritative_income value - high confidence but review variance"
            elif high_pct >= 50:
                confidence_in_result = "medium"
                rationale = f"{confidence_counts['high']}/{len(all_results)} runs achieved high confidence; {confidence_counts['medium']} medium, {confidence_counts['low']} low"
                recommendation = "REVIEW authoritative_income value - moderate confidence, consider manual verification"
            else:
                confidence_in_result = "low"
                rationale = f"Only {confidence_counts['high']}/{len(all_results)} runs achieved high confidence; variance {all_variance_pct:.2f}%"
                recommendation = "MANUAL REVIEW REQUIRED - low confidence across runs or high variance detected"
            
            all_summary = {
                'loan_id': loan_id,
                'total_runs': len(all_results),
                'run_range': f"1-{len(all_results)}",
                'documents_analyzed': len(income_docs),
                'income_documents': [{'type': d['document_type'], 'file_name': d['file_name']} for d in income_docs],
                'results': all_results,
                'statistics': {
                    'average_income': all_avg_income,
                    'min_income': all_min_income,
                    'max_income': all_max_income,
                    'variance': all_variance,
                    'variance_percentage': all_variance_pct,
                    'min_run_number': all_min_idx + 1,
                    'max_run_number': all_max_idx + 1
                },
                'underwriter_decision': {
                    'authoritative_income': round(confidence_weighted_avg, 2),
                    'confidence_weighted_avg': round(confidence_weighted_avg, 2),
                    'high_confidence_only_avg': round(high_confidence_avg, 2),
                    'simple_average': round(all_avg_income, 2),
                    'confidence_distribution': confidence_counts,
                    'confidence_in_result': confidence_in_result,
                    'rationale': rationale,
                    'recommendation': recommendation
                }
            }
            
            # Save comprehensive "all runs" summary
            all_summary_file = summary_dir / "consistency_summary_all.json"
            with open(all_summary_file, 'w', encoding='utf-8') as f:
                json.dump(all_summary, f, indent=2)
            
            print(f">> Comprehensive summary (all {len(all_results)} runs) saved to: {all_summary_file}")
            
            # Print underwriter decision
            print(f"\n{'='*80}")
            print(f"UNDERWRITER DECISION")
            print(f"{'='*80}")
            decision = all_summary['underwriter_decision']
            print(f"  Authoritative Income: ${decision['authoritative_income']:,.2f}")
            print(f"  Confidence in Result: {decision['confidence_in_result'].upper()}")
            print(f"  Confidence Distribution: {decision['confidence_distribution']['high']} high, {decision['confidence_distribution']['medium']} medium, {decision['confidence_distribution']['low']} low")
            print(f"  Rationale: {decision['rationale']}")
            print(f"  Recommendation: {decision['recommendation']}")
            print(f"\n  Comparison:")
            print(f"    Simple Average:        ${decision['simple_average']:,.2f}")
            print(f"    Confidence-Weighted:   ${decision['confidence_weighted_avg']:,.2f}")
            print(f"    High-Confidence Only:  ${decision['high_confidence_only_avg']:,.2f}")
            print(f"{'='*80}\n")
            
            # Create comprehensive HTML report
            create_html_report(loan_id, "all")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python income_analysis_agent.py <loan_id> [num_runs]")
        print("Example: python income_analysis_agent.py 1000179167 3")
        print("\nNOTE: Documents must be pre-classified first:")
        print("      python pipeline/classify_income_documents.py <loan_id>")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    num_runs = 3
    
    # Parse number of runs
    if len(sys.argv) > 2:
        try:
            num_runs = int(sys.argv[2])
        except ValueError:
            print(f"Warning: Invalid number of runs '{sys.argv[2]}', using default (3)")
    
    run_consistency_test(loan_id, num_runs)
