"""
Timeline Analysis Agent

This agent analyzes TWO DISTINCT temporal dimensions in loan underwriting data:

1. UNDERWRITING TIMELINE (Process Timeline):
   - When documents were created/collected during the underwriting process
   - Examples: When credit was pulled, when appraisal was done, when application was signed
   - This shows the PROCESS of underwriting - the sequence of events in loan origination
   
2. DATA TIMELINE (Historical/Content Timeline):
   - Temporal data WITHIN the documents that describes historical events
   - Examples: When trade lines were opened, when paystubs were issued, when payments were made
   - This shows the BORROWER'S HISTORY - their financial evolution over time

The distinction is critical:
- Credit report PULLED on 8/20/2025 (underwriting timeline)
- But contains trade lines OPENED in 2005, 2010, 2018 (data timeline)
- Paystub DATED 3/25/2025 (data timeline)
- But COLLECTED/USED for application on 8/20/2025 (underwriting timeline)

This agent will analyze both dimensions to provide comprehensive temporal insights.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import re

# Azure OpenAI setup
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

DEPLOYMENT_NAME = deployment


def load_all_loan_json_files(loan_id: str) -> Dict[str, Dict]:
    """Load all JSON files for a given loan."""
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        print(f"JSON directory not found: {json_dir}")
        return {}
    
    json_files = {}
    for json_file in json_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                json_files[json_file.stem] = data
        except Exception as e:
            print(f"Error loading {json_file.name}: {e}")
    
    return json_files


def create_agent_prompt(json_data: Dict[str, Dict]) -> str:
    """Create a comprehensive prompt for the timeline analysis agent."""
    
    prompt = f"""You are a Timeline Analysis Agent specializing in mortgage loan underwriting.

You have been provided with {len(json_data)} JSON documents from a loan file. Your task is to analyze TWO DISTINCT temporal dimensions:

## DIMENSION 1: UNDERWRITING TIMELINE (Process Timeline)
This is the sequence of events during the loan origination/underwriting process.
- When was the loan application submitted?
- When was the credit report pulled?
- When was the appraisal ordered/completed?
- When were various documents collected?
- When was the loan approved/closed?

Look for fields like:
- "date", "created_date", "document_date", "report_date"
- "application_date", "appraisal_date", "closing_date"
- Any date that indicates WHEN the document was created or the event occurred

## DIMENSION 2: DATA TIMELINE (Historical/Content Timeline)
This is the temporal data WITHIN documents that describes historical events and patterns.

Examples:
- CREDIT REPORT: Trade lines with opening dates, payment history dates, last activity dates
  * A credit report pulled on 8/20/2025 might contain:
    - Mortgage opened 2018-03-15
    - Credit card opened 2010-06-20
    - Auto loan opened 2022-11-03
  * These are HISTORICAL dates that show the borrower's credit evolution
  
- PAYSTUBS: Issue dates showing income over time
  * Paystubs from March, July, August showing income progression
  
- BANK STATEMENTS: Transaction dates, statement periods
  * Multiple months showing deposit patterns
  
- W-2s: Tax year dates showing multi-year income history
  
- APPRAISAL: Property purchase date, improvement dates
  
- MORTGAGE STATEMENTS: Payment history, loan origination date

Look for fields like:
- "trade_lines", "accounts", "payment_history"
- "opened_date", "purchase_date", "origination_date"
- "pay_period", "statement_period", "tax_year"
- Any date that describes WHEN something in the past happened

## YOUR ANALYSIS SHOULD INCLUDE:

### Part 1: Underwriting Process Timeline
1. Chronological sequence of loan origination events
2. Key milestones (application, credit pull, appraisal, approval, closing)
3. Process speed metrics (days between milestones)
4. Document collection timeline
5. Document freshness at decision time (were documents recent or stale?)

### Part 2: Historical Data Timeline
1. Borrower's credit history evolution
   - When trade lines were established
   - Payment patterns over time
   - Recent vs historical credit behavior
   
