"""
Form 1003 Income Tracker

Identifies all Form 1003 documents in semantic_json, sorts them chronologically,
and extracts the monthly income stated in each version to track changes over time.

Usage:
    python agents/form_1003_income_tracker.py <loan_id>
    
Example:
    python agents/form_1003_income_tracker.py 1000175957
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import os
import asyncio

# Fix console encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")


def identify_1003_files(loan_id: str) -> list:
    """
    Scan semantic_json folder and identify all files where semantic_content.document_type is 'form_1003'.
    Returns list of file info dictionaries sorted by upload date.
    """
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return []
    
    print(f"\n{'='*80}")
    print(f"🔍 SCANNING FOR FORM 1003 DOCUMENTS")
    print(f"{'='*80}\n")
    print(f"📁 Directory: {semantic_dir}")
    
    form_1003_files = []
    
    all_files = list(semantic_dir.glob("*.json"))
    print(f"📋 Total semantic JSON files: {len(all_files)}")
    print(f"\n🔎 Checking semantic_content.document_type in each file...")
    
    for json_file in all_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check semantic_content.document_type (this is what the LLM classified it as)
            semantic_content = data.get('semantic_content', {})
            document_type = semantic_content.get('document_type', '').lower()
            
            # Look for form_1003 in the semantic classification
            is_1003 = 'form_1003' in document_type or '1003' in document_type
            
            if is_1003:
                metadata = data.get('metadata', {})
                upload_date = metadata.get('FileUploadDate', '')
                
                print(f"  ✓ Found: {json_file.name}")
                print(f"    Semantic Type: {document_type}")
                print(f"    Upload Date: {upload_date}")
                
                form_1003_files.append({
                    'file_path': json_file,
                    'file_name': json_file.name,
                    'metadata': metadata,
                    'upload_date': upload_date,
                    'full_data': data
                })
        
        except Exception as e:
            print(f"  ⚠️  Error reading {json_file.name}: {e}")
            continue
    
    print(f"\n✅ Found {len(form_1003_files)} Form 1003 document(s)")
    
    return form_1003_files


def sort_by_upload_date(form_1003_files: list) -> list:
    """Sort Form 1003 files by FileUploadDate in chronological order."""
    
    print(f"\n{'='*80}")
    print(f"📅 SORTING BY UPLOAD DATE")
    print(f"{'='*80}\n")
    
    # Sort by upload_date
    sorted_files = sorted(
        form_1003_files, 
        key=lambda x: x['upload_date'] if x['upload_date'] else '0000-00-00'
    )
    
    print("Chronological order:")
    for idx, file_info in enumerate(sorted_files, 1):
        print(f"  {idx}. {file_info['upload_date']} - {file_info['file_name']}")
    
    return sorted_files


async def extract_income_from_all_1003s(loan_id: str, sorted_1003_files: list) -> dict:
    """
    Send all Form 1003 semantic_json files to LLM at once and extract monthly income from each.
    Returns structured data showing income evolution over time.
    """
    
    print(f"\n{'='*80}")
    print(f"💰 EXTRACTING INCOME FROM ALL FORM 1003 VERSIONS")
    print(f"{'='*80}\n")
    
    if not sorted_1003_files:
        print("❌ No Form 1003 files to analyze")
        return {}
    
    print(f"📤 Sending {len(sorted_1003_files)} Form 1003 semantic JSON files to LLM...")
    print(f"   Model: {deployment}\n")
    
    # Initialize async client
    client = AsyncAzureOpenAI(
        api_key=subscription_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )
    
    # Build the context with all Form 1003 files
    files_context = []
    for idx, file_info in enumerate(sorted_1003_files, 1):
        files_context.append({
            'version': idx,
            'file_name': file_info['file_name'],
            'upload_date': file_info['upload_date'],
            'semantic_content': file_info['full_data'].get('semantic_content', {})
        })
    
    prompt = f"""You are analyzing Form 1003 (Uniform Residential Loan Application) documents for a mortgage loan.

**LOAN ID:** {loan_id}

I have provided {len(sorted_1003_files)} Form 1003 semantic JSON files, already sorted in chronological order by FileUploadDate.

**YOUR TASK:**

For EACH Form 1003 version, extract the monthly income information and return it in chronological order.

**WHAT TO EXTRACT:**

1. Primary Borrower's Monthly Income:
   - Employment income (base salary)
   - Overtime income
   - Bonus income
   - Commission income
   - Self-employment income
   - Retirement/pension income
   - Other income sources
   - **TOTAL monthly income**

2. Co-Borrower's Monthly Income (if present):
   - Same breakdown as above
   - **TOTAL monthly income**

