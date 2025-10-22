"""
Underwriting Compliance Agent

Reviews all semantic JSON files for a loan against Spring EQ underwriting guidelines
to verify proper qualification and compliance with lending policies.

Usage:
    python agents/underwriting_compliance_agent.py <loan_id>
    
Example:
    python agents/underwriting_compliance_agent.py 1000182227
"""

import os
import sys
import json
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialize Azure OpenAI client
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


def generate_html_report(compliance_review, output_path):
    """Generate HTML report with loan details and compliance findings."""
    
    loan_summary = compliance_review.get('loan_summary', {})
    uw_summary = compliance_review.get('underwriting_summary', {})
    status = compliance_review.get('overall_compliance_status', 'UNKNOWN')
    score = compliance_review.get('compliance_score', 0)
    recommendation = compliance_review.get('recommendation', 'UNKNOWN')
    
    # Extract property value from compliance findings or appraisal details
    property_value = uw_summary.get('property_value', 0)
    if property_value == 0:
        # Try to extract from findings
        for finding in compliance_review.get('critical_findings', []) + compliance_review.get('compliant_items', []):
            text = str(finding.get('actual_value', '')) + str(finding.get('details', ''))
            # Look for appraisal value, appraised value, etc.
            import re
            matches = re.findall(r'(?:apprais|valu)(?:ed|e)[^\d]*[\$]?([\d,]+)', text, re.IGNORECASE)
            for match in matches:
                try:
                    val = float(match.replace(',', ''))
                    if 100000 < val < 10000000:  # Reasonable property value range
                        property_value = val
                        break
                except:
                    pass
            if property_value > 0:
                break
    
    # Extract interest rate from compliance findings
    interest_rate = 'N/A'
    for finding in compliance_review.get('critical_findings', []) + compliance_review.get('compliant_items', []):
        text = str(finding.get('actual_value', '')) + str(finding.get('details', '')) + str(finding.get('issue', ''))
        # Look for interest rate, APR, rate patterns
        import re
        matches = re.findall(r'(?:interest rate|rate|apr)[^\d]*([\d.]+)%', text, re.IGNORECASE)
        for match in matches:
            try:
                rate = float(match)
                if 1 < rate < 30:  # Reasonable interest rate range
                    interest_rate = f"{rate}%"
                    break
            except:
                pass
        if interest_rate != 'N/A':
            break
    
    # Extract payoff information from critical findings and conditions
    payoffs = []
    for finding in compliance_review.get('critical_findings', []):
        if 'payoff' in finding.get('issue', '').lower() or 'debt' in finding.get('category', '').lower():
            payoffs.append(finding.get('issue', ''))
    
    # Determine income types
    income_types = []
    for item in compliance_review.get('compliant_items', []):
        if 'income' in item.get('category', '').lower() or 'employment' in item.get('category', '').lower():
            details = item.get('details', '')
            if 'w-2' in details.lower() or 'w2' in details.lower():
                income_types.append('W-2')
            if 'self-employed' in details.lower():
                income_types.append('Self-Employed')
            if 'bonus' in details.lower():
                income_types.append('Bonus')
            if 'overtime' in details.lower():
                income_types.append('Overtime')
    income_types = list(set(income_types)) or ['W-2 (default)']
    
    # Check if debt consolidation
    is_debt_consolidation = 'cash-out' in loan_summary.get('loan_purpose', '').lower() or 'debt' in loan_summary.get('loan_purpose', '').lower() or 'payoff' in loan_summary.get('loan_purpose', '').lower()
    
    # Severity badges
    def severity_badge(severity):
        colors = {
            'CRITICAL': '#dc3545',
            'MAJOR': '#fd7e14',
            'MINOR': '#ffc107'
        }
        return f'<span style="background-color: {colors.get(severity, "#6c757d")}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold;">{severity}</span>'
    
    def status_badge(status):
        colors = {
            'APPROVED': '#28a745',
            'APPROVED_WITH_CONDITIONS': '#ffc107',
            'SUSPENDED': '#fd7e14',
            'DECLINED': '#dc3545',
            'PASS': '#28a745',
            'CONDITIONAL': '#ffc107',
            'FAIL': '#dc3545'
        }
        return f'<span style="background-color: {colors.get(status, "#6c757d")}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">{status.replace("_", " ")}</span>'
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Underwriting Compliance Review - Loan {loan_summary.get('loan_number', 'N/A')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        h3 {{
            color: #34495e;
            margin-top: 20px;
        }}
        .header-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .status-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .status-box h2 {{
            color: white;
            border: none;
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }}
        .status-box .score {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .info-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}
        .info-card strong {{
            color: #2c3e50;
            display: block;
            margin-bottom: 5px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-card.green {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        .metric-card.blue {{
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }}
        .metric-card.purple {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 1.8em;
            font-weight: bold;
        }}
        .findings {{
            margin: 20px 0;
        }}
        .finding-item {{
            background-color: #fff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .finding-item.critical {{
            border-left: 4px solid #dc3545;
            background-color: #fff5f5;
        }}
        .finding-item.major {{
            border-left: 4px solid #fd7e14;
            background-color: #fff8f0;
        }}
        .finding-item.minor {{
            border-left: 4px solid #ffc107;
            background-color: #fffbf0;
        }}
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .finding-category {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .checklist {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }}
        .checklist-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #28a745;
        }}
        .checklist-item.conditional {{
            border-left-color: #ffc107;
            background-color: #fffbf0;
        }}
        .checklist-item.fail {{
            border-left-color: #dc3545;
            background-color: #fff5f5;
        }}
        .checklist-icon {{
            font-size: 1.5em;
            margin-right: 10px;
        }}
        .conditions-list {{
            background-color: #fff8f0;
            border: 1px solid #ffc107;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
        }}
        .conditions-list ol {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .conditions-list li {{
            margin: 10px 0;
            line-height: 1.6;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 30px;
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏦 Underwriting Compliance Review</h1>
        
        <!-- Status Overview -->
        <div class="header-grid">
            <div class="status-box">
                <h2>Compliance Score</h2>
                <div class="score">{score}%</div>
                <div>{status_badge(status)}</div>
            </div>
            <div class="info-card">
                <strong>Loan Number</strong>
                {loan_summary.get('loan_number', 'N/A')}
            </div>
            <div class="info-card">
                <strong>Borrower(s)</strong>
                {loan_summary.get('borrower_name', 'N/A')}
            </div>
            <div class="info-card">
                <strong>Recommendation</strong>
                {status_badge(recommendation)}
            </div>
        </div>
        
        <!-- Loan Details -->
        <h2>📋 Loan Details</h2>
        <div class="metric-grid">
            <div class="metric-card green">
                <div class="metric-label">Loan Amount</div>
                <div class="metric-value">${loan_summary.get('loan_amount', 0):,.0f}</div>
            </div>
            <div class="metric-card blue">
                <div class="metric-label">Interest Rate</div>
                <div class="metric-value">{interest_rate}</div>
            </div>
            <div class="metric-card purple">
                <div class="metric-label">Property Value</div>
                <div class="metric-value">${property_value:,.0f}</div>
            </div>
            <div class="metric-card green">
                <div class="metric-label">CLTV</div>
                <div class="metric-value">{uw_summary.get('cltv', 0):.2f}%</div>
            </div>
            <div class="metric-card blue">
                <div class="metric-label">LTV</div>
                <div class="metric-value">{uw_summary.get('ltv', 0):.2f}%</div>
            </div>
        </div>
        
        <!-- Property Information -->
        <h2>🏠 Property Information</h2>
        <table>
            <tr>
                <th>Address</th>
                <td>{loan_summary.get('property_address', 'N/A')}</td>
            </tr>
            <tr>
                <th>Property Type</th>
                <td>{uw_summary.get('property_type', 'N/A')}</td>
            </tr>
            <tr>
                <th>Occupancy</th>
                <td>{loan_summary.get('occupancy', 'N/A')}</td>
            </tr>
            <tr>
                <th>Loan Purpose</th>
                <td>{loan_summary.get('loan_purpose', 'N/A')}</td>
            </tr>
        </table>
        
        <!-- Borrower Financial Profile -->
        <h2>👤 Borrower Financial Profile</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">FICO Score</div>
                <div class="metric-value">{uw_summary.get('fico_score', 0)}</div>
            </div>
            <div class="metric-card blue">
                <div class="metric-label">DTI Ratio</div>
                <div class="metric-value">{uw_summary.get('dti_ratio', 0):.2f}%</div>
            </div>
            <div class="metric-card green">
                <div class="metric-label">Income Type</div>
                <div class="metric-value" style="font-size: 1.2em;">{', '.join(income_types)}</div>
            </div>
        </div>
        
        <table>
            <tr>
                <th>Income Verified</th>
                <td>{'✅ Yes' if uw_summary.get('income_verified', False) else '❌ No'}</td>
            </tr>
            <tr>
                <th>Employment Verified</th>
                <td>{'✅ Yes' if uw_summary.get('employment_verified', False) else '❌ No'}</td>
            </tr>
            <tr>
                <th>Assets Verified</th>
                <td>{'✅ Yes' if uw_summary.get('assets_verified', False) else '❌ No'}</td>
            </tr>
            <tr>
                <th>Credit Acceptable</th>
                <td>{'✅ Yes' if uw_summary.get('credit_acceptable', False) else '❌ No'}</td>
            </tr>
            <tr>
                <th>Property Acceptable</th>
                <td>{'✅ Yes' if uw_summary.get('property_acceptable', False) else '❌ No'}</td>
            </tr>
        </table>
"""
    
    # Debt Consolidation / Payoffs
    if is_debt_consolidation:
        html += """
        <h2>💳 Debt Consolidation / Payoffs</h2>
        <div class="info-card">
            <strong>Loan Purpose: Debt Consolidation</strong>
"""
        if payoffs:
            html += "<ul>"
            for payoff in payoffs:
                html += f"<li>{payoff}</li>"
            html += "</ul>"
        else:
            html += "<p>Payoff details included in compliance findings below.</p>"
        html += """
        </div>
"""
    
    # Appraisal Information
    appraisal_info = None
    for item in compliance_review.get('compliant_items', []):
        if 'appraisal' in item.get('category', '').lower():
            appraisal_info = item
            break
    
    if appraisal_info:
        html += f"""
        <h2>📊 Appraisal Information</h2>
        <div class="info-card">
            <strong>{appraisal_info.get('requirement', 'Appraisal')}</strong>
            <p>{appraisal_info.get('details', 'N/A')}</p>
            <p><strong>Status:</strong> {status_badge(appraisal_info.get('status', 'UNKNOWN'))}</p>
        </div>
"""
    
    # Critical Findings
    critical = [f for f in compliance_review.get('critical_findings', []) if f.get('severity') == 'CRITICAL']
    if critical:
        html += """
        <h2>🚨 Critical Issues</h2>
        <div class="findings">
"""
        for finding in critical:
            html += f"""
            <div class="finding-item critical">
                <div class="finding-header">
                    <div class="finding-category">{finding.get('category', 'Unknown')}</div>
                    {severity_badge('CRITICAL')}
                </div>
                <p><strong>Issue:</strong> {finding.get('issue', 'N/A')}</p>
                <p><strong>Guideline Requirement:</strong> {finding.get('guideline_requirement', 'N/A')}</p>
                <p><strong>Actual Value:</strong> {finding.get('actual_value', 'N/A')}</p>
                <p><strong>Recommendation:</strong> {finding.get('recommendation', 'N/A')}</p>
            </div>
"""
        html += "</div>"
    
    # Major Findings
    major = [f for f in compliance_review.get('critical_findings', []) if f.get('severity') == 'MAJOR']
    if major:
        html += """
        <h2>⚠️ Major Issues</h2>
        <div class="findings">
"""
        for finding in major:
            html += f"""
            <div class="finding-item major">
                <div class="finding-header">
                    <div class="finding-category">{finding.get('category', 'Unknown')}</div>
                    {severity_badge('MAJOR')}
                </div>
                <p><strong>Issue:</strong> {finding.get('issue', 'N/A')}</p>
                <p><strong>Guideline Requirement:</strong> {finding.get('guideline_requirement', 'N/A')}</p>
                <p><strong>Actual Value:</strong> {finding.get('actual_value', 'N/A')}</p>
                <p><strong>Recommendation:</strong> {finding.get('recommendation', 'N/A')}</p>
            </div>
"""
        html += "</div>"
    
    # Minor Findings
    minor = [f for f in compliance_review.get('critical_findings', []) if f.get('severity') == 'MINOR']
    if minor:
        html += """
        <h2>ℹ️ Minor Issues</h2>
        <div class="findings">
"""
        for finding in minor:
            html += f"""
            <div class="finding-item minor">
                <div class="finding-header">
                    <div class="finding-category">{finding.get('category', 'Unknown')}</div>
                    {severity_badge('MINOR')}
                </div>
                <p><strong>Issue:</strong> {finding.get('issue', 'N/A')}</p>
                <p><strong>Guideline Requirement:</strong> {finding.get('guideline_requirement', 'N/A')}</p>
                <p><strong>Actual Value:</strong> {finding.get('actual_value', 'N/A')}</p>
                <p><strong>Recommendation:</strong> {finding.get('recommendation', 'N/A')}</p>
            </div>
"""
        html += "</div>"
    
    # Conditions for Approval
    conditions = compliance_review.get('conditions_for_approval', [])
    if conditions:
        html += f"""
        <h2>📋 Conditions for Approval ({len(conditions)})</h2>
        <div class="conditions-list">
            <ol>
"""
        for condition in conditions:
            html += f"                <li>{condition}</li>\n"
        html += """
            </ol>
        </div>
"""
    
    # Compliance Checklist
    html += """
        <h2>✓ Detailed Compliance Checklist</h2>
        <div class="checklist">
"""
    checklist = compliance_review.get('detailed_checklist', {})
    for category, result in checklist.items():
        status_class = result.get('status', 'PASS').lower()
        icon = '✅' if status_class == 'pass' else '⚠️' if status_class == 'conditional' else '❌'
        html += f"""
            <div class="checklist-item {status_class}">
                <div class="checklist-icon">{icon}</div>
                <div>
                    <strong>{category.replace('_', ' ').title()}</strong><br>
                    {status_badge(result.get('status', 'UNKNOWN'))}
                </div>
            </div>
"""
    html += """
        </div>
"""
    
    # Underwriter Notes
    notes = compliance_review.get('underwriter_notes', '')
    if notes:
        html += f"""
        <h2>📝 Underwriter Notes</h2>
        <div class="info-card">
            <p>{notes}</p>
        </div>
"""
    
    # Footer
    metadata = compliance_review.get('_metadata', {})
    html += f"""
        <div class="timestamp">
            <p>Review Generated: {metadata.get('review_date', 'N/A')}</p>
            <p>Guidelines Version: {metadata.get('guidelines_version', 'N/A')} | Model: {metadata.get('reviewing_model', 'N/A')}</p>
            <p>Documents Reviewed: {metadata.get('documents_reviewed', 0)}</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def load_spring_eq_guidelines():
    """Load Spring EQ underwriting guidelines."""
    guidelines_path = Path("guidelines/spring_eq_guidelines.json")
    with open(guidelines_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all_semantic_json(loan_id):
    """Load all semantic JSON files for a loan."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        print("   Run document_semantic_processor.py first!")
        return {}
    
    semantic_docs = {}
    for json_file in semantic_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                clean_name = json_file.stem
                semantic_docs[clean_name] = data
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return semantic_docs


def review_compliance(loan_id="1000182227"):
    """
    Review loan compliance against Spring EQ underwriting guidelines.
    """
    
    print("=" * 80)
    print(f"Underwriting Compliance Review - Loan {loan_id}")
    print("=" * 80)
    print()
    
    # Load guidelines and semantic data
    print("📋 Loading Spring EQ underwriting guidelines...")
    guidelines = load_spring_eq_guidelines()
    
    print("📁 Loading all semantic JSON files...")
    semantic_docs = load_all_semantic_json(loan_id)
    
    if not semantic_docs:
        print("❌ No semantic JSON files found!")
        return None
    
    print(f"✅ Loaded {len(semantic_docs)} semantic documents")
    print()
    print("=" * 80)
    print("🔍 Analyzing loan for compliance...")
    print("=" * 80)
    print()
    
    # Build comprehensive prompt
    prompt = f"""You are a Spring EQ Underwriting Compliance Officer reviewing a loan package for compliance with company guidelines.

SPRING EQ UNDERWRITING GUIDELINES:
{json.dumps(guidelines, indent=2)}

LOAN DOCUMENTS (Semantic Data):
{json.dumps(semantic_docs, indent=2)}

YOUR TASK:
Conduct a comprehensive underwriting compliance review covering ALL guideline categories:

1. CREDIT REQUIREMENTS
   - Verify FICO scores meet minimum requirements for CLTV
   - Check credit report type (Experian single or tri-merge)
   - Verify tradeline requirements (3 tradelines, 1 active within 6 months)
   - Review housing history (0x30x6 maximum)
   - Check for significant derogatory credit events and waiting periods
   - Verify no unauthorized user accounts in debt calculations

2. DEBT-TO-INCOME RATIO
   - Calculate DTI using correct payment calculations
   - Verify DTI is ≤50% (if 740+ FICO or 700+ with $3500 residual) OR ≤45% (all other)
   - Check IO senior lien treatment (use fully amortizing payment)
   - Verify all liabilities are included correctly
   - Check for debt payoffs (permitted) vs paydowns (not permitted)

3. LOAN-TO-VALUE REQUIREMENTS
   - Verify CLTV meets maximum for occupancy type and FICO score
   - Check owner occupied: Max 90% (680+ FICO), 80% (660-679), 70% (640-659)
   - Check second home/investment: Max 80% (740+), 70% (680-739)

4. LOAN AMOUNT AND LIMITS
   - Verify loan ≥$25,000 minimum
   - Verify loan ≤$500,000 maximum single loan
   - Check total financing limits by occupancy type
   - Verify single borrower aggregate ≤$500,000

5. PROPERTY ELIGIBILITY
   - Verify property type is eligible (SFR, PUD, modular, condo, 1-4 unit primary)
   - Check for ineligible types (co-ops, condotels, mobile homes, commercial, >20 acres, etc.)
   - Verify no state restrictions (Texas multi-unit, PA/TN first lien HELOC)

6. BORROWER ELIGIBILITY
   - Verify US citizen, permanent resident, or non-permanent resident with proper docs
   - Check no diplomatic immunity holders
   - Verify no non-occupant co-borrowers or guarantors

7. INCOME AND EMPLOYMENT
   - Verify 2 year employment history
   - Check income continuance for 3 years
   - Verify proper documentation (paystubs, W-2s, tax returns)
   - Check self-employed requirements if applicable (25%+ ownership or 1099s)
   - Verify employment verification within 10 business days of note date
   - Check for unacceptable income types

8. ASSET REQUIREMENTS
   - Verify cash to close documentation if >1 month PITIA
   - Check acceptable asset sources
   - Verify 2 months bank statements
   - Check large deposits (>50% monthly income)

9. APPRAISAL COMPLIANCE
   - Verify correct appraisal type for loan amount
   - Check ≤$400K: AVM, prior use, drive-by, or full interior
   - Check >$400K: Prior use or full interior only
   - Verify appraisal age ≤90 days from note date

10. SENIOR LIEN ELIGIBILITY
    - Verify no active forbearance/deferment
    - Check no negative amortization
    - Verify no balloon payment within 5 years
    - Check no reverse mortgages
    - Verify no private mortgages opened within 12 months

11. DOCUMENT CURRENCY
    - Verify credit report ≤60 days from note date
    - Check income/asset documents ≤60 days
    - Verify collateral/title/appraisal ≤90 days

12. SPECIAL REQUIREMENTS
    - Check piggyback requirements if applicable
    - Verify trust requirements if property in trust
    - Check UCC filings (PACE/HERO must be paid in full)
    - Verify title insurance requirements
    - Check homeowners insurance compliance

OUTPUT FORMAT (JSON only, no markdown):
{{
  "loan_summary": {{
    "loan_number": "...",
    "borrower_name": "...",
    "property_address": "...",
    "loan_amount": 0,
    "loan_purpose": "...",
    "occupancy": "..."
  }},
  "overall_compliance_status": "APPROVED" | "APPROVED_WITH_CONDITIONS" | "SUSPENDED" | "DECLINED",
  "compliance_score": "0-100 (percentage of requirements met)",
  "critical_findings": [
    {{
      "category": "...",
      "issue": "...",
      "guideline_requirement": "...",
      "actual_value": "...",
      "severity": "CRITICAL" | "MAJOR" | "MINOR",
      "recommendation": "..."
    }}
  ],
  "compliant_items": [
    {{
      "category": "...",
      "requirement": "...",
      "status": "PASS",
      "details": "..."
    }}
  ],
  "conditions_for_approval": [
    "Condition 1...",
    "Condition 2..."
  ],
  "underwriting_summary": {{
    "fico_score": 0,
    "dti_ratio": 0,
    "cltv": 0,
    "ltv": 0,
    "property_type": "...",
    "occupancy": "...",
    "income_verified": true/false,
    "employment_verified": true/false,
    "assets_verified": true/false,
    "credit_acceptable": true/false,
    "property_acceptable": true/false
  }},
  "detailed_checklist": {{
    "credit_requirements": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "dti_requirements": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "ltv_requirements": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "loan_limits": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "property_eligibility": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "borrower_eligibility": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "income_employment": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "asset_requirements": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "appraisal_compliance": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "senior_lien_eligibility": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "document_currency": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}},
    "special_requirements": {{"status": "PASS|FAIL|CONDITIONAL", "notes": "..."}}
  }},
  "recommendation": "APPROVE | APPROVE_WITH_CONDITIONS | REFER_TO_SENIOR_UW | DECLINE",
  "underwriter_notes": "Comprehensive summary of findings and rationale for decision"
}}

Be thorough, precise, and cite specific guideline requirements when identifying issues."""

    # Call LLM
    print("⏳ Performing comprehensive compliance review (this may take 60-90 seconds)...")
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system", 
                "content": "You are a Spring EQ Senior Underwriter with expert knowledge of company guidelines. Output only valid JSON with thorough compliance analysis."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=16000
    )
    
    # Parse response
    compliance_review = json.loads(response.choices[0].message.content)
    
    # Add metadata
    compliance_review['_metadata'] = {
        'review_date': datetime.now().isoformat(),
        'loan_id': loan_id,
        'guidelines_version': guidelines.get('parsing_metadata', {}).get('parse_date', 'unknown'),
        'documents_reviewed': len(semantic_docs),
        'reviewing_model': deployment,
        'agent': 'underwriting_compliance_agent'
    }
    
    # Save output
    output_dir = Path(f"loan_docs/{loan_id}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"compliance_review_{loan_id}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(compliance_review, f, indent=2, ensure_ascii=False)
    
    # Generate HTML report
    html_path = output_path.with_suffix('.html')
    generate_html_report(compliance_review, html_path)
    
    # Display results
    print()
    print("=" * 80)
    print("✅ COMPLIANCE REVIEW COMPLETE!")
    print("=" * 80)
    print(f"📄 JSON saved to: {output_path}")
    print(f"📄 HTML saved to: {html_path}")
    print()
    
    # Summary
    print("📊 REVIEW SUMMARY:")
    print(f"   Loan: {compliance_review.get('loan_summary', {}).get('loan_number', 'Unknown')}")
    print(f"   Borrower: {compliance_review.get('loan_summary', {}).get('borrower_name', 'Unknown')}")
    print(f"   Status: {compliance_review.get('overall_compliance_status', 'Unknown')}")
    print(f"   Compliance Score: {compliance_review.get('compliance_score', 'N/A')}")
    print(f"   Recommendation: {compliance_review.get('recommendation', 'Unknown')}")
    print()
    
    # Critical findings
    critical = [f for f in compliance_review.get('critical_findings', []) if f.get('severity') == 'CRITICAL']
    major = [f for f in compliance_review.get('critical_findings', []) if f.get('severity') == 'MAJOR']
    minor = [f for f in compliance_review.get('critical_findings', []) if f.get('severity') == 'MINOR']
    
    if critical:
        print(f"🚨 CRITICAL ISSUES: {len(critical)}")
        for finding in critical:
            print(f"   - {finding.get('category')}: {finding.get('issue')}")
        print()
    
    if major:
        print(f"⚠️  MAJOR ISSUES: {len(major)}")
        for finding in major:
            print(f"   - {finding.get('category')}: {finding.get('issue')}")
        print()
    
    if minor:
        print(f"ℹ️  MINOR ISSUES: {len(minor)}")
        for finding in minor:
            print(f"   - {finding.get('category')}: {finding.get('issue')}")
        print()
    
    # Conditions
    conditions = compliance_review.get('conditions_for_approval', [])
    if conditions:
        print(f"📋 CONDITIONS FOR APPROVAL: {len(conditions)}")
        for i, condition in enumerate(conditions, 1):
            print(f"   {i}. {condition}")
        print()
    
    # Checklist summary
    print("✓ DETAILED CHECKLIST:")
    checklist = compliance_review.get('detailed_checklist', {})
    for category, result in checklist.items():
        status = result.get('status', 'UNKNOWN')
        emoji = "✅" if status == "PASS" else "⚠️" if status == "CONDITIONAL" else "❌"
        print(f"   {emoji} {category.replace('_', ' ').title()}: {status}")
    
    print()
    print("=" * 80)
    
    return compliance_review


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    review_compliance(loan_id)
