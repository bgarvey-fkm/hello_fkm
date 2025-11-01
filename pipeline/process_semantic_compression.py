# -*- coding: utf-8 -*-
"""
Semantic Compression Pipeline

Takes RAW JSON files (Harvest API + Document Intelligence OCR) and produces
semantically compressed JSON using LLM processing.

This script processes the "raw_json" files that contain:
- metadata (from Harvest API) - PRESERVED VERBATIM
- document_intelligence (raw Azure OCR output) - PROCESSED BY LLM

And produces compressed semantic JSON with:
- metadata (preserved exactly as-is)
- semantic_content (LLM-extracted meaning with appropriate schema)
- _processing_metadata (compression stats, model info)

The LLM will:
1. Identify the document type
2. Create an appropriate JSON schema for that document type
3. Extract all meaningful data while compressing boilerplate
4. Preserve 100% of underwriting-relevant information

This runs in PARALLEL for speed.

Usage:
    python pipeline/process_semantic_compression.py <loan_id>
    
Example:
    python pipeline/process_semantic_compression.py 1000179167
"""

import os
import sys
import json

# Fix console encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
from pathlib import Path
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize Azure OpenAI client (async)
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

client = AsyncAzureOpenAI(
    api_key=subscription_key,
    api_version=api_version,
    azure_endpoint=endpoint
)


def load_form_1003_schema():
    """Load Form 1003 schema for structured extraction."""
    schema_path = Path("utils/form_1003_schema.json")
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Warning: Form 1003 schema not found at {schema_path}")
        return None


