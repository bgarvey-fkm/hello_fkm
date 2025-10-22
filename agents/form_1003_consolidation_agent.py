"""
Form 1003 Consolidation Agent

Reads ALL semantic JSON files from a loan package and consolidates them
into a complete, accurate Form 1003 JSON following the official schema.

This agent:
1. Loads all semantic_json/* files
2. Loads the Form 1003 schema template
3. Uses LLM to intelligently map semantic data to Form 1003 fields
4. Respects that values may have changed during underwriting
5. Prioritizes the most recent/authoritative source for each field
6. Flags any conflicts or uncertainties

Usage:
    python agents/form_1003_consolidation_agent.py <loan_id>
    
Example:
    python agents/form_1003_consolidation_agent.py 1000182227
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


def load_form_1003_schema():
    """Load the Form 1003 JSON schema template."""
    schema_path = Path("form_1003/form_1003_schema.json")
    with open(schema_path, 'r', encoding='utf-8') as f:
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
                # Use a clean key name
                clean_name = json_file.stem.replace("__aws-prd-nfs03_Deals_Trade__SpringEQ_Src_453_1000182227_", "")
                semantic_docs[clean_name] = data
        except Exception as e:
            print(f"⚠️  Error loading {json_file.name}: {e}")
    
    return semantic_docs


def consolidate_form_1003(loan_id="1000182227"):
    """
    Consolidate all semantic JSONs into a complete Form 1003.
    """
    
    print("=" * 80)
    print(f"Form 1003 Consolidation Agent - Loan {loan_id}")
    print("=" * 80)
    print()
    
    # Load schema and semantic data
    print("📋 Loading Form 1003 schema template...")
    schema = load_form_1003_schema()
    
    print("📁 Loading all semantic JSON files...")
    semantic_docs = load_all_semantic_json(loan_id)
    
    if not semantic_docs:
        print("❌ No semantic JSON files found!")
        return None
    
    print(f"✅ Loaded {len(semantic_docs)} semantic documents:")
    for doc_name, doc_data in semantic_docs.items():
        doc_type = doc_data.get('document_type', 'unknown')
        print(f"   - {doc_name}: {doc_type}")
    
    print()
    print("=" * 80)
    print("🤖 Sending to LLM for intelligent consolidation...")
    print("=" * 80)
    print()
    
    # Build comprehensive prompt
    prompt = f"""You are a Mortgage Loan Processing AI with expertise in Form 1003 (Uniform Residential Loan Application).

TASK: Consolidate data from multiple semantic loan documents into a complete, accurate Form 1003 JSON.

FORM 1003 SCHEMA (YOUR OUTPUT MUST MATCH THIS):
{json.dumps(schema, indent=2)}

AVAILABLE SEMANTIC DOCUMENTS:
{json.dumps(semantic_docs, indent=2)}

CRITICAL INSTRUCTIONS:

1. DATA SOURCE PRIORITY (most authoritative first):
   - ALTA Settlement Statement / Closing Disclosure: Final loan terms, property address, closing date
   - Form 1003 (if present): Application data, borrower info, employment, assets
   - Underwriting Worksheet: Final DTI, LTV, income calculations
   - W-2s: Employment verification, income
   - Paystubs: Current employment, YTD income
   - Credit Report: Liabilities, credit scores
   - Appraisal: Property value, characteristics
   - Insurance: Property insurance details
   - Mortgage Statement: Existing mortgage balance

2. HANDLE DISCREPANCIES:
   - If values changed during underwriting (e.g., loan amount, income), use FINAL values from settlement/closing docs
   - If employment changed, use most recent paystub
   - If addresses differ, use settlement statement for property, latest paystub for current residence
   - Flag any significant conflicts in a "_data_quality_notes" field

3. MISSING DATA:
   - If a REQUIRED field has no data in any document, set to null and note in "_data_quality_notes"
   - For optional fields, omit if no data available
   - Do NOT fabricate data

4. DATA VALIDATION:
   - Ensure SSN format: ###-##-####
   - Ensure dates: mm/dd/yyyy
   - Ensure amounts are numbers (not strings)
   - Respect enum constraints from schema

5. OUTPUT FORMAT:
   - Valid JSON matching the Form 1003 schema EXACTLY
   - Add "_metadata" section with processing info
   - Add "_data_quality_notes" array for any issues/conflicts
   - Output ONLY JSON, no markdown, no explanations

6. KEY SECTIONS TO POPULATE:
   - lender_info: Use settlement statement
   - section_1_borrower_info: Combine Form 1003, paystubs, W-2s, settlement
   - section_2_financial_assets_liabilities: Use credit report, Form 1003
   - section_3_real_estate: Use Form 1003, appraisal
   - section_4_loan_property_info: Use settlement, appraisal
   - section_5_declarations: Use Form 1003
   - section_6_acknowledgments: Use Form 1003, settlement
   - section_7_military_service: Use Form 1003
   - section_8_demographic_info: Use Form 1003
   - section_9_loan_originator_info: Use settlement statement

BEGIN CONSOLIDATION. Output complete Form 1003 JSON now:"""

    # Call LLM with extended timeout for complex processing
    print("⏳ Processing (this may take 30-60 seconds for complex consolidation)...")
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system", 
                "content": "You are an expert Mortgage Loan Processor specializing in Form 1003 data consolidation. Output only valid JSON matching the provided schema."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=16000  # Form 1003 can be large
    )
    
    # Parse response
    consolidated_1003 = json.loads(response.choices[0].message.content)
    
    # Add processing metadata if not already present
    if '_metadata' not in consolidated_1003:
        consolidated_1003['_metadata'] = {}
    
    consolidated_1003['_metadata'].update({
        'processing_date': datetime.now().isoformat(),
        'source_documents_count': len(semantic_docs),
        'source_documents': list(semantic_docs.keys()),
        'processing_model': deployment,
        'agent': 'form_1003_consolidation_agent'
    })
    
    # Save output
    output_dir = Path(f"loan_docs/{loan_id}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"form_1003_consolidated_{loan_id}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated_1003, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 80)
    print("✅ CONSOLIDATION COMPLETE!")
    print("=" * 80)
    print(f"📄 Saved to: {output_path}")
    print()
    
    # Summary
    if '_data_quality_notes' in consolidated_1003:
        notes = consolidated_1003['_data_quality_notes']
        if notes:
            print("⚠️  DATA QUALITY NOTES:")
            for note in notes:
                print(f"   - {note}")
            print()
    
    # Show key populated sections
    print("📊 POPULATED SECTIONS:")
    sections = [
        'lender_info',
        'section_1_borrower_info',
        'section_2_financial_assets_liabilities',
        'section_3_real_estate',
        'section_4_loan_property_info',
        'section_5_declarations',
        'section_6_acknowledgments',
        'section_7_military_service',
        'section_8_demographic_info',
        'section_9_loan_originator_info'
    ]
    
    for section in sections:
        if section in consolidated_1003:
            status = "✅" if consolidated_1003[section] else "⚠️  (empty)"
            print(f"   {status} {section}")
        else:
            print(f"   ❌ {section} (missing)")
    
    print()
    print("=" * 80)
    
    return consolidated_1003


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    consolidate_form_1003(loan_id)
