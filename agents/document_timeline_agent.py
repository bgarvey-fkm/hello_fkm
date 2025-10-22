"""
Document Timeline Agent

Analyzes semantic JSON files and organizes them by document type and timeline.
Reconstructs the loan processing workflow from application through closing.

Typical Loan Lifecycle:
1. Application (1003 submission with signature date)
2. Credit Pull (credit report ordered)
3. Home Valuation (AVM/Appraisal ordered)
4. Income Verification (paystubs, W-2s, VOE collected)
5. Additional Documentation (flood cert, insurance, first mortgage statement)
6. VOI/VOE Notes (employment/income verification)
7. Underwriting Decision (conditions issued)
8. Pre-Closing (closing disclosure, title commitment)
9. Closing Documents (final execution)
10. Funding (disbursement)

Usage:
    python agents/document_timeline_agent.py <loan_id>

Example:
    python agents/document_timeline_agent.py 1000182005
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv
import re
from collections import defaultdict

load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")


# Document type categories aligned with loan lifecycle
DOCUMENT_CATEGORIES = {
    "1003_APPLICATION": {
        "priority": 1,
        "stage": "Application",
        "keywords": ["1003", "application", "urla", "loan application", "borrower application"],
        "description": "Uniform Residential Loan Application (Form 1003)"
    },
    "CREDIT_REPORT": {
        "priority": 2,
        "stage": "Credit Pull",
        "keywords": ["credit report", "credit score", "tri-merge", "experian", "equifax", "transunion", "fico"],
        "description": "Credit Report and Credit Score"
    },
    "CREDIT_SUPPLEMENTS": {
        "priority": 3,
        "stage": "Credit Pull",
        "keywords": ["letter of explanation", "lox", "credit explanation", "payoff letter", "settlement letter"],
        "description": "Credit-Related Supplements (LOX, payoff letters)"
    },
    "APPRAISAL": {
        "priority": 4,
        "stage": "Home Valuation",
        "keywords": ["appraisal", "avm", "bpo", "property valuation", "comparable sales", "subject property"],
        "description": "Property Appraisal or Valuation Report"
    },
    "PROPERTY_INSPECTION": {
        "priority": 5,
        "stage": "Home Valuation",
        "keywords": ["property inspection", "condition report", "property condition", "exterior inspection"],
        "description": "Property Condition Inspection"
    },
    "INCOME_DOCS": {
        "priority": 6,
        "stage": "Income Verification",
        "keywords": ["paystub", "w-2", "w2", "tax return", "1040", "schedule c", "pay stub", "earnings"],
        "description": "Income Documentation (Paystubs, W-2s, Tax Returns)"
    },
    "EMPLOYMENT_VERIFICATION": {
        "priority": 7,
        "stage": "Income Verification",
        "keywords": ["voe", "voi", "employment verification", "verification of employment", "work number", "autovoe"],
        "description": "Employment/Income Verification (VOE/VOI)"
    },
    "ASSET_DOCS": {
        "priority": 8,
        "stage": "Asset Verification",
        "keywords": ["bank statement", "asset", "account statement", "checking", "savings", "investment"],
        "description": "Asset Documentation (Bank Statements)"
    },
    "FIRST_MORTGAGE": {
        "priority": 9,
        "stage": "Additional Documentation",
        "keywords": ["first mortgage", "senior lien", "existing mortgage", "mortgage statement", "payoff statement"],
        "description": "First Mortgage Documentation"
    },
    "INSURANCE": {
        "priority": 10,
        "stage": "Additional Documentation",
        "keywords": ["insurance", "homeowners insurance", "hazard insurance", "insurance declaration", "hoi"],
        "description": "Homeowners Insurance"
    },
    "FLOOD": {
        "priority": 11,
        "stage": "Additional Documentation",
        "keywords": ["flood", "flood zone", "flood certification", "fema", "flood determination"],
        "description": "Flood Certification"
    },
    "HOA": {
        "priority": 12,
        "stage": "Additional Documentation",
        "keywords": ["hoa", "homeowners association", "condo", "association dues", "condo fees"],
        "description": "HOA/Condo Documentation"
    },
    "TITLE": {
        "priority": 13,
        "stage": "Pre-Closing",
        "keywords": ["title", "title commitment", "title insurance", "title policy", "vesting", "encumbrance"],
        "description": "Title Commitment and Title Insurance"
    },
    "UNDERWRITING_CONDITIONS": {
        "priority": 14,
        "stage": "Underwriting Decision",
        "keywords": ["condition", "underwriting condition", "prior to doc", "ptd", "prior to funding", "ptf"],
        "description": "Underwriting Conditions"
    },
    "CLOSING_DISCLOSURE": {
        "priority": 15,
        "stage": "Pre-Closing",
        "keywords": ["closing disclosure", "cd", "settlement statement", "alta", "hud-1"],
        "description": "Closing Disclosure / Settlement Statement"
    },
    "INITIAL_DISCLOSURES": {
        "priority": 16,
        "stage": "Initial Disclosures",
        "keywords": ["initial disclosure", "loan estimate", "le", "tila", "respa", "notice", "right to cancel"],
        "description": "Initial Disclosures (Loan Estimate, TILA, RESPA)"
    },
    "CLOSING_DOCS": {
        "priority": 17,
        "stage": "Closing",
        "keywords": ["note", "mortgage", "deed of trust", "security instrument", "closing document", "pre-closing"],
        "description": "Closing Documents (Note, Mortgage, Deed of Trust)"
    },
    "ESIGN_AUDIT": {
        "priority": 18,
        "stage": "Closing",
        "keywords": ["esign", "e-sign", "audit log", "audit trail", "docusign", "electronic signature"],
        "description": "E-Signature Audit Trail"
    },
    "COMPLIANCE": {
        "priority": 19,
        "stage": "Compliance",
        "keywords": ["compliance", "fraud", "ofac", "patriot act", "identity verification", "4506"],
        "description": "Compliance Documentation (Fraud, OFAC, 4506-C)"
    },
    "FUNDING": {
        "priority": 20,
        "stage": "Funding",
        "keywords": ["funding", "disbursement", "wire", "ach", "proceeds", "settlement"],
        "description": "Funding and Disbursement"
    },
    "OTHER": {
        "priority": 99,
        "stage": "Other",
        "keywords": [],
        "description": "Uncategorized Documents"
    }
}


def load_semantic_json_files(loan_id: str) -> list[dict]:
    """Load all semantic JSON files for the loan."""
    semantic_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    if not semantic_dir.exists():
        print(f"❌ Semantic JSON directory not found: {semantic_dir}")
        return []
    
    json_files = list(semantic_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No semantic JSON files found in {semantic_dir}")
        return []
    
    print(f"\n📂 Loading {len(json_files)} semantic JSON files...")
    
    documents = []
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Include filename for reference
                data['source_filename'] = json_file.name
                data['source_path'] = str(json_file)
                documents.append(data)
        except Exception as e:
            print(f"   ✗ Error loading {json_file.name}: {e}")
    
    print(f"✓ Loaded {len(documents)} semantic documents")
    return documents


def extract_dates_from_text(text: str) -> list[datetime]:
    """Extract potential dates from text content."""
    dates = []
    
    # Common date patterns
    patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
        r'\b\d{4}-\d{2}-\d{2}\b',      # YYYY-MM-DD
        r'\b\d{1,2}-\d{1,2}-\d{4}\b',  # MM-DD-YYYY
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, str(text))
        for match in matches:
            try:
                # Try different date formats
                for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
                    try:
                        date = datetime.strptime(match, fmt)
                        if 2020 <= date.year <= 2030:  # Reasonable year range
                            dates.append(date)
                        break
                    except ValueError:
                        continue
            except Exception:
                continue
    
    return dates


def categorize_document(doc: dict) -> str:
    """Categorize a document based on its content."""
    # Get document content for analysis
    doc_type = doc.get('document_type', '').lower()
    summary = doc.get('summary', '').lower()
    key_entities = str(doc.get('key_entities', [])).lower()
    filename = doc.get('source_filename', '').lower()
    
    # Combine all text for keyword matching
    combined_text = f"{doc_type} {summary} {key_entities} {filename}"
    
    # Check each category
    best_match = "OTHER"
    best_score = 0
    
    for category, info in DOCUMENT_CATEGORIES.items():
        score = 0
        for keyword in info['keywords']:
            if keyword.lower() in combined_text:
                score += 1
        
        if score > best_score:
            best_score = score
            best_match = category
    
    return best_match


def analyze_timeline_with_llm(loan_id: str, documents: list[dict]) -> dict:
    """Use LLM to analyze document timeline and extract key dates."""
    
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
    
    system_prompt = """You are an expert mortgage loan processor and document analyst.