3. **Combined Household Monthly Income**

**FORM 1003 FILES (in chronological order):**

{json.dumps(files_context, indent=2)}

**RESPONSE FORMAT:**

Return a JSON object with this exact structure:

{{
  "loan_id": "{loan_id}",
  "analysis_date": "CURRENT_ISO_TIMESTAMP",
  "total_versions_found": {len(sorted_1003_files)},
  "income_by_version": [
    {{
      "version_number": 1,
      "file_name": "...",
      "upload_date": "2025-05-20T19:58:12",
      "primary_borrower": {{
        "name": "ANTHONY ROBERT ZIMBICKI",
        "employment_income_base": 9533.33,
        "employment_income_overtime": 0,
        "employment_income_bonus": 9086.00,
        "employment_income_commission": 0,
        "self_employment_income": 0,
        "retirement_income": 0,
        "other_income": 0,
        "total_monthly_income": 18619.33
      }},
      "co_borrower": {{
        "name": null,
        "total_monthly_income": 0
      }},
      "combined_monthly_income": 18619.33
    }}
  ],
  "income_changes": [
    {{
      "from_version": 1,
      "to_version": 2,
      "primary_borrower_change": 0,
      "co_borrower_change": 0,
      "combined_change": 0,
      "description": "No changes" or "Base salary increased from $X to $Y"
    }}
  ],
  "summary": {{
    "initial_combined_income": 18619.33,
    "final_combined_income": 18619.33,
    "net_change": 0,
    "number_of_versions": 3
  }}
}}

**IMPORTANT:**
- Extract EXACT dollar amounts from the semantic content
- If a field is not present, use 0 or null appropriately
- Monthly income is the key metric - ensure all amounts are monthly (not annual)
- Compare versions and identify any changes in income amounts