async def process_document_semantic(input_path, output_path):
    """
    Process a combined JSON file (metadata + document_intelligence) into semantic JSON.
    
    Args:
        input_path: Path to combined JSON with metadata and document_intelligence
        output_path: Path to save semantically compressed JSON
    """
    
    # Load combined document
    with open(input_path, 'r', encoding='utf-8') as f:
        combined_doc = json.load(f)
    
    # Extract components
    metadata = combined_doc.get('metadata', {})
    doc_intelligence = combined_doc.get('document_intelligence', {})
    
    # Get the content
    content = doc_intelligence.get('content', '')
    table_count = len(doc_intelligence.get('tables', []))
    page_count = len(doc_intelligence.get('pages', []))
    
    # Get document type hints from metadata
    doc_type = metadata.get('SpringDocType') or metadata.get('DocPredictionType') or 'unknown'
    file_name = metadata.get('FileName', 'unknown')
    
    # Load Form 1003 schema (but only include key sections in prompt to avoid token bloat)
    form_1003_schema = load_form_1003_schema()
    
    # Build simplified Form 1003 schema description for prompt
    form_1003_description = """
Form 1003 Required Sections:
- lender_info: {lender_loan_number, universal_loan_identifier, agency_case_number}
- section_1_borrower_info: {personal_info, current_employment, previous_employment, income_sources}
- section_2_financial_assets_liabilities: {assets[], liabilities[], real_estate_owned[]}
- section_3_previous_employment: {employment_history[]}
- section_4_loan_property_info: {loan_and_property_information, transaction_details}
- section_5_declarations: {questions about bankruptcies, foreclosures, lawsuits, etc.}
- section_6_acknowledgments: {agreement, borrower_signature, co_borrower_signature}
- section_7_military_service: {military_service_status}
- section_8_demographic_info: {ethnicity, sex, race}

Extract all borrower and co-borrower data, employment history, assets/liabilities, property details, and declarations.
"""
    
    # Build prompt - mention Form 1003 but don't include full schema
    prompt = f"""You are a Mortgage Loan Document Processor AI with expertise in understanding and extracting semantic meaning from loan documents.

INPUT DOCUMENT CONTENT (from OCR):
{content}

DOCUMENT METADATA (for context only):
- Filename: {file_name}
- Suggested Type: {doc_type}
- Pages: {page_count}
- Tables: {table_count}
- Timeline Stage: {metadata.get('Timeline', 'unknown')}

YOUR TASK:

**STEP 1: Identify the document type**

First, determine if this is a **Form 1003 (Uniform Residential Loan Application / URLA)**. 
A Form 1003 contains:
- Borrower personal information (name, SSN, DOB, citizenship, marital status)
- Current and previous addresses
- Employment and income information
- Assets and liabilities sections
- Loan and property information
- Declarations (bankruptcies, foreclosures, lawsuits, etc.)
- Demographic information
- Acknowledgments and agreements

{form_1003_description}

**STEP 2: Extract data based on document type**

IF THIS IS A FORM 1003:
- Set "document_type": "form_1003"
- Extract data into the structure described above
- Include all 8 sections as separate top-level objects
- For blank/missing fields, use null
- Preserve amounts as numbers, dates as strings in MM/DD/YYYY format
- Extract co-borrower data if present
- Include all employment history, assets, and liabilities

IF THIS IS NOT A FORM 1003:
- Identify the actual document type (credit_report, paystub, w2, appraisal, title_commitment, etc.)
- Create an appropriate JSON schema for that document type
- Extract all meaningful data while compressing boilerplate

**STEP 3: Output**

Output ONLY valid JSON (no markdown, no code blocks, no explanations)

CRITICAL RULES:
- PRESERVE: All financial amounts, dates, names, addresses, account numbers, rates, terms
- PRESERVE: All verification data (signatures, dates, verification numbers)
- PRESERVE: All risk data (credit scores, DTI, employment, income, assets, liabilities)
- COMPRESS: Legal boilerplate, disclaimers, instructions, formatting
- SCHEMA: Use Form 1003 schema if applicable, otherwise create appropriate structure

EXAMPLE OUTPUT STRUCTURES for non-Form 1003 documents:

For Credit Report:
{{
  "document_type": "credit_report",
  "summary": "Credit report for [Name] with score [Score]",
  "borrower": {{"name": "...", "ssn": "***-**-1234", "dob": "MM/DD/YYYY", "current_address": "..."}},
  "credit_score": {{"score": 750, "model": "FICO", "date": "..."}},
  "tradelines": [...],
  "summary_stats": {{...}}
}}

For Paystub:
{{
  "document_type": "paystub",
  "summary": "Paystub for [Name] from [Employer]",
  "employer": {{"name": "...", "address": "..."}},
  "employee": {{"name": "...", "address": "..."}},
  "pay_period": {{"start": "...", "end": "...", "pay_date": "..."}},
  "earnings": [
    {{
      "type": "Salary",
      "hours": 40.0,
      "rate": 25.0,
      "amount": 1000.0,
      "ytd_hours": 2000.0,
      "ytd_amount": 50000.0
    }},
    {{
      "type": "Commission",
      "hours": null,
      "rate": null,
      "amount": 5000.0,
      "ytd_hours": null,
      "ytd_amount": 60000.0
    }},
    {{
      "type": "Bonus-Regular",
      "hours": null,
      "rate": null,
      "amount": 10000.0,
      "ytd_hours": null,
      "ytd_amount": 40000.0
    }},
    {{
      "type": "Overtime",
      "hours": 5.0,
      "rate": 37.5,
      "amount": 187.5,
      "ytd_hours": 100.0,
      "ytd_amount": 3750.0
    }}
  ],
  "taxes": [
    {{
      "type": "Federal Withholding",
      "amount": 2000.0,
      "ytd_amount": 25000.0
    }},
    {{
      "type": "Social Security",
      "amount": 620.0,
      "ytd_amount": 7750.0
    }}
  ],
  "gross_pay": 16187.5,
  "net_pay": 12500.0,
  "ytd_gross": 153750.0
}}

CRITICAL FOR PAYSTUBS: 
1. Paystubs show earnings in tables with headers like: "INCOME | HRS/UNITS | RATE | AMT | YTD HRS/UNITS | YTD AMT"
2. EVERY earnings row (Salary, Commission, Bonus, Overtime, Tips) has BOTH a current amount AND a YTD amount
3. You MUST extract BOTH values for EACH earnings type
4. Look for the YTD column - it's usually the rightmost column in the earnings section
5. Even if the current period amount is 0, the YTD amount is still valuable and MUST be extracted
6. Example: "Bonus-Regular    10,000.00    20,000.00" means current bonus $10k, YTD bonus $20k
7. Example: "Bonus-Regular    0    101,960.82" means no bonus this period, but $101,960.82 YTD
8. This is CRITICAL for income calculations - bonuses/commissions can be $100k+ annually

For W2:
{{
  "document_type": "w2",
  "summary": "W2 for [Year]",
  "tax_year": 2024,
  "employer": {{...}},
  "employee": {{...}},
  "wages": {{"box_1": 75000, "box_2": 12000, ...}},
  "state_info": [...]
}}

For Appraisal:
{{
  "document_type": "appraisal",
  "summary": "Appraisal of [Address]",
  "property": {{
    "address": "...",
    "property_type": "single_family",
    "year_built": 1995,
    "square_feet": 2400,
    ...
  }},
  "valuation": {{
    "appraised_value": 350000,
    "effective_date": "...",
    "approach": "sales_comparison"
  }},
  "appraiser": {{...}},
  "comparables": [...]
}}

**Adapt the schema to match the actual document type you identify.**
**Include ALL meaningful data - amounts, dates, names, account numbers, etc.**
**Output ONLY the JSON - no markdown, no explanations.**"""

    # Call LLM
    print(f"   Input: {len(content):,} chars ({len(content)//4:,} tokens approx)")
    
    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert Mortgage Loan Document Processor. Output only valid JSON, no markdown."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    # Parse response
    semantic_content = json.loads(response.choices[0].message.content)
    
    # Build output structure - PRESERVE METADATA VERBATIM
    output = {
        'metadata': metadata,  # << PRESERVED EXACTLY AS-IS FROM RAW JSON
        'semantic_content': semantic_content,  # << LLM-created structured data
        '_processing_metadata': {  # << Processing info (renamed to avoid confusion)
            'source_file': str(input_path.name),
            'processing_model': deployment,
            'raw_content_length': len(content),
            'semantic_content_length': len(json.dumps(semantic_content)),
            'compression_ratio': f"{len(content) / len(json.dumps(semantic_content)):.1f}x",
            'processed_at': combined_doc.get('processing_info', {}).get('processed_at', 'unknown')
        }
    }
    
    # Save output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    output_size = len(json.dumps(output))
    compression = len(content) / len(json.dumps(semantic_content))
    
    print(f"   Output: {output_size:,} chars | Compression: {compression:.1f}x")
    
    return output