Your task is to analyze loan documents and reconstruct the chronological timeline of the loan process.

For each document, identify:
1. Document type and category
2. Key dates (creation, execution, signature, verification, etc.)
3. Document purpose and stage in loan lifecycle
4. Relationships to other documents

Loan Processing Stages:
1. Application - Borrower submits 1003 with signature date
2. Credit Pull - Credit report ordered and received
3. Home Valuation - AVM/Appraisal ordered and completed
4. Income Verification - Paystubs, W-2s, VOE collected and verified
5. Asset Verification - Bank statements collected
6. Additional Documentation - Flood cert, insurance, first mortgage
7. Underwriting Decision - Conditions issued
8. Pre-Closing - Closing disclosure, title commitment prepared
9. Closing - Final documents executed
10. Funding - Disbursement completed

Extract all dates mentioned in documents, including:
- Application signature date
- Credit report date
- Appraisal/valuation date
- Document creation dates
- Verification dates (VOE, VOI)
- E-signature dates
- Closing disclosure date
- Final closing/funding date

Return detailed timeline analysis with accurate dates extracted from document content."""

    # Prepare document summary for LLM
    doc_summaries = []
    for i, doc in enumerate(documents[:50]):  # Limit to first 50 to avoid token limits
        doc_summary = {
            "index": i,
            "filename": doc.get('source_filename', 'unknown'),
            "document_type": doc.get('document_type', 'unknown'),
            "summary": doc.get('summary', 'No summary'),
            "key_entities": doc.get('key_entities', [])[:10],  # Limit entities
            "dates_found": doc.get('key_dates', [])
        }
        doc_summaries.append(doc_summary)
    
    user_prompt = f"""Analyze the loan document timeline for loan {loan_id}.

