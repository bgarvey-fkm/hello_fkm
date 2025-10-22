"""
Document Semantic Processor Agent

Takes raw Document Intelligence JSON and produces semantic, compressed JSON
based on document type schemas. Acts as a "Mortgage Loan Document Processor"
that understands the meaning and importance of document data.

Usage:
    python agents/document_semantic_processor.py <loan_id> <document_name>
    
Example:
    python agents/document_semantic_processor.py 1000182227 "title.json"
"""

import os
import sys
import json
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

def load_schema(schema_name):
    """Load a document schema from utils/"""
    schema_path = Path(f"utils/{schema_name}")
    with open(schema_path, 'r') as f:
        return json.load(f)

async def process_document(raw_json_path, output_path, document_type="auto_detect"):
    """
    Process a raw Document Intelligence JSON into semantic JSON.
    
    Args:
        raw_json_path: Path to raw JSON from Document Intelligence
        output_path: Path to save semantic JSON
        document_type: Type of document (or "auto_detect")
    """
    
    # Load raw document
    with open(raw_json_path, 'r', encoding='utf-8') as f:
        raw_doc = json.load(f)
    
    # Get the content
    content = raw_doc.get('content', '')
    
    # Also include table count as context
    table_count = len(raw_doc.get('tables', []))
    
    # Load appropriate schema based on document type
    if document_type == "auto_detect":
        # Let the LLM detect the document type
        schema_info = "You will determine the document type from: alta_settlement_statement, title_commitment, appraisal, w2, paystub, credit_report, mortgage_statement, insurance, form_1003"
    else:
        schema_path = f"{document_type}_schema.json"
        try:
            schema = load_schema(schema_path)
            schema_info = f"Use this JSON schema: {json.dumps(schema, indent=2)}"
        except FileNotFoundError:
            schema_info = "No specific schema found. Create appropriate structured output."
    
    # Build prompt
    prompt = f"""You are a Mortgage Loan Document Processor AI with expertise in understanding and extracting semantic meaning from loan documents.

INPUT DOCUMENT:
{content}

METADATA:
- Document has {table_count} tables
- Original filename: {raw_doc.get('document_name', 'unknown')}

YOUR TASK:
1. Identify the document type
2. Extract the SEMANTIC MEANING - what matters for underwriting/loan processing
3. Compress the data significantly while retaining all critical information
4. Output ONLY valid JSON (no markdown, no explanations)

{schema_info}

FOCUS ON:
- Key financial data (amounts, dates, parties)
- Critical loan/property information
- Compliance/legal data points
- Risk-relevant information

IGNORE:
- Boilerplate legal text
- Formatting information
- Repetitive disclaimers
- Page numbers/footers

OUTPUT FORMAT:
{{
  "document_type": "...",
  "summary": "One sentence description",
  ...rest of structured data based on document type...
}}

Remember: The goal is to compress the content down to essential semantic data while keeping 100% of the value for a loan processor."""

    # Call LLM
    print(f"📤 Sending to LLM for semantic processing...")
    print(f"   Input size: {len(content)} chars ({len(content)//4} tokens approx)")
    
    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert Mortgage Loan Document Processor. Output only valid JSON, no markdown."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    # Parse response
    semantic_json = json.loads(response.choices[0].message.content)
    
    # Add metadata
    semantic_json['_metadata'] = {
        'source_file': raw_doc.get('document_name'),
        'processing_model': deployment,
        'raw_content_length': len(content),
        'compression_ratio': f"{len(content) / len(json.dumps(semantic_json)):.1f}x"
    }
    
    # Save output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(semantic_json, f, indent=2, ensure_ascii=False)
    
    output_size = len(json.dumps(semantic_json))
    print(f"✅ Semantic processing complete!")
    print(f"   Output size: {output_size} chars ({output_size//4} tokens approx)")
    print(f"   Compression: {len(content) / output_size:.1f}x")
    print(f"   Saved to: {output_path}")
    
    return semantic_json


async def process_loan_documents(loan_id="1000182227"):
    """
    Process all raw JSONs for a loan into semantic JSONs (async parallel).
    """
    
    loan_dir = Path(f"loan_docs/{loan_id}")
    raw_json_dir = loan_dir / "json"
    semantic_json_dir = loan_dir / "semantic_json"
    
    # Create output directory
    semantic_json_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all raw JSON files
    json_files = list(raw_json_dir.glob("*.json"))
    
    print("=" * 80)
    print(f"Processing {len(json_files)} documents for loan {loan_id}")
    print(f"Raw JSON: {raw_json_dir}/")
    print(f"Output: {semantic_json_dir}/")
    print("Processing in parallel with async I/O...")
    print("=" * 80)
    print()
    
    # Create tasks for all documents
    async def process_single(json_file):
        """Process a single document and return result."""
        print(f"📄 Processing: {json_file.name}")
        output_path = semantic_json_dir / json_file.name
        
        try:
            semantic_doc = await process_document(
                raw_json_path=json_file,
                output_path=output_path,
                document_type="auto_detect"
            )
            return {
                'file': json_file.name,
                'status': 'success',
                'type': semantic_doc.get('document_type', 'unknown'),
                'compression': semantic_doc['_metadata']['compression_ratio']
            }
        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")
            return {
                'file': json_file.name,
                'status': 'error',
                'error': str(e)
            }
    
    # Process all documents in parallel
    tasks = [process_single(json_file) for json_file in json_files]
    results = await asyncio.gather(*tasks)
    
    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print("\nDocument Types Processed:")
        for r in successful:
            print(f"  - {r['file']}: {r['type']} (compressed {r['compression']})")
    
    if failed:
        print("\nErrors:")
        for r in failed:
            print(f"  - {r['file']}: {r['error']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    if len(sys.argv) > 2:
        # Process single document
        doc_name = sys.argv[2]
        raw_path = Path(f"loan_docs/{loan_id}/json/{doc_name}")
        output_path = Path(f"loan_docs/{loan_id}/semantic_json/{doc_name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(process_document(raw_path, output_path))
    else:
        # Process all documents in parallel
        asyncio.run(process_loan_documents(loan_id))