async def process_loan(loan_id):
    """
    Process all raw JSON files for a loan into semantically compressed JSONs.
    Runs in PARALLEL for speed.
    """
    
    # Paths
    input_dir = Path(f"loan_docs/{loan_id}/raw_json")
    output_dir = Path(f"loan_docs/{loan_id}/semantic_json")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all JSON files
    json_files = sorted(input_dir.glob("FID*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {input_dir}")
        return
    
    print("=" * 80)
    print(f"SEMANTIC COMPRESSION PIPELINE")
    print("=" * 80)
    print(f"Loan ID: {loan_id}")
    print(f"Input: {input_dir}/")
    print(f"Output: {output_dir}/")
    print(f"Documents: {len(json_files)}")
    print(f"Mode: PARALLEL PROCESSING")
    print("=" * 80)
    print()
    
    # Process each document
    async def process_single(idx, json_file):
        """Process a single document and return result."""
        print(f"[{idx+1}/{len(json_files)}] 📄 {json_file.name}")
        output_path = output_dir / json_file.name
        
        try:
            result = await process_document_semantic(
                input_path=json_file,
                output_path=output_path
            )
            return {
                'file': json_file.name,
                'status': 'success',
                'type': result['semantic_content'].get('document_type', 'unknown'),
                'compression': result['_processing_metadata']['compression_ratio']
            }
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {
                'file': json_file.name,
                'status': 'error',
                'error': str(e)
            }
    
    # Process all documents IN PARALLEL using asyncio.gather
    print(">> Starting parallel processing...\n")
    tasks = [process_single(idx, json_file) for idx, json_file in enumerate(json_files)]
    results = await asyncio.gather(*tasks)
    
    # Summary
    print("=" * 80)
    print(">> PROCESSING SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"  ✅ Processed: {len(successful)}")
    print(f"  ❌ Errors: {len(failed)}")
    print(f"  📁 Output: {output_dir}")
    print("=" * 80)
    
    if successful:
        # Group by document type
        by_type = {}
        for r in successful:
            doc_type = r['type']
            if doc_type not in by_type:
                by_type[doc_type] = []
            by_type[doc_type].append(r)
        
        print("\nDocument Types:")
        for doc_type, docs in sorted(by_type.items()):
            print(f"  - {doc_type}: {len(docs)} documents")
    
    if failed:
        print("\nErrors:")
        for r in failed:
            print(f"  - {r['file']}: {r['error']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        print("Usage: python pipeline/process_semantic_compression.py <loan_id>")
        print("Example: python pipeline/process_semantic_compression.py 1000179167")
        sys.exit(1)
    
    asyncio.run(process_loan(loan_id))