Documents to analyze:
{json.dumps(doc_summaries, indent=2)}

Return a JSON object with this structure:
{{
  "loan_id": "{loan_id}",
  "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
  "key_milestones": [
    {{
      "milestone": "Application Submitted",
      "date": "YYYY-MM-DD",
      "document_references": ["filename"],
      "details": "string"
    }}
  ],
  "documents_by_stage": {{
    "Application": [
      {{
        "document_index": number,
        "filename": "string",
        "document_type": "string",
        "key_date": "YYYY-MM-DD",
        "description": "string"
      }}
    ],
    "Credit Pull": [...],
    "Home Valuation": [...],
    "Income Verification": [...],
    "Asset Verification": [...],
    "Additional Documentation": [...],
    "Underwriting Decision": [...],
    "Pre-Closing": [...],
    "Closing": [...],
    "Funding": [...]
  }},
  "timeline_summary": {{
    "application_date": "YYYY-MM-DD or null",
    "credit_report_date": "YYYY-MM-DD or null",
    "appraisal_date": "YYYY-MM-DD or null",
    "voe_date": "YYYY-MM-DD or null",
    "initial_disclosure_date": "YYYY-MM-DD or null",
    "closing_disclosure_date": "YYYY-MM-DD or null",
    "closing_date": "YYYY-MM-DD or null",
    "funding_date": "YYYY-MM-DD or null",
    "total_days_to_close": number or null
  }},
  "document_gaps": [
    "string (description of missing or unclear documents)"
  ],
  "processing_notes": [
    "string (observations about document collection and timing)"
  ]
}}"""

    print(f"\n🤖 Analyzing document timeline with Azure OpenAI ({AZURE_OPENAI_DEPLOYMENT})...")
    
    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=16000
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Add metadata
        analysis['metadata'] = {
            'agent': 'document_timeline_agent',
            'version': '1.0',
            'model': AZURE_OPENAI_DEPLOYMENT,
            'analysis_timestamp': datetime.now().isoformat(),
            'total_documents_analyzed': len(documents)
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error during LLM analysis: {e}")
        raise


def organize_documents_locally(documents: list[dict]) -> dict:
    """Organize documents by category without LLM."""
    organized = defaultdict(list)
    
    for doc in documents:
        category = categorize_document(doc)
        
        # Extract dates from filename and content
        filename = doc.get('source_filename', '')
        dates = extract_dates_from_text(filename)
        
        # Look for dates in document
        if doc.get('key_dates'):
            for date_item in doc['key_dates']:
                if isinstance(date_item, str):
                    # Try to parse string dates
                    try:
                        parsed_date = datetime.fromisoformat(date_item.replace('Z', '+00:00'))
                        dates.append(parsed_date)
                    except:
                        pass
                elif isinstance(date_item, datetime):
                    dates.append(date_item)
        
        # Convert dates to strings safely
        date_strings = []
        for d in dates:
            if isinstance(d, datetime):
                date_strings.append(d.strftime('%Y-%m-%d'))
            elif isinstance(d, str):
                date_strings.append(d)
        
        organized[category].append({
            'filename': doc.get('source_filename'),
            'document_type': doc.get('document_type'),
            'summary': doc.get('summary', '')[:200],
            'dates': sorted(set(date_strings)) if date_strings else [],
            'category_info': DOCUMENT_CATEGORIES[category]
        })
    
    return dict(organized)


def save_timeline_report(loan_id: str, analysis: dict, organized: dict) -> str:
    """Save the timeline analysis report."""
    reports_dir = Path(f"loan_docs/{loan_id}/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save full analysis
    analysis_path = reports_dir / f"document_timeline_{loan_id}_{timestamp}.json"
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump({
            'llm_analysis': analysis,
            'local_categorization': organized
        }, f, indent=2)
    
    # Save human-readable summary
    summary_path = reports_dir / f"document_timeline_{loan_id}_{timestamp}.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# Document Timeline Analysis - Loan {loan_id}\n\n")
        f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Timeline summary
        if analysis.get('timeline_summary'):
            f.write("## Timeline Summary\n\n")
            summary = analysis['timeline_summary']
            for key, value in summary.items():
                label = key.replace('_', ' ').title()
                f.write(f"- **{label}:** {value}\n")
            f.write("\n")
        
        # Key milestones
        if analysis.get('key_milestones'):
            f.write("## Key Milestones\n\n")
            for milestone in analysis['key_milestones']:
                f.write(f"### {milestone.get('milestone')}\n")
                f.write(f"- **Date:** {milestone.get('date')}\n")
                f.write(f"- **Details:** {milestone.get('details')}\n")
                if milestone.get('document_references'):
                    f.write(f"- **Documents:** {', '.join(milestone['document_references'])}\n")
                f.write("\n")
        
        # Documents by stage
        if analysis.get('documents_by_stage'):
            f.write("## Documents by Loan Stage\n\n")
            for stage, docs in analysis['documents_by_stage'].items():
                if docs:
                    f.write(f"### {stage} ({len(docs)} documents)\n\n")
                    for doc in docs:
                        f.write(f"- **{doc.get('filename')}**\n")
                        f.write(f"  - Type: {doc.get('document_type')}\n")
                        if doc.get('key_date'):
                            f.write(f"  - Date: {doc['key_date']}\n")
                        if doc.get('description'):
                            f.write(f"  - Description: {doc['description']}\n")
                        f.write("\n")
        
        # Document gaps
        if analysis.get('document_gaps'):
            f.write("## Document Gaps / Missing Items\n\n")
            for gap in analysis['document_gaps']:
                f.write(f"- {gap}\n")
            f.write("\n")
        
        # Processing notes
        if analysis.get('processing_notes'):
            f.write("## Processing Notes\n\n")
            for note in analysis['processing_notes']:
                f.write(f"- {note}\n")
    
    return str(analysis_path)


def display_timeline_summary(analysis: dict, organized: dict):
    """Display formatted timeline summary."""
    print("\n" + "="*80)
    print(f"📅 DOCUMENT TIMELINE ANALYSIS - Loan {analysis['loan_id']}")
    print("="*80)
    
    # Timeline Summary
    if analysis.get('timeline_summary'):
        print("\n📊 TIMELINE SUMMARY")
        print("-" * 80)
        summary = analysis['timeline_summary']
        
        timeline_items = [
            ('Application Date', summary.get('application_date')),
            ('Credit Report Date', summary.get('credit_report_date')),
            ('Appraisal Date', summary.get('appraisal_date')),
            ('VOE Date', summary.get('voe_date')),
            ('Initial Disclosure Date', summary.get('initial_disclosure_date')),
            ('Closing Disclosure Date', summary.get('closing_disclosure_date')),
            ('Closing Date', summary.get('closing_date')),
            ('Funding Date', summary.get('funding_date'))
        ]
        
        for label, date in timeline_items:
            status = f"✓ {date}" if date and date != 'null' else "✗ Not Found"
            print(f"   {label:.<30} {status}")
        
        if summary.get('total_days_to_close'):
            print(f"\n   ⏱️  Total Days to Close: {summary['total_days_to_close']} days")
    
    # Key Milestones
    if analysis.get('key_milestones'):
        print("\n\n🎯 KEY MILESTONES")
        print("-" * 80)
        for milestone in sorted(analysis['key_milestones'], 
                               key=lambda x: x.get('date', '9999-99-99')):
            date = milestone.get('date', 'Unknown')
            name = milestone.get('milestone', 'Unknown')
            details = milestone.get('details', '')
            
            print(f"\n   📌 {date} - {name}")
            if details:
                print(f"      {details}")
    
    # Documents by Stage
    print("\n\n📚 DOCUMENTS BY LOAN STAGE")
    print("-" * 80)
    
    if analysis.get('documents_by_stage'):
        for stage in ["Application", "Credit Pull", "Home Valuation", 
                      "Income Verification", "Asset Verification", 
                      "Additional Documentation", "Underwriting Decision",
                      "Pre-Closing", "Closing", "Funding"]:
            docs = analysis['documents_by_stage'].get(stage, [])
            if docs:
                print(f"\n   {stage.upper()} ({len(docs)} documents)")
                for doc in docs[:5]:  # Show first 5
                    filename = doc.get('filename', 'Unknown')
                    date = doc.get('key_date', '')
                    date_str = f" [{date}]" if date else ""
                    print(f"      • {filename}{date_str}")
                if len(docs) > 5:
                    print(f"      ... and {len(docs) - 5} more")
    
    # Local Categorization Summary
    print("\n\n📁 DOCUMENT CATEGORIZATION SUMMARY")
    print("-" * 80)
    
    # Sort categories by priority
    sorted_categories = sorted(
        organized.items(),
        key=lambda x: DOCUMENT_CATEGORIES[x[0]]['priority']
    )
    
    for category, docs in sorted_categories:
        if docs:
            cat_info = DOCUMENT_CATEGORIES[category]
            print(f"\n   {cat_info['description']}")
            print(f"   Stage: {cat_info['stage']} | Count: {len(docs)}")
            
            # Show first 3 documents
            for doc in docs[:3]:
                dates_str = f" ({', '.join(doc['dates'][:2])})" if doc['dates'] else ""
                print(f"      • {doc['filename']}{dates_str}")
            if len(docs) > 3:
                print(f"      ... and {len(docs) - 3} more")
    
    # Document Gaps
    if analysis.get('document_gaps'):
        print("\n\n⚠️  DOCUMENT GAPS / MISSING ITEMS")
        print("-" * 80)
        for gap in analysis['document_gaps']:
            print(f"   • {gap}")
    
    # Processing Notes
    if analysis.get('processing_notes'):
        print("\n\n📝 PROCESSING NOTES")
        print("-" * 80)
        for note in analysis['processing_notes']:
            print(f"   • {note}")
    
    print("\n" + "="*80)


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python agents/document_timeline_agent.py <loan_id>")
        print("Example: python agents/document_timeline_agent.py 1000182005")
        sys.exit(1)
    
    loan_id = sys.argv[1]
    
    print(f"\n🚀 Starting Document Timeline Agent for Loan {loan_id}")
    print("="*80)
    
    # Load semantic JSON files
    documents = load_semantic_json_files(loan_id)
    
    if not documents:
        print("❌ No semantic documents found. Exiting.")
        sys.exit(1)
    
    # Organize documents locally (fast categorization)
    print(f"\n📋 Categorizing {len(documents)} documents...")
    organized = organize_documents_locally(documents)
    print(f"✓ Documents organized into {len(organized)} categories")
    
    # Analyze timeline with LLM (detailed analysis)
    try:
        analysis = analyze_timeline_with_llm(loan_id, documents)
        print("✓ Timeline analysis completed")
    except Exception as e:
        print(f"❌ Failed to analyze timeline: {e}")
        sys.exit(1)
    
    # Save reports
    try:
        report_path = save_timeline_report(loan_id, analysis, organized)
        print(f"✓ Timeline report saved to: {report_path}")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")
        sys.exit(1)
    
    # Display summary
    display_timeline_summary(analysis, organized)
    
    print(f"\n✅ Document timeline analysis completed successfully!")
    print(f"📊 Full report saved to: {report_path}\n")


if __name__ == "__main__":
    main()