Return ONLY valid JSON. No markdown, no explanations."""
    
    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert mortgage underwriter. You extract income data from Form 1003 loan applications with perfect accuracy."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=8000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        print("✅ Successfully extracted income data from all Form 1003 versions!")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: LLM did not return valid JSON: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return {}


def print_income_summary(analysis: dict):
    """Print a formatted summary of the income analysis."""
    
    print(f"\n{'='*80}")
    print(f"📊 INCOME ANALYSIS SUMMARY")
    print(f"{'='*80}\n")
    
    if not analysis:
        print("❌ No analysis data available")
        return
    
    print(f"Loan ID: {analysis.get('loan_id')}")
    print(f"Total Form 1003 Versions: {analysis.get('total_versions_found', 0)}")
    print(f"Analysis Date: {analysis.get('analysis_date')}")
    
    income_versions = analysis.get('income_by_version', [])
    
    if not income_versions:
        print("\n❌ No income data extracted")
        return
    
    print(f"\n{'─'*80}")
    print("INCOME BY VERSION (Chronological)")
    print(f"{'─'*80}\n")
    
    for version in income_versions:
        print(f"📄 Version {version.get('version_number')} - {version.get('upload_date')}")
        print(f"   File: {version.get('file_name')}")
        
        primary = version.get('primary_borrower', {})
        if primary:
            print(f"\n   👤 Primary Borrower: {primary.get('name', 'N/A')}")
            print(f"      • Employment Income: ${primary.get('employment_income', 0):,.2f}")
            if primary.get('self_employment_income', 0) > 0:
                print(f"      • Self-Employment Income: ${primary.get('self_employment_income', 0):,.2f}")
            if primary.get('retirement_income', 0) > 0:
                print(f"      • Retirement Income: ${primary.get('retirement_income', 0):,.2f}")
            if primary.get('other_income', 0) > 0:
                print(f"      • Other Income: ${primary.get('other_income', 0):,.2f}")
            print(f"      💰 Total: ${primary.get('total_monthly_income', 0):,.2f}/month")
        
        co_borrower = version.get('co_borrower')
        if co_borrower and co_borrower.get('name'):
            print(f"\n   👥 Co-Borrower: {co_borrower.get('name')}")
            print(f"      💰 Total: ${co_borrower.get('total_monthly_income', 0):,.2f}/month")
        
        print(f"\n   🏠 Combined Household Income: ${version.get('combined_monthly_income', 0):,.2f}/month")
        
        if version.get('notes'):
            print(f"   📝 Notes: {version.get('notes')}")
        
        print()
    
    # Show changes if multiple versions
    changes = analysis.get('income_changes', [])
    if changes:
        print(f"{'─'*80}")
        print("INCOME CHANGES BETWEEN VERSIONS")
        print(f"{'─'*80}\n")
        
        for change in changes:
            print(f"📈 Version {change.get('from_version')} → Version {change.get('to_version')}:")
            for item in change.get('changes_detected', []):
                print(f"   • {item}")
            print()
    
    # Show summary
    summary = analysis.get('summary', {})
    if summary:
        print(f"{'─'*80}")
        print("OVERALL SUMMARY")
        print(f"{'─'*80}\n")
        print(f"Initial Income:  ${summary.get('initial_income', 0):,.2f}/month")
        print(f"Final Income:    ${summary.get('final_income', 0):,.2f}/month")
        
        net_change = summary.get('net_change', 0)
        if net_change != 0:
            direction = "↑" if net_change > 0 else "↓"
            print(f"Net Change:      {direction} ${abs(net_change):,.2f}")
        else:
            print(f"Net Change:      No change")
        
        print(f"Revisions:       {summary.get('number_of_revisions', 0)}")


def save_analysis(loan_id: str, analysis: dict):
    """Save the analysis to JSON file in the income_analysis folder."""
    
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"form_1003_income_timeline.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"💾 JSON saved to: {output_file}")
    print(f"{'='*80}\n")
    
    return output_file


def create_html_report(loan_id: str, analysis: dict):
    """Create an HTML report of the Form 1003 income timeline."""
    
    if not analysis:
        print("❌ No analysis data to create HTML report")
        return None
    
    income_versions = analysis.get('income_by_version', [])
    summary = analysis.get('summary', {})
    changes = analysis.get('income_changes', [])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='UTF-8'>
    <title>Form 1003 Income Timeline - Loan {loan_id}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        h1 {{ color: #2c3e50; margin-bottom: 5px; }}
        h2 {{ color: #34495e; margin-top: 0; font-size: 18px; font-weight: normal; }}
        .overview {{ background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }}
        .stat-box {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .stat-label {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
        .version-section {{ background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .version-header {{ background-color: #3498db; color: white; padding: 10px 15px; margin: -20px -20px 15px -20px; border-radius: 5px 5px 0 0; font-size: 18px; font-weight: bold; }}
        .version-header.first {{ background-color: #27ae60; }}
        .version-header.last {{ background-color: #e67e22; }}
        .income-breakdown {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }}
        .income-item {{ background-color: #ecf0f1; padding: 10px; border-radius: 3px; }}
        .income-item label {{ font-size: 12px; color: #7f8c8d; }}
        .income-item value {{ font-size: 16px; font-weight: bold; color: #2c3e50; display: block; }}
        .total-income {{ background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 15px 0; }}
        .total-income value {{ font-size: 24px; font-weight: bold; color: #155724; }}
        .change-indicator {{ padding: 3px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }}
        .change-up {{ background-color: #d4edda; color: #155724; }}
        .change-down {{ background-color: #f8d7da; color: #721c24; }}
        .change-none {{ background-color: #d1ecf1; color: #0c5460; }}
        .timeline {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }}
        .timeline h4 {{ margin-top: 0; color: #856404; }}
        .file-info {{ background-color: #f8f9fa; padding: 10px; border-radius: 3px; margin: 10px 0; font-size: 14px; color: #6c757d; }}
    </style>
</head>
<body>
    <h1>Form 1003 Income Timeline Report</h1>
    <h2>Loan ID: {analysis.get('loan_id')} | {analysis.get('total_versions_found', 0)} Form 1003 Versions</h2>
    
    <div class='overview'>
        <h3>Summary</h3>
        <div class='stats-grid'>
            <div class='stat-box'>
                <div class='stat-value'>${summary.get('initial_combined_income', 0):,.2f}</div>
                <div class='stat-label'>Initial Income (Version 1)</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value'>${summary.get('final_combined_income', 0):,.2f}</div>
                <div class='stat-label'>Final Income (Latest Version)</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value'>${abs(summary.get('net_change', 0)):,.2f}</div>
                <div class='stat-label'>Net Change</div>
            </div>
            <div class='stat-box'>
                <div class='stat-value'>{analysis.get('total_versions_found', 0)}</div>
                <div class='stat-label'>Total Revisions</div>
            </div>
        </div>
    </div>
"""
    
    # Add each version
    for idx, version in enumerate(income_versions):
        version_num = version.get('version_number', idx + 1)
        header_class = ""
        if version_num == 1:
            header_class = "first"
        elif version_num == len(income_versions):
            header_class = "last"
        
        primary = version.get('primary_borrower', {})
        co_borrower = version.get('co_borrower', {})
        combined_income = version.get('combined_monthly_income', 0)
        
        html += f"""
    <div class='version-section'>
        <div class='version-header {header_class}'>Version {version_num} - {version.get('upload_date', 'Unknown Date')}</div>
        
        <div class='file-info'>
            📄 File: {version.get('file_name', 'Unknown')}
        </div>
        
        <h4>👤 Primary Borrower: {primary.get('name', 'N/A')}</h4>
        <div class='income-breakdown'>
            <div class='income-item'>
                <label>Base Salary</label>
                <value>${primary.get('employment_income_base', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Overtime</label>
                <value>${primary.get('employment_income_overtime', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Bonus</label>
                <value>${primary.get('employment_income_bonus', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Commission</label>
                <value>${primary.get('employment_income_commission', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Self-Employment</label>
                <value>${primary.get('self_employment_income', 0):,.2f}</value>
            </div>
            <div class='income-item'>
                <label>Other Income</label>
                <value>${primary.get('other_income', 0):,.2f}</value>
            </div>
        </div>
        
        <div class='total-income'>
            <label>Primary Borrower Total Monthly Income</label>
            <value>${primary.get('total_monthly_income', 0):,.2f}</value>
        </div>
"""
        
        # Add co-borrower if present
        if co_borrower and co_borrower.get('name'):
            html += f"""
        <h4>👥 Co-Borrower: {co_borrower.get('name')}</h4>
        <div class='total-income'>
            <label>Co-Borrower Total Monthly Income</label>
            <value>${co_borrower.get('total_monthly_income', 0):,.2f}</value>
        </div>
"""
        
        html += f"""
        <div class='total-income' style='background-color: #cfe2ff; border-left-color: #0d6efd;'>
            <label>🏠 Combined Household Monthly Income</label>
            <value style='color: #084298;'>${combined_income:,.2f}</value>
        </div>
    </div>
"""
    
    # Add changes timeline if there are multiple versions
    if len(income_versions) > 1 and changes:
        html += """
    <div class='overview'>
        <h3>Income Changes Timeline</h3>
        <div class='timeline'>
"""
        for change in changes:
            from_ver = change.get('from_version')
            to_ver = change.get('to_version')
            desc = change.get('description', 'No description')
            combined_change = change.get('combined_change', 0)
            
            if combined_change > 0:
                change_class = 'change-up'
                change_symbol = '↑'
            elif combined_change < 0:
                change_class = 'change-down'
                change_symbol = '↓'
            else:
                change_class = 'change-none'
                change_symbol = '='
            
            html += f"""
            <p>
                <strong>Version {from_ver} → Version {to_ver}:</strong> 
                <span class='change-indicator {change_class}'>{change_symbol} ${abs(combined_change):,.2f}</span>
                <br/>
                {desc}
            </p>
"""
        
        html += """
        </div>
    </div>
"""
    
    html += f"""
    <div class='overview'>
        <p style='color: #6c757d; font-size: 14px;'>
            <strong>Report Generated:</strong> {analysis.get('analysis_date', datetime.now().isoformat())}<br/>
            <strong>Source:</strong> Form 1003 Income Timeline Tracker
        </p>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    output_dir = Path(f"loan_docs/{loan_id}/income_analysis")
    output_file = output_dir / "form_1003_income_timeline.html"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"💾 HTML report saved to: {output_file}\n")
    
    return output_file


async def main():
    """Main execution function."""
    
    if len(sys.argv) < 2:
        print("Usage: python agents/form_1003_income_tracker.py <loan_id>")
        print("Example: python agents/form_1003_income_tracker.py 1000175957")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    print(f"\n{'='*80}")
    print(f"📋 FORM 1003 INCOME TRACKER")
    print(f"{'='*80}")
    print(f"\nLoan ID: {loan_id}")
    
    # Step 1: Identify all Form 1003 files
    form_1003_files = identify_1003_files(loan_id)
    
    if not form_1003_files:
        print("\n❌ No Form 1003 documents found!")
        print("\nPossible reasons:")
        print("  • semantic_json folder doesn't exist")
        print("  • No files match Form 1003 naming patterns")
        print("  • Documents haven't been processed yet")
        sys.exit(1)
    
    # Step 2: Sort by upload date
    sorted_files = sort_by_upload_date(form_1003_files)
    
    # Step 3: Extract income from all versions at once
    analysis = await extract_income_from_all_1003s(loan_id, sorted_files)
    
    if not analysis:
        print("\n❌ Failed to extract income data")
        sys.exit(1)
    
    # Step 4: Print summary
    print_income_summary(analysis)
    
    # Step 5: Save results
    save_analysis(loan_id, analysis)
    
    # Step 6: Create HTML report
    create_html_report(loan_id, analysis)
    
    print("\n✅ ANALYSIS COMPLETE!\n")


if __name__ == "__main__":
    asyncio.run(main())
