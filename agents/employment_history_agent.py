# -*- coding: utf-8 -*-
"""
Employment History Agent

Analyzes income verification documents to construct a chronological employment
history for all borrowers on a loan application.

Usage:
    python agents/employment_history_agent.py <loan_id>

Output:
    Creates loan_docs/<loan_id>/employment_history/employment_history.md
"""

import sys
import io

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_income_documents(loan_id):
    """
    Load all documents marked as income verification relevant.
    
    Args:
        loan_id: The loan identifier
        
    Returns:
        List of income verification documents with their semantic content
    """
    loan_dir = Path(f"loan_docs/{loan_id}")
    semantic_dir = loan_dir / "semantic_json"
    
    if not semantic_dir.exists():
        raise FileNotFoundError(f"Semantic JSON directory not found: {semantic_dir}")
    
    income_docs = []
    not_classified_count = 0
    
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            
            # Validate that doc is a dictionary
            if not isinstance(doc, dict):
                print(f"WARNING: Skipping {json_file.name} - loaded as {type(doc)} instead of dict")
                continue
            
            # Check if this document has been classified
            if 'income_verification_relevant' not in doc:
                not_classified_count += 1
                continue
                
            # Only include documents marked as income verification relevant
            if doc.get('income_verification_relevant', {}).get('is_relevant', False):
                income_docs.append({
                    'file_id': doc.get('metadata', {}).get('FileId'),
                    'file_name': doc.get('metadata', {}).get('FileName'),
                    'document_type': doc.get('semantic_content', {}).get('document_type', 'unknown'),
                    'semantic_content': doc.get('semantic_content', {}),
                    'metadata': doc.get('metadata', {})
                })
                
        except Exception as e:
            print(f"WARNING: Error loading {json_file.name}: {e}")
            continue
    
    if not_classified_count > 0:
        raise RuntimeError(
            f"\n{'='*80}\n"
            f"ERROR: Found {not_classified_count} documents without classification flags.\n"
            f"\n"
            f"Documents must be pre-classified before running employment history analysis.\n"
            f"Please run the classification pipeline first:\n"
            f"\n"
            f"  python pipeline/classify_income_documents.py {loan_id}\n"
            f"\n"
            f"Or to force re-classification:\n"
            f"\n"
            f"  python pipeline/classify_income_documents.py {loan_id} --refilter\n"
            f"{'='*80}\n"
        )
    
    if not income_docs:
        raise ValueError(f"No income verification documents found for loan {loan_id}")
    
    return income_docs