2. Income progression
   - Multiple paystubs showing income trends
   - Year-over-year W-2 comparisons
   - Income stability or changes
   
3. Property/asset history
   - When properties were purchased
   - Improvement dates
   - Asset accumulation timeline
   
4. Financial obligation evolution
   - When debts were taken on
   - Payment history patterns
   - Debt payoff timeline

### Part 3: Critical Insights
1. Document freshness issues
   - Were any documents too old at underwriting time?
   - Did income/employment need verification updates?
   
2. Timeline discrepancies
   - Gaps between document dates and usage
   - Inconsistencies in reported dates
   
3. Borrower financial trajectory
   - Improving, stable, or declining financial picture?
   - Recent changes vs long-term patterns
   
4. Underwriting efficiency
   - How quickly was the loan processed?
   - Were there delays or bottlenecks?

## IMPORTANT DISTINCTIONS:
- A credit report PULLED on 8/20/2025 is an UNDERWRITING TIMELINE event
- Trade lines OPENED in 2005, 2010, 2018 within that report are DATA TIMELINE events
- A paystub DATED 3/25/2025 is a DATA TIMELINE event
- That paystub being USED in an application on 8/20/2025 is an UNDERWRITING TIMELINE event

Provide a comprehensive analysis that clearly distinguishes these two temporal dimensions.

## THE JSON DOCUMENTS:

"""
    
    # Add each JSON document
    for doc_name, doc_data in json_data.items():
        prompt += f"\n\n=== DOCUMENT: {doc_name} ===\n"
        prompt += json.dumps(doc_data, indent=2)
        prompt += "\n" + "="*80
    
    return prompt


def run_timeline_analysis_agent(loan_id: str) -> str:
    """Run the timeline analysis agent on all loan documents."""
    
    print(f"\n{'='*80}")
    print(f"TIMELINE ANALYSIS AGENT - Loan {loan_id}")
    print(f"{'='*80}\n")
    
    # Load all JSON files
    print("Loading JSON documents...")
    json_data = load_all_loan_json_files(loan_id)
    
    if not json_data:
        return "No JSON files found to analyze."
    
    print(f"Loaded {len(json_data)} JSON documents\n")
    
    # Create the prompt
    print("Creating analysis prompt...")
    prompt = create_agent_prompt(json_data)
    
    print(f"Prompt size: {len(prompt):,} characters")
    print(f"Estimated tokens: ~{len(prompt)//4:,}\n")
    
    # Call Azure OpenAI
    print("Calling Azure OpenAI agent...")
    print("This may take a minute due to the large amount of data...\n")
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage underwriting analyst specializing in temporal analysis and timeline reconstruction. You excel at distinguishing between process timelines and data timelines."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=16000  # Large response for comprehensive analysis
        )
        
        analysis = response.choices[0].message.content
        
        print(f"\n{'='*80}")
        print("AGENT ANALYSIS COMPLETE")
        print(f"{'='*80}\n")
        
        return analysis
        
    except Exception as e:
        error_msg = f"Error calling Azure OpenAI: {e}"
        print(error_msg)
        return error_msg


def save_analysis_report(loan_id: str, analysis: str):
    """Save the analysis to a report file."""
    report_dir = Path(f"reports")
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"timeline_analysis_{loan_id}_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Timeline Analysis Report\n\n")
        f.write(f"**Loan ID:** {loan_id}\n")
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        f.write(analysis)
    
    print(f"\nReport saved to: {report_file}")
    return report_file


if __name__ == "__main__":
    loan_id = "1000182227"
    
    # Run the analysis
    analysis_result = run_timeline_analysis_agent(loan_id)
    
    # Print the result
    print(analysis_result)
    
    # Save to file
    report_file = save_analysis_report(loan_id, analysis_result)
    print(f"\n{'='*80}")
    print(f"Analysis complete! Check {report_file} for the full report.")
    print(f"{'='*80}\n")