async def generate_employment_history(loan_id, income_docs):
    """
    Use LLM to analyze income documents and generate employment history.
    
    Args:
        loan_id: The loan identifier
        income_docs: List of income verification documents
        
    Returns:
        Dictionary containing employment history analysis
    """
    # Initialize Azure OpenAI client
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Prepare document summaries for the LLM
    doc_summaries = []
    for doc in income_docs:
        doc_summaries.append({
            'file_name': doc['file_name'],
            'document_type': doc['document_type'],
            'content': doc['semantic_content']
        })
    
    prompt = f"""You are analyzing income verification documents to construct a comprehensive employment history for all borrowers on this loan application.

INCOME VERIFICATION DOCUMENTS:
{json.dumps(doc_summaries, indent=2, default=str)}

YOUR TASK:
Create a detailed, chronological employment history report that includes:

1. **Borrower Identification**
   - How many borrowers are on this application?
   - Identify each borrower by name from the documents

2. **For Each Borrower, Create Employment Timeline:**
   - List all employers mentioned in chronological order
   - For each employer, document:
     * Employer name (note any name variations across documents)
     * Employment start date (if available)
     * Employment end date (if still employed, note "Current")
     * Position/title
     * Employment type (Full-Time, Part-Time, PRN, Contract, Self-Employed, etc.)
     * Any status changes at the same employer (e.g., PRN → Full-Time)
     * Income amounts documented (with source document type)

3. **Income Sources Summary:**
   - W-2 employment
   - Self-employment / business ownership
   - Rental income
   - Investment income
   - Other income sources

4. **Document Coverage:**
   - What time periods are covered by the available documents?
   - What types of documents verify each employment period? (paystubs, W-2s, VOE, offer letters, tax returns, etc.)

5. **Notable Patterns or Issues:**
   - Employment gaps
   - Job changes
   - Status changes at same employer
   - Multiple concurrent employments
   - Name variations for same employer
   - Inconsistencies across documents

**IMPORTANT GUIDELINES:**
- Be factual - only report what is explicitly documented
- Note date ranges clearly (use "Not specified" if dates aren't in documents)
- Flag employer name variations (e.g., "Care IV Inc" vs "Care4 Home Health")
- Distinguish between job changes and status changes at same employer
- Organize chronologically with most recent first
- If documents show conflicting information, note both versions
- Keep the tone professional and concise

Return your analysis as a JSON object with this structure:
{{
  "loan_id": "{loan_id}",
  "analysis_date": "{datetime.now().isoformat()}",
  "number_of_borrowers": <number>,
  "borrowers": [
    {{
      "borrower_name": "<name>",
      "employment_history": [
        {{
          "employer": "<employer name>",
          "employer_variations": ["<variation1>", "<variation2>"],
          "start_date": "<date or 'Not specified'>",
          "end_date": "<date or 'Current' or 'Not specified'>",
          "position": "<title>",
          "employment_type": "<type>",
          "status_changes": ["<change1>", "<change2>"],
          "income_documented": {{
            "source": "<W-2, paystub, VOE, etc.>",
            "amount": "<amount>",
            "period": "<annual, monthly, etc.>"
          }},
          "verification_documents": ["<doc type 1>", "<doc type 2>"]
        }}
      ],
      "self_employment": [
        {{
          "business_name": "<name>",
          "business_type": "<S-Corp, Schedule C, Partnership, etc.>",
          "start_date": "<date or 'Not specified'>",
          "income_documented": {{
            "source": "<1120-S, 1065, Schedule C, etc.>",
            "amount": "<amount>",
            "period": "<annual, monthly, etc.>"
          }},
          "verification_documents": ["<doc type 1>", "<doc type 2>"]
        }}
      ],
      "other_income": [
        {{
          "income_type": "<rental, investment, etc.>",
          "source": "<description>",
          "amount": "<amount if documented>",
          "verification_documents": ["<doc type>"]
        }}
      ]
    }}
  ],
  "document_coverage": {{
    "earliest_date": "<date>",
    "latest_date": "<date>",
    "time_span_years": <number>
  }},
  "notable_findings": [
    "<finding 1>",
    "<finding 2>"
  ],
  "employer_name_variations": [
    {{
      "canonical_name": "<most formal name>",
      "variations": ["<variation1>", "<variation2>"]
    }}
  ],
  "income_scenario_classification": {{
    "employment_status": "<same_employer|employer_change|new_to_workforce|multiple_jobs>",
    "employment_continuity_years": <number>,
    "income_type": "<base_only|base_plus_variable|commissioned|hourly_fluctuating>",
    "variable_income_present": <true|false>,
    "variable_income_history_years": <number or 0>,
    "complexity_level": "<simple|moderate|complex|very_complex>",
    "complexity_factors": ["<factor1>", "<factor2>"],
    "documentation_completeness": "<complete|adequate|incomplete>",
    "income_trend": "<stable|increasing|decreasing|fluctuating>",
    "scenario_summary": "<2-3 sentence description of the overall income situation>"
  }}
}}"""

    response = await client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[
            {
                "role": "system",
                "content": "You are an expert mortgage underwriter analyzing employment and income documentation. You are meticulous about dates, document types, and identifying patterns in employment history."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result


def format_employment_history_markdown(analysis):
    """
    Convert the JSON analysis into a well-formatted markdown report.
    
    Args:
        analysis: Dictionary containing the employment history analysis
        
    Returns:
        Markdown formatted string
    """
    md = f"""# Employment History Report

**Loan ID:** {analysis['loan_id']}  
**Analysis Date:** {analysis['analysis_date']}  
**Number of Borrowers:** {analysis['number_of_borrowers']}

---

"""
    
    # Document Coverage
    coverage = analysis.get('document_coverage', {})
    if coverage:
        md += f"""## Document Coverage

**Time Span:** {coverage.get('time_span_years', 'Not specified')} years  
**Earliest Document:** {coverage.get('earliest_date', 'Not specified')}  
**Latest Document:** {coverage.get('latest_date', 'Not specified')}

---

"""
    
    # For each borrower
    for borrower in analysis.get('borrowers', []):
        md += f"""## {borrower['borrower_name']}

"""
        
        # Employment History
        if borrower.get('employment_history'):
            md += f"""### W-2 Employment History

"""
            for i, employment in enumerate(borrower['employment_history'], 1):
                md += f"""#### {i}. {employment['employer']}

"""
                
                # Employer variations
                if employment.get('employer_variations') and len(employment['employer_variations']) > 0:
                    md += f"""**Name Variations:** {', '.join(employment['employer_variations'])}

"""
                
                # Employment details
                md += f"""**Position:** {employment.get('position', 'Not specified')}  
**Employment Type:** {employment.get('employment_type', 'Not specified')}  
**Start Date:** {employment.get('start_date', 'Not specified')}  
**End Date:** {employment.get('end_date', 'Not specified')}

"""
                
                # Status changes
                if employment.get('status_changes') and len(employment['status_changes']) > 0:
                    md += f"""**Status Changes:**
"""
                    for change in employment['status_changes']:
                        md += f"""- {change}
"""
                    md += "\n"
                
                # Income documented
                if employment.get('income_documented'):
                    income = employment['income_documented']
                    if isinstance(income, dict):
                        md += f"""**Income Documented:**  
- Source: {income.get('source', 'Not specified')}  
- Amount: {income.get('amount', 'Not specified')}  
- Period: {income.get('period', 'Not specified')}

"""
                    elif isinstance(income, list) and len(income) > 0:
                        md += f"""**Income Documented:**
"""
                        for inc in income:
                            if isinstance(inc, dict):
                                md += f"""- Source: {inc.get('source', 'Not specified')} | Amount: {inc.get('amount', 'Not specified')} | Period: {inc.get('period', 'Not specified')}
"""
                        md += "\n"
                
                # Verification documents
                if employment.get('verification_documents'):
                    md += f"""**Verified By:** {', '.join(employment['verification_documents'])}

"""
                
                md += "---\n\n"
        
        # Self-Employment
        if borrower.get('self_employment'):
            md += f"""### Self-Employment / Business Ownership

"""
            for i, business in enumerate(borrower['self_employment'], 1):
                md += f"""#### {i}. {business['business_name']}

**Business Type:** {business.get('business_type', 'Not specified')}  
**Start Date:** {business.get('start_date', 'Not specified')}

"""
                
                # Income documented
                if business.get('income_documented'):
                    income = business['income_documented']
                    if isinstance(income, dict):
                        md += f"""**Income Documented:**  
- Source: {income.get('source', 'Not specified')}  
- Amount: {income.get('amount', 'Not specified')}  
- Period: {income.get('period', 'Not specified')}

"""
                    elif isinstance(income, list) and len(income) > 0:
                        md += f"""**Income Documented:**
"""
                        for inc in income:
                            if isinstance(inc, dict):
                                md += f"""- Source: {inc.get('source', 'Not specified')} | Amount: {inc.get('amount', 'Not specified')} | Period: {inc.get('period', 'Not specified')}
"""
                        md += "\n"
                
                # Verification documents
                if business.get('verification_documents'):
                    md += f"""**Verified By:** {', '.join(business['verification_documents'])}

"""
                
                md += "---\n\n"
        
        # Other Income
        if borrower.get('other_income'):
            md += f"""### Other Income Sources

"""
            for income in borrower['other_income']:
                # Handle case where income might be a list or dict
                if isinstance(income, dict):
                    income_type = income.get('income_type', 'Other Income')
                    source = income.get('source', 'Not specified')
                    amount = income.get('amount', 'Not specified')
                    docs = income.get('verification_documents', [])
                    md += f"""- **{income_type}:** {source}
  - Amount: {amount}
  - Verified By: {', '.join(docs) if docs else 'Not specified'}

"""
                else:
                    # Skip if not a dict
                    continue
            md += "\n"
    
    # Employer Name Variations
    if analysis.get('employer_name_variations'):
        md += f"""## Employer Name Variations

The following employers appear under multiple names in the documents:

"""
        for variation_group in analysis['employer_name_variations']:
            md += f"""**{variation_group['canonical_name']}**
"""
            for variation in variation_group['variations']:
                md += f"""- {variation}
"""
            md += "\n"
    
    # Notable Findings
    if analysis.get('notable_findings'):
        md += f"""## Notable Findings

"""
        for finding in analysis['notable_findings']:
            md += f"""- {finding}
"""
        md += "\n"
    
    # Income Scenario Classification
    if analysis.get('income_scenario_classification'):
        scenario = analysis['income_scenario_classification']
        md += f"""## Income Scenario Classification

**Employment Status:** {scenario.get('employment_status', 'Not classified').replace('_', ' ').title()}  
**Employment Continuity:** {scenario.get('employment_continuity_years', 'Unknown')} years  
**Income Type:** {scenario.get('income_type', 'Not classified').replace('_', ' ').title()}  
**Variable Income Present:** {'Yes' if scenario.get('variable_income_present') else 'No'}  
**Variable Income History:** {scenario.get('variable_income_history_years', 0)} years  
**Complexity Level:** {scenario.get('complexity_level', 'Not classified').upper()}  
**Documentation Completeness:** {scenario.get('documentation_completeness', 'Not assessed').title()}  
**Income Trend:** {scenario.get('income_trend', 'Not assessed').title()}

**Complexity Factors:**
"""
        if scenario.get('complexity_factors'):
            for factor in scenario['complexity_factors']:
                md += f"""- {factor}
"""
        else:
            md += "- None identified\n"
        
        md += f"""
**Scenario Summary:**  
{scenario.get('scenario_summary', 'No summary provided.')}

"""
    
    return md


def save_employment_history(analysis, markdown_report, loan_id):
    """
    Save both JSON and Markdown versions of the employment history.
    
    Args:
        analysis: Dictionary containing the analysis
        markdown_report: Formatted markdown string
        loan_id: The loan identifier
    """
    loan_dir = Path(f"loan_docs/{loan_id}")
    output_dir = loan_dir / "employment_history"
    output_dir.mkdir(exist_ok=True)
    
    # Save JSON
    json_path = output_dir / "employment_history.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    # Save Markdown
    md_path = output_dir / "employment_history.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print(f"\n✓ Employment history saved:")
    print(f"  - JSON: {json_path}")
    print(f"  - Markdown: {md_path}")


async def run_employment_history_analysis(loan_id):
    """
    Main function to run employment history analysis.
    
    Args:
        loan_id: The loan identifier
    """
    print("\n" + "="*80)
    print("EMPLOYMENT HISTORY ANALYSIS")
    print(f"Loan ID: {loan_id}")
    print("="*80)
    
    # Load income documents
    print("\n>> Loading income verification documents...")
    income_docs = load_income_documents(loan_id)
    print(f">> Found {len(income_docs)} income-relevant documents")
    
    # Generate employment history
    print("\n>> Analyzing employment history...")
    analysis = await generate_employment_history(loan_id, income_docs)
    
    # Format as markdown
    print("\n>> Formatting employment history report...")
    markdown_report = format_employment_history_markdown(analysis)
    
    # Save results
    save_employment_history(analysis, markdown_report, loan_id)
    
    print("\n" + "="*80)
    print("EMPLOYMENT HISTORY ANALYSIS COMPLETE")
    print("="*80)
    
    # Print summary
    print(f"\nBorrowers: {analysis['number_of_borrowers']}")
    for borrower in analysis.get('borrowers', []):
        print(f"\n{borrower['borrower_name']}:")
        print(f"  - W-2 Employment: {len(borrower.get('employment_history', []))} employer(s)")
        print(f"  - Self-Employment: {len(borrower.get('self_employment', []))} business(es)")
        print(f"  - Other Income: {len(borrower.get('other_income', []))} source(s)")
    
    if analysis.get('notable_findings'):
        print(f"\nNotable Findings: {len(analysis['notable_findings'])}")
        for finding in analysis['notable_findings'][:3]:
            print(f"  - {finding}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agents/employment_history_agent.py <loan_id>")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    try:
        asyncio.run(run_employment_history_analysis(loan_id))
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
